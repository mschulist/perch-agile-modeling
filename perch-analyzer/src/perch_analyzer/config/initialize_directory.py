from pathlib import Path
from perch_hoplite.db import sqlite_usearch_impl
from perch_analyzer.db.db import AnalyzerDB
from perch_analyzer.config.config import Config
from perch_hoplite.zoo import model_configs


def check_initialized(data_path: Path):
    return (data_path / "config.yaml").exists()


def initialize_directory(
    data_path: Path,
    project_name: str,
    user_name: str,
    embedding_model: str,
):
    # first initialize the config
    if (data_path / "config.yaml").exists():
        config = Config.load(str(data_path))
    else:
        if not project_name or not user_name or not embedding_model:
            raise ValueError(
                "project_name and user_name must be provided if a project does not exist"
            )
        config = create_default_config(
            str(data_path),
            project_name=project_name,
            user_name=user_name,
            embedding_model=embedding_model,
        )

        data_path.mkdir(exist_ok=True, parents=True)
        config.to_file()

    # now initialize the databases
    if (data_path / config.hoplite_db_path).exists():
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(data_path / config.hoplite_db_path)
        )
    else:
        if not embedding_model:
            raise ValueError(
                "embedding model must be passed if the hoplite db does not exist"
            )
        embed_dim = model_configs.get_preset_model_config(embedding_model).embedding_dim
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(data_path / config.hoplite_db_path),
            sqlite_usearch_impl.get_default_usearch_config(embed_dim),
        )

    analyzer_db = AnalyzerDB(config)

    # create all of the directories
    (data_path / config.classifier_outputs_dir).mkdir(exist_ok=True, parents=True)
    (data_path / config.classifiers_dir).mkdir(exist_ok=True, parents=True)
    (data_path / config.precomputed_windows_dir).mkdir(exist_ok=True, parents=True)
    (data_path / config.target_recordings_dir).mkdir(exist_ok=True, parents=True)

    return analyzer_db, hoplite_db


def create_default_config(
    data_path: str,
    project_name: str,
    user_name: str,
    embedding_model: str,
):
    return Config(
        data_path=data_path,
        project_name=project_name,
        user_name=user_name,
        classifiers_dir="classifiers",
        classifier_outputs_dir="classifier_outputs",
        precomputed_windows_dir="precomputed_windows",
        target_recordings_dir="target_recordings",
        db_path="analyzer.db",
        throwaway_classes=[],
        hoplite_db_path="hoplite",
        train_ratio=0.8,
        max_train_examples_per_label=100,
        learning_rate=1e-3,
        weak_neg_rate=0.05,
        num_train_steps=128,
        embedding_model=embedding_model,
        xenocanto_api_key="test",
    )
