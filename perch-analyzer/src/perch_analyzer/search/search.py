from perch_hoplite.db import sqlite_usearch_impl
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_hoplite.zoo import model_configs
from perch_hoplite.db import interface

SEARCH_PROVENANCE = "searched_annotator"


def search_using_target_recordings(
    config: config.Config,
    db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    num_per_target_recording: int,
):
    embedding_model = model_configs.load_model_by_name(config.embedding_model)

    target_recordings = db.get_all_target_recordings(include_finished=False)

    for target_recording in target_recordings:
        target_embedding = embedding_model.embed(target_recording.audio)
        if target_embedding.embeddings is None:
            continue
        close_results = hoplite_db.ui.search(
            target_embedding.embeddings[0, 0], num_per_target_recording
        )

        for result in close_results:
            window = hoplite_db.get_window(result.key)

            hoplite_db.insert_annotation(
                recording_id=window.recording_id,
                offsets=window.offsets,
                label=target_recording.label,
                provenance=SEARCH_PROVENANCE,
                label_type=interface.LabelType.POSSIBLE,
            )

    hoplite_db.commit()
