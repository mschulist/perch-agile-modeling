"""Reading and editing the annotations attached to audio windows."""

import logging
from collections import defaultdict
from collections.abc import Sequence

from ml_collections import config_dict
from perch_hoplite.db import datatypes
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from pydantic import BaseModel, ConfigDict

from perch_analyzer.config import config

logger = logging.getLogger(__name__)

# Offsets are floats written from the same source on both sides of the join,
# so rounding well below the window hop is enough to group them.
_OFFSET_PRECISION = 4

# (recording_id, *rounded offsets), used to join annotations onto windows.
OffsetKey = tuple[float, ...]


class WindowWithAnnotations(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    recording: datatypes.Recording
    window: datatypes.Window
    annotations: list[datatypes.Annotation]


def _offset_key(recording_id: int, offsets: Sequence[float]) -> OffsetKey:
    return (recording_id, *(round(float(o), _OFFSET_PRECISION) for o in offsets))


def get_window_ids_by_label(hoplite_db: SQLiteUSearchDB, label: str) -> list[int]:
    """Get the ids of every window positively annotated with `label`."""
    return list(
        hoplite_db.match_window_ids(
            annotations_filter=config_dict.create(
                eq=dict(label=label, label_type=datatypes.LabelType.POSITIVE)
            )
        )
    )


def get_windows_with_annotations(
    hoplite_db: SQLiteUSearchDB, window_ids: Sequence[int]
) -> list[WindowWithAnnotations]:
    """Load windows, their recordings and their annotations in bulk.

    Done as three queries regardless of how many windows are asked for, rather
    than three queries per window.
    """
    if not window_ids:
        return []

    windows = hoplite_db.get_all_windows(
        filter=config_dict.create(isin=dict(id=[int(i) for i in window_ids]))
    )
    recording_ids = sorted({window.recording_id for window in windows})

    recordings = {
        recording.id: recording
        for recording in hoplite_db.get_all_recordings(
            filter=config_dict.create(isin=dict(id=recording_ids))
        )
    }

    annotations_by_offset: dict[OffsetKey, list[datatypes.Annotation]] = defaultdict(
        list
    )
    for annotation in hoplite_db.get_all_annotations(
        filter=config_dict.create(isin=dict(recording_id=recording_ids))
    ):
        key = _offset_key(annotation.recording_id, annotation.offsets)
        annotations_by_offset[key].append(annotation)

    windows_by_id = {window.id: window for window in windows}

    result: list[WindowWithAnnotations] = []
    for window_id in window_ids:
        window = windows_by_id.get(int(window_id))
        if window is None:
            logger.warning("window %s disappeared while loading", window_id)
            continue
        result.append(
            WindowWithAnnotations(
                recording=recordings[window.recording_id],
                window=window,
                annotations=annotations_by_offset[
                    _offset_key(window.recording_id, window.offsets)
                ],
            )
        )
    return result


def get_windows_by_label(
    hoplite_db: SQLiteUSearchDB, label: str
) -> list[WindowWithAnnotations]:
    return get_windows_with_annotations(
        hoplite_db, get_window_ids_by_label(hoplite_db, label)
    )


def update_labels(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    window_id: int,
    new_labels: Sequence[str],
) -> None:
    window = hoplite_db.get_window(window_id)

    existing_annotations = hoplite_db.get_all_annotations(
        config_dict.create(
            eq=dict(recording_id=window.recording_id),
            approx=dict(offsets=window.offsets),
        )
    )

    existing_labels = {ann.label for ann in existing_annotations}
    new_label_set = set(new_labels)

    for annotation in existing_annotations:
        if annotation.label not in new_label_set:
            hoplite_db.remove_annotation(annotation.id)

    for label in new_labels:
        if label not in existing_labels:
            hoplite_db.insert_annotation(
                window.recording_id,
                offsets=window.offsets,
                label=label,
                label_type=datatypes.LabelType.POSITIVE,
                provenance=config.user_name,
            )

    hoplite_db.commit()
