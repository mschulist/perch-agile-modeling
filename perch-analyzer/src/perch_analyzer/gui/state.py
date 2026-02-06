import reflex as rx
from perch_analyzer.config.config import Config
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl

TMP_DATA_PATH = "data"

# Global config loaded once
_config = Config.load(TMP_DATA_PATH)


class ConfigState(rx.State):
    # Serializable config
    config: Config = _config

    # Class-level database connections (shared across all instances)
    @classmethod
    def get_hoplite_db(cls) -> sqlite_usearch_impl.SQLiteUSearchDB:
        if not hasattr(cls, "_hoplite_db_instance"):
            cls._hoplite_db_instance = sqlite_usearch_impl.SQLiteUSearchDB.create(
                f"{_config.data_path}/{_config.hoplite_db_path}"
            )
        return cls._hoplite_db_instance

    @classmethod
    def get_analyzer_db(cls) -> db.AnalyzerDB:
        if not hasattr(cls, "_analyzer_db_instance"):
            cls._analyzer_db_instance = db.AnalyzerDB(_config)
        return cls._analyzer_db_instance


# type: ignore
