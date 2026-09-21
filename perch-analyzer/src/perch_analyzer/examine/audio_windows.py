"""Rendering audio windows to disk as a .wav plus a spectrogram .png.

The rendered files live in the project's `precomputed_windows` directory and
are served to the GUI as static files, so each window only ever gets rendered
once.
"""

import logging
import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from perch_hoplite import audio_io
from perch_hoplite.db import datatypes
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from scipy.io import wavfile

from perch_analyzer.config import config

logger = logging.getLogger(__name__)

# Matches the previous matplotlib default of a 640x480 figure.
FIGURE_SIZE_INCHES = (6.4, 4.8)
FIGURE_DPI = 100

_render_settings_cache: dict[str, "RenderSettings"] = {}
_render_settings_lock = threading.Lock()


@dataclass(frozen=True)
class RenderSettings:
    """The bits of hoplite metadata needed to cut a window out of a recording."""

    sample_rate: int
    window_size_s: float
    base_path: str


def get_render_settings(hoplite_db: SQLiteUSearchDB) -> RenderSettings:
    """Read (and cache) the render settings for a hoplite database.

    These come from two metadata queries that would otherwise run once per
    window rendered.
    """
    key = str(hoplite_db.db_path)
    with _render_settings_lock:
        cached = _render_settings_cache.get(key)
    if cached is not None:
        return cached

    # TODO: make this less cursed/more robust
    model_config = hoplite_db.get_metadata("model_config").model_config
    audio_globs = hoplite_db.get_metadata("audio_sources").audio_globs
    settings = RenderSettings(
        sample_rate=int(model_config.sample_rate),  # type: ignore[union-attr]
        window_size_s=float(model_config.window_size_s),  # type: ignore[union-attr]
        base_path=audio_globs[0]["base_path"],  # type: ignore[index]
    )

    with _render_settings_lock:
        _render_settings_cache[key] = settings
    return settings


def window_asset_paths(config: config.Config, window_id: int) -> tuple[Path, Path]:
    """Get the (audio, spectrogram) paths for a window, rendered or not."""
    windows_dir = Path(config.data_path) / config.precomputed_windows_dir
    return windows_dir / f"{window_id}.wav", windows_dir / f"{window_id}.png"


def get_audio_window_path(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    window_id: int,
    settings: RenderSettings | None = None,
) -> tuple[Path, Path]:
    """Get the audio and spectrogram paths for a window, rendering if needed."""
    recording_file, spec_file = window_asset_paths(config, window_id)

    if not recording_file.exists() or not spec_file.exists():
        if settings is None:
            settings = get_render_settings(hoplite_db)
        window = hoplite_db.get_window(window_id)
        recording = hoplite_db.get_recording(window.recording_id)
        flush_window_to_disk(
            recording=recording,
            window=window,
            sample_rate=settings.sample_rate,
            window_size_s=settings.window_size_s,
            base_path=settings.base_path,
            recording_file=recording_file,
            spec_file=spec_file,
        )

    return recording_file.absolute(), spec_file.absolute()


def precompute_windows(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    window_ids: Sequence[int],
    max_workers: int = 4,
) -> None:
    """Render any windows in `window_ids` that are not on disk yet.

    Rendering is IO- and CPU-bound in roughly equal measure and is independent
    per window, so missing windows are rendered in parallel.
    """
    missing = [
        window_id
        for window_id in window_ids
        if not all(path.exists() for path in window_asset_paths(config, window_id))
    ]
    if not missing:
        return

    logger.info("rendering %d window(s)", len(missing))
    settings = get_render_settings(hoplite_db)

    def render(window_id: int) -> None:
        # SQLite connections cannot cross threads.
        thread_db = hoplite_db.thread_split()
        try:
            get_audio_window_path(config, thread_db, window_id, settings=settings)
        except Exception:
            logger.exception("failed to render window %d", window_id)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(render, missing))


@lru_cache(maxsize=4)
def _melspec_layer(sample_rate: int):
    # Imported lazily: perch_hoplite.agile.embedding_display pulls in IPython
    # and ipywidgets, which cost ~0.8s and are only needed when rendering.
    from perch_hoplite.agile import embedding_display

    return embedding_display.get_melspec_layer(sample_rate)


def flush_window_to_disk(
    recording: datatypes.Recording,
    window: datatypes.Window,
    sample_rate: int,
    window_size_s: float,
    base_path: str,
    recording_file: str | Path,
    spec_file: str | Path,
) -> None:
    logger.info("flushing window id: %s to disk", window.id)
    audio_slice = audio_io.load_audio_window_soundfile(
        f"{base_path}/{recording.filename}",
        offset_s=window.offsets[0],
        window_size_s=window_size_s,
        sample_rate=sample_rate,
    )

    wavfile.write(recording_file, sample_rate, np.float32(audio_slice))

    if audio_slice.shape[0] < sample_rate / 100 + 1:
        # Center pad if audio is too short.
        zs = np.zeros([sample_rate // 10], dtype=audio_slice.dtype)
        audio_slice = np.concatenate([zs, audio_slice, zs], axis=0)
    melspec = _melspec_layer(sample_rate)(audio_slice).T  # type: ignore[operator]

    _write_spectrogram(melspec, sample_rate, spec_file)


def _write_spectrogram(
    melspec: np.ndarray, sample_rate: int, spec_file: str | Path
) -> None:
    """Write a melspec to a PNG.

    Uses an explicit Agg figure rather than `pyplot`: pyplot keeps global
    figure state that is neither thread-safe nor freed unless closed, and
    windows are rendered from a thread pool.
    """
    from librosa import display as librosa_display

    figure = Figure(figsize=FIGURE_SIZE_INCHES, dpi=FIGURE_DPI)
    FigureCanvasAgg(figure)
    axes = figure.add_subplot(111)
    librosa_display.specshow(
        melspec,
        sr=sample_rate,
        y_axis="mel",
        x_axis="time",
        hop_length=sample_rate // 100,
        cmap="Greys",
        ax=axes,
    )
    with Path(spec_file).open("wb") as f:
        figure.savefig(f)
