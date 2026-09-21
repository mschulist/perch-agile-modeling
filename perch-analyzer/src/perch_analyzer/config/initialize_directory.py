import logging
from pathlib import Path

from perch_analyzer.config.config import CONFIG_FILENAME, Config

logger = logging.getLogger(__name__)

DEFAULT_DIRS = {
    "classifiers_dir": "classifiers",
    "classifier_outputs_dir": "classifier_outputs",
    "precomputed_windows_dir": "precomputed_windows",
    "target_recordings_dir": "target_recordings",
}


def check_initialized(data_path: Path | str) -> bool:
    return (Path(data_path) / CONFIG_FILENAME).exists()


def create_default_config(
    data_path: str,
    project_name: str,
    user_name: str,
    embedding_model: str,
) -> Config:
    return Config(
        data_path=data_path,
        project_name=project_name,
        user_name=user_name,
        db_path="analyzer.db",
        hoplite_db_path="hoplite",
        embedding_model=embedding_model,
        xenocanto_api_key="",
        **DEFAULT_DIRS,
    )


def initialize_directory(
    data_path: Path,
    project_name: str,
    user_name: str,
    embedding_model: str,
):
    """Create (or open) a project at `data_path`.

    Safe to re-run: an existing config and hoplite database are reused rather
    than overwritten.
    """
    from perch_hoplite.db import sqlite_usearch_impl
    from perch_hoplite.zoo import model_configs

    from perch_analyzer.db.db import AnalyzerDB

    data_path = Path(data_path).expanduser().resolve()

    if check_initialized(data_path):
        config = Config.load(data_path)
        config.data_path = str(data_path)
        logger.info("reusing existing project at %s", data_path)
    else:
        if not project_name or not user_name or not embedding_model:
            raise ValueError(
                "project_name, user_name and embedding_model must be provided "
                "if a project does not exist"
            )
        config = create_default_config(
            str(data_path),
            project_name=project_name,
            user_name=user_name,
            embedding_model=embedding_model,
        )
        data_path.mkdir(exist_ok=True, parents=True)
        config.to_file()

    hoplite_path = data_path / config.hoplite_db_path
    if hoplite_path.exists():
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(str(hoplite_path))
    else:
        if not embedding_model:
            raise ValueError(
                "embedding model must be passed if the hoplite db does not exist"
            )
        embed_dim = model_configs.get_preset_model_config(embedding_model).embedding_dim
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(hoplite_path),
            sqlite_usearch_impl.get_default_usearch_config(embed_dim),
        )

    analyzer_db = AnalyzerDB(config)

    for dir_key in DEFAULT_DIRS:
        (data_path / getattr(config, dir_key)).mkdir(exist_ok=True, parents=True)

    return analyzer_db, hoplite_db
