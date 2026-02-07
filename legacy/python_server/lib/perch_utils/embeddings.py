import os
from perch_hoplite.agile.convert_legacy import convert_tfrecords


def convert_legacy_tfrecords(
    project_id: int,
    embeddings_path: str,
    db_type: str,
):
    db_path = f"data/perch_db/perch_{project_id}.db"
    if os.path.exists(db_path):
        raise ValueError(f"DB path {db_path} already exists.")
    convert_tfrecords(
        embeddings_path=embeddings_path,
        db_path=db_path,
        db_type=db_type,
        dataset_name=str(project_id),
    )

    return True
