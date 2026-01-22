from perch_analyzer.config import config
from perch_analyzer.target_recordings import xenocanto
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl
from perch_hoplite import audio_io


def add_target_recording_from_file(
    db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    label: str,
    filename: str,
    offset_s: float,
):
    sample_rate = hoplite_db.get_metadata("model_config").model_config.sample_rate  # type: ignore
    window_size_s = hoplite_db.get_metadata("model_config").model_config.window_size_s  # type: ignore

    audio = audio_io.load_audio_window(
        filepath=filename,
        offset_s=offset_s,
        sample_rate=sample_rate,
        window_size_s=window_size_s,
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
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    ebird_6_code: str,
    call_type: str,
    num_recordings: int,
):
    xc_ids = xenocanto.get_xc_ids(config, ebird_6_code, call_type)

    # TODO: filter out the existing xc_ids that are in the database

    xc_ids = xc_ids[:num_recordings]
    
    
