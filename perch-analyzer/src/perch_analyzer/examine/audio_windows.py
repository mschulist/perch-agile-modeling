from perch_analyzer.config import config
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_hoplite.db import interface
from perch_hoplite import audio_io
from perch_hoplite.agile import embedding_display
from pathlib import Path
from librosa import display as librosa_display
import matplotlib.pyplot as plt
from scipy.io import wavfile
import numpy as np
import logging

logger = logging.getLogger(__name__)


def get_audio_window_path(
    config: config.Config, hoplite_db: SQLiteUSearchDB, window_id: int
) -> tuple[Path, Path]:
    recording_file = (
        Path(config.data_path) / config.precomputed_windows_dir / f"{window_id}.wav"
    )
    spec_file = (
        Path(config.data_path) / config.precomputed_windows_dir / f"{window_id}.png"
    )

    # TODO: make this less cursed/more robust
    model_config = hoplite_db.get_metadata("model_config").model_config
    sample_rate = model_config.sample_rate  # type: ignore
    window_size_s = model_config.window_size_s  # type: ignore
    audio_globs = hoplite_db.get_metadata("audio_sources").audio_globs
    base_path = audio_globs[0]["base_path"]  # type: ignore

    if not recording_file.exists() or not spec_file.exists():
        window = hoplite_db.get_window(window_id)
        recording = hoplite_db.get_recording(window.recording_id)
        flush_window_to_disk(
            recording=recording,
            window=window,
            sample_rate=int(sample_rate),
            window_size_s=float(window_size_s),
            base_path=base_path,
            recording_file=recording_file,
            spec_file=spec_file,
        )

    return recording_file.absolute(), spec_file.absolute()


def flush_window_to_disk(
    recording: interface.Recording,
    window: interface.Window,
    sample_rate: int,
    window_size_s: float,
    base_path: str,
    recording_file: str | Path,
    spec_file: str | Path,
):
    logger.info(f"flushing window id: {window.id} to disk")
    audio_slice = audio_io.load_audio_window_soundfile(
        f"{base_path}/{recording.filename}",
        offset_s=window.offsets[0],
        window_size_s=window_size_s,
        sample_rate=sample_rate,
    )

    wavfile.write(recording_file, sample_rate, np.float32(audio_slice))

    melspec_layer = embedding_display.get_melspec_layer(sample_rate)
    if audio_slice.shape[0] < sample_rate / 100 + 1:
        # Center pad if audio is too short.
        zs = np.zeros([sample_rate // 10], dtype=audio_slice.dtype)
        audio_slice = np.concatenate([zs, audio_slice, zs], axis=0)
    melspec = melspec_layer(audio_slice).T  # type: ignore

    librosa_display.specshow(
        melspec,
        sr=sample_rate,
        y_axis="mel",
        x_axis="time",
        hop_length=sample_rate // 100,
        cmap="Greys",
    )
    with Path(spec_file).open("wb") as f:
        plt.savefig(f)
    plt.close()
