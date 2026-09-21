"""Lazily-opened handles to a project's config and databases.

Opening a database or parsing the config costs real time, and most commands
need only one of them, so everything here is created on first use and then
cached.
"""

from functools import cached_property
from pathlib import Path

from perch_analyzer.config.config import Config

CONFIG_FILENAME = "config.yaml"


class ProjectNotInitializedError(RuntimeError):
    """Raised when a data directory has no project in it yet."""


def is_initialized(data_dir: Path | str) -> bool:
    return (Path(data_dir) / CONFIG_FILENAME).exists()


class AppContext:
    """Everything a command needs to talk to one project."""

    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir).expanduser().resolve()

    def require_initialized(self) -> "AppContext":
        if not is_initialized(self.data_dir):
            raise ProjectNotInitializedError(
                f"data directory {self.data_dir} is not initialized yet, run "
                f"perch-analyzer init --data_dir={self.data_dir}"
            )
        return self

    @cached_property
    def config(self) -> Config:
        config = Config.load(self.data_dir)
        # The config records where it was created; trust where it was *found*
        # instead, so a project directory can be moved or mounted elsewhere.
        config.data_path = str(self.data_dir)
        return config

    @cached_property
    def analyzer_db(self):
        from perch_analyzer.db.db import AnalyzerDB

        return AnalyzerDB(self.config)

    @cached_property
    def hoplite_db(self):
        from perch_hoplite.db import sqlite_usearch_impl

        return sqlite_usearch_impl.SQLiteUSearchDB.create(str(self.hoplite_db_path))

    @property
    def hoplite_db_path(self) -> Path:
        return self.data_dir / self.config.hoplite_db_path

    def hoplite_db_for_thread(self):
        """Get a hoplite handle usable from the calling thread.

        SQLite connections cannot be shared across threads, so each thread
        needs its own.
        """
        return self.hoplite_db.thread_split()
