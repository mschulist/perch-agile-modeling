from perch_hoplite.db import sqlite_usearch_impl
from perch_analyzer.db import db
from perch_hoplite.zoo import model_configs
from perch_hoplite.db import interface

SEARCH_PROVENANCE = "searched_annotator"


def search_using_target_recordings(
    db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    num_per_target_recording: int,
):
    model_config = hoplite_db.get_metadata("model_config")

    embedding_model = model_configs.get_model_class(model_config.model_key).from_config(  # type: ignore
        model_config
    )

    target_recordings = db.get_all_target_recordings(include_finished=False)

    for target_recording in target_recordings:
        target_embedding = embedding_model.embed(target_recording.audio)
        if not target_embedding.embeddings:
            continue
        close_results = hoplite_db.ui.search(
            target_embedding.embeddings, num_per_target_recording
        )

        for result in close_results:
            window = hoplite_db.get_window(result.key)

            hoplite_db.insert_annotation(
                recording_id=window.recording_id,
                offsets=window.offsets,
                label=target_recording.label,
                provenance=SEARCH_PROVENANCE,
                label_type=interface.LabelType.POSITIVE,  # TODO: use the uncertain label
            )
