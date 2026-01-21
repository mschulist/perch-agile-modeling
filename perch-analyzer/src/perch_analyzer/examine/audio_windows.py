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


def get_audio_window_path(
    config: config.Config, hoplite_db: SQLiteUSearchDB, window_id: int
) -> tuple[Path, Path]:
    recording_file = Path(config.precomputed_windows_dir) / f"{window_id}.wav"
    spec_file = Path(config.precomputed_windows_dir) / f"{window_id}.png"

    # TODO: get the sample rate from this
    sample_rate = str(hoplite_db.get_metadata("sample_rate"))
    base_path = str(hoplite_db.get_metadata("base_path"))
    window_size_s = str(hoplite_db.get_metadata("window_size_s"))

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

    return recording_file, spec_file


def flush_window_to_disk(
    recording: interface.Recording,
    window: interface.Window,
    sample_rate: int,
    window_size_s: float,
    base_path: str,
    recording_file: str | Path,
    spec_file: str | Path,
):
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
