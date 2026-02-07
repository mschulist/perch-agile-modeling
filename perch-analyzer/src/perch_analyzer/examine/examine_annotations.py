from pydantic import BaseModel, ConfigDict
from perch_hoplite.db import interface
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_analyzer.config import config

from ml_collections import config_dict


class WindowWithAnnotations(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    recording: interface.Recording
    window: interface.Window
    annotations: list[interface.Annotation]


def get_windows_by_label(
    hoplite_db: SQLiteUSearchDB, label: str
) -> list[WindowWithAnnotations]:
    window_ids = hoplite_db.match_window_ids(
        annotations_filter=config_dict.create(
            eq=dict(label=label, label_type=interface.LabelType.POSITIVE)
        )
    )

    windows_with_annotations: list[WindowWithAnnotations] = []

    for window_id in window_ids:
        window = hoplite_db.get_window(window_id)
        annotations = hoplite_db.get_all_annotations(
            config_dict.create(
                eq=dict(recording_id=window.recording_id),
                approx=dict(offsets=window.offsets),
            )
        )
        recording = hoplite_db.get_recording(window.recording_id)

        windows_with_annotations.append(
            WindowWithAnnotations(
                recording=recording, window=window, annotations=list(annotations)
            )
        )

    return windows_with_annotations


def update_labels(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    window_id: int,
    new_labels: list[str],
):
    window = hoplite_db.get_window(window_id)

    existing_annotations = hoplite_db.get_all_annotations(
        config_dict.create(
            eq=dict(recording_id=window.recording_id),
            approx=dict(offsets=window.offsets),
        )
    )

    existing_labels = [ann.label for ann in existing_annotations]

    annotations_to_remove = [
        ann for ann in existing_annotations if ann.label not in new_labels
    ]

    labels_to_add = [lab for lab in new_labels if lab not in existing_labels]

    for ann_to_rem in annotations_to_remove:
        hoplite_db.remove_annotation(ann_to_rem.id)

    for lab in labels_to_add:
        hoplite_db.insert_annotation(
            window.recording_id,
            offsets=window.offsets,
            label=lab,
            label_type=interface.LabelType.POSITIVE,
            provenance=config.user_name,
        )

    hoplite_db.commit()
