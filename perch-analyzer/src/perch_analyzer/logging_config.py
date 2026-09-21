"""Logging setup shared by the CLI and the GUI."""

import logging
import sys
from pathlib import Path

LOG_FILENAME = "perch_analyzer.log"
_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_configured = False


def setup_logging(data_dir: Path | str | None = None, verbosity: int = 0) -> None:
    """Configure logging once, for the process.

    The root logger is deliberately left at WARNING: perch-hoplite logs every
    SQL statement it executes through absl at INFO, which floods the log file
    and slows queries down.  Only the `perch_analyzer` tree is turned up.

    Args:
      data_dir: Project directory to write `perch_analyzer.log` into. If None,
        logs only go to the console.
      verbosity: 0 for normal, >0 for debug, <0 for quiet.
    """
    global _configured
    if _configured:
        return

    if verbosity > 0:
        app_level, console_level = logging.DEBUG, logging.DEBUG
    elif verbosity < 0:
        app_level, console_level = logging.INFO, logging.ERROR
    else:
        app_level, console_level = logging.INFO, logging.INFO

    root = logging.getLogger()
    root.setLevel(logging.WARNING)

    console = logging.StreamHandler(sys.stderr)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.addHandler(console)

    if data_dir is not None:
        log_path = Path(data_dir) / LOG_FILENAME
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)

    logging.getLogger("perch_analyzer").setLevel(app_level)
    _configured = True
