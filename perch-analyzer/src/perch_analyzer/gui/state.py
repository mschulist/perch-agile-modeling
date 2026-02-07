import reflex as rx
import os
from pathlib import Path
from perch_analyzer.config.config import Config
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl

# Get data path from environment variable, fallback to "data" for backwards compatibility
DATA_DIR = os.environ.get("PERCH_ANALYZER_DATA_DIR", "data")

# Global config loaded once
_config = Config.load(DATA_DIR)

# Override the data_path in config with the absolute path we're using
# This ensures all database connections use the correct absolute path
_config.data_path = str(Path(DATA_DIR).absolute())


class ConfigState(rx.State):
    # Serializable config
    config: Config = _config

    # Editable fields
    edit_user_name: str = _config.user_name
    edit_project_name: str = _config.project_name
    edit_xenocanto_api_key: str = _config.xenocanto_api_key

    @rx.event
    def set_edit_user_name(self, value: str):
        self.edit_user_name = value

    @rx.event
    def set_edit_project_name(self, value: str):
        self.edit_project_name = value

    @rx.event
    def set_edit_xenocanto_api_key(self, value: str):
        self.edit_xenocanto_api_key = value

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

    @rx.event
    def save_config_changes(self):
        """Save the editable config fields to disk."""
        self.config.user_name = self.edit_user_name
        self.config.project_name = self.edit_project_name
        self.config.xenocanto_api_key = self.edit_xenocanto_api_key
        self.config.to_file()
        # Update global config
        global _config
        _config = self.config


# type: ignore
