from perch_analyzer.config import config
from perch_analyzer.target_recordings import xenocanto
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl
from perch_hoplite import audio_io
from perch_analyzer.target_recordings import audio_utils

# TODO: make these configs
SAMPLE_RATE = 32000
WINDOW_SIZE_S = 5


def add_target_recording_from_file(
    db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    label: str,
    filename: str,
    offset_s: float,
):
    audio = audio_io.load_audio_window(
        filepath=filename,
        offset_s=offset_s,
        sample_rate=SAMPLE_RATE,
        window_size_s=WINDOW_SIZE_S,
    )

    target_recording_id = db.insert_target_recording(
        xc_id=None,
        filename=filename,
        label=label,
        audio=audio,
    )

    return target_recording_id


def add_target_recording_from_xc(
    config: config.Config,
    db: db.AnalyzerDB,
    ebird_6_code: str,
    call_type: str,
    num_recordings: int,
):
    xc_ids = xenocanto.get_xc_ids(config, ebird_6_code, call_type)

    # TODO: filter out the existing xc_ids that are in the database

    xc_ids = xc_ids[:num_recordings]

    for xc_id in xc_ids:
        audio = audio_io.load_xc_audio(f"xc{xc_id}", SAMPLE_RATE)

        # we only take a single peak because we do not need multiple target recordings from a single xc recording
        peaks = audio_utils.slice_peaked_audio(
            audio,
            sample_rate_hz=SAMPLE_RATE,
            interval_length_s=WINDOW_SIZE_S,
            max_intervals=1,
        )
        for peak in peaks:
            audio_slice = audio[peak[0] : peak[1]]

            db.insert_target_recording(
                xc_id=int(xc_id),
                filename=None,
                label=ebird_6_code,
                audio=audio_slice,
            )
