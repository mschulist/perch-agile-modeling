"""Project-wide services shared by every GUI page.

One `ProjectServices` is created when the GUI starts and reached through
`project()`.  It owns the config and both databases so pages never re-open
them, and it hands out per-thread hoplite handles because NiceGUI runs
blocking work on a thread pool and SQLite connections cannot cross threads.
"""

import logging
import threading
from collections.abc import Sequence
from functools import cached_property
from pathlib import Path

from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB

from perch_analyzer.app_context import AppContext
from perch_analyzer.config.config import Config
from perch_analyzer.db.db import AnalyzerDB
from perch_analyzer.examine import audio_windows

logger = logging.getLogger(__name__)

_project: "ProjectServices | None" = None


class ProjectServices:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self._thread_local = threading.local()

    @property
    def config(self) -> Config:
        return self.ctx.config

    @cached_property
    def analyzer_db(self) -> AnalyzerDB:
        return self.ctx.analyzer_db

    @property
    def hoplite_db(self) -> SQLiteUSearchDB:
        """A hoplite handle owned by the calling thread.

        `thread_split()` opens a fresh SQLite connection and usearch index, so
        the result is cached per thread rather than per call.
        """
        db = getattr(self._thread_local, "hoplite_db", None)
        if db is None:
            db = self.ctx.hoplite_db.thread_split()
            self._thread_local.hoplite_db = db
        return db

    def window_urls(self, window_id: int) -> tuple[str, str]:
        """Get the (audio, spectrogram) URLs for a window, rendering if needed."""
        audio_file, spec_file = audio_windows.get_audio_window_path(
            config=self.config, hoplite_db=self.hoplite_db, window_id=window_id
        )
        return data_url(self.config, audio_file), data_url(self.config, spec_file)

    def precompute_windows(self, window_ids: Sequence[int]) -> None:
        audio_windows.precompute_windows(self.config, self.hoplite_db, window_ids)


def data_url(config: Config, path: Path | str) -> str:
    """Turn a path inside the project directory into a URL the browser can fetch.

    The GUI serves the project directory at `/data`, from the same origin as
    the pages themselves, so a relative URL is all that is needed.
    """
    return "/data/" + str(Path(path).relative_to(Path(config.data_path)))


def set_project(services: ProjectServices) -> None:
    global _project
    _project = services


def project() -> ProjectServices:
    if _project is None:
        raise RuntimeError("GUI project services have not been initialized")
    return _project
