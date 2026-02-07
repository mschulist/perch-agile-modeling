import reflex as rx
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl, interface
from ml_collections import config_dict
from .state import ConfigState


def summary():
    hoplite_db = ConfigState.get_hoplite_db()
    analyzer_db = ConfigState.get_analyzer_db()

    class_counts = hoplite_db.count_each_label()
    embedding_count = hoplite_db.count_embeddings()
    annotation_count = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.POSITIVE))
        )
    )
    recording_count = len(hoplite_db.get_all_recordings())

    target_recordings_count = analyzer_db.count_target_recordings(True)
    annotations_to_be_labeled = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.POSSIBLE))
        )
    )

    return rx.center(
        rx.vstack(
            rx.heading("Summary", size="9"),
            rx.heading(f"Classes: {len(class_counts)}", size="6"),
            rx.heading(f"Windows: {embedding_count}", size="6"),
            rx.heading(f"Annotations: {annotation_count}", size="6"),
            rx.heading(f"Recordings: {recording_count}", size="6"),
            rx.heading(f"Target recordings: {target_recordings_count}", size="6"),
            rx.heading(
                f"Annotations to be labeled: {annotations_to_be_labeled}", size="6"
            ),
            spacing="4",
            align="center",
        )
    )
