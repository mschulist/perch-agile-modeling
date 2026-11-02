import logging

from perch_hoplite.db import datatypes, sqlite_usearch_impl
from perch_hoplite.zoo import model_configs

from perch_analyzer.config import config
from perch_analyzer.db import db

logger = logging.getLogger(__name__)

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
        # Embed and search before writing anything. SQLite takes its write
        # lock at the first INSERT and holds it until commit, so inserting
        # inside this loop and committing at the end would lock out every GUI
        # user's label saves for the whole (slow) search.
        target_embedding = embedding_model.embed(target_recording.audio)
        if target_embedding.embeddings is None:
            continue
        close_results = hoplite_db.ui.search(
            target_embedding.embeddings[0, 0], num_per_target_recording
        )
        windows = [hoplite_db.get_window(result.key) for result in close_results]

        for window in windows:
            hoplite_db.insert_annotation(
                recording_id=window.recording_id,
                offsets=window.offsets,
                label=target_recording.label,
                provenance=SEARCH_PROVENANCE,
                label_type=datatypes.LabelType.UNCERTAIN,
            )
        # Commit before marking the recording finished, so a recording is
        # never marked done without its results saved.
        hoplite_db.commit()
        db.set_finish_target_recording(target_recording.id, True)
        logger.info(
            "target recording %d (%s): %d possible example(s)",
            target_recording.id,
            target_recording.label,
            len(windows),
        )
