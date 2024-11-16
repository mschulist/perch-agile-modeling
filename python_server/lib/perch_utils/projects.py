from chirp.projects.agile2 import colab_utils, source_info
from chirp.projects.hoplite import sqlite_usearch_impl
import os


def get_hoplite_db_path(project_id: int) -> str:
    """
    Gets the path to the hoplite db for the project.
    """
    return f"data/hoplite_db/hoplite_{project_id}.db"


def load_hoplite_db(project_id: int):
    db_path = get_hoplite_db_path(project_id)
    return sqlite_usearch_impl.SQLiteUsearchDB.create(db_path)


def setup_hoplite_db(
    project_id: int,
    dataset_base_path: str,
    dataset_fileglob: str,
    model_choice: str = "perch_8",
):
    """
    Setup the hoplite db for the project.

    Returns True if the db was successfully created, False otherwise.
    """
    audio_glob = source_info.AudioSourceConfig(
        dataset_name=str(project_id),
        base_path=dataset_base_path,
        file_glob=dataset_fileglob,
        min_audio_len_s=1.0,
        target_sample_rate_hz=-2,
        shard_len_s=60.0,
    )

    db_path = get_hoplite_db_path(project_id)

    if os.path.exists(db_path):
        return False

    configs = colab_utils.load_configs(
        source_info.AudioSources((audio_glob,)),
        db_path=db_path,
        model_config_key=model_choice,
        db_key="sqlite_usearch",
    )

    configs.db_config.load_db()
    return True
