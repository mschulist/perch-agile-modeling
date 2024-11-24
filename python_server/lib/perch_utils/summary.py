from python_server.lib.db.db import AccountsDB
from python_server.lib.models import RecordingsSummary
from .usearch_hoplite import SQLiteUsearchDBExt


def get_summary(
    project_id: int, db: AccountsDB, hoplite_db: SQLiteUsearchDBExt
) -> RecordingsSummary:
    """
    Get the summary for the project with the given id.
    """
    num_embeddings = hoplite_db.count_embeddings()
    # num labels is the number of classes in the dataset (not the number of individual labels)
    num_labels = hoplite_db.count_classes()
    num_possible_examples = len(db.get_possible_examples(project_id))
    num_source_files = hoplite_db.get_num_sources()
    hours_recordings = num_embeddings * 5 / 3600

    return RecordingsSummary(
        num_finished_possible_examples=num_possible_examples,
        num_labels=num_labels,
        num_embeddings=num_embeddings,
        num_source_files=num_source_files,
        hours_recordings=hours_recordings,
    )
