from chirp.projects.agile2 import colab_utils  # type: ignore
from chirp.projects.agile2 import source_info  # type: ignore
import os


def setup_perch_db(
    project_id: int,
    dataset_base_path: str,
    dataset_fileglob: str,
    model_choice: str = "perch_8",
):
    audio_glob = source_info.AudioSourceConfig(
        dataset_name=str(project_id),
        base_path=dataset_base_path,
        file_glob=dataset_fileglob,
        min_audio_len_s=1.0,
        target_sample_rate_hz=-2,
        shard_len_s=60.0,
    )

    db_path = f"data/perch_db/perch_{project_id}.db"

    if os.path.exists(db_path):
        return False

    configs = colab_utils.load_configs(
        source_info.AudioSources((audio_glob,)),
        db_path=f"data/perch_db/perch_{project_id}.db",
        model_config_key=model_choice,
        db_key="sqlite_usearch",
    )

    configs.db_config.load_db()
    return True
