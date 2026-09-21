import logging

from perch_hoplite import audio_io
from perch_hoplite.db import sqlite_usearch_impl

from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_analyzer.target_recordings import audio_utils, xenocanto

logger = logging.getLogger(__name__)

# TODO: make these configs
SAMPLE_RATE = 32000
WINDOW_SIZE_S = 5


def add_target_recording_from_file(
    db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
    label: str,
    filename: str,
    offset_s: float,
) -> int:
    audio = audio_io.load_audio_window(
        filepath=filename,
        offset_s=offset_s,
        sample_rate=SAMPLE_RATE,
        window_size_s=WINDOW_SIZE_S,
    )

    return db.insert_target_recording(
        xc_id=None,
        filename=filename,
        label=label,
        audio=audio,
    )


def add_target_recording_from_xc(
    config: config.Config,
    db: db.AnalyzerDB,
    ebird_6_code: str,
    call_type: str,
    num_recordings: int,
) -> int:
    """Download up to `num_recordings` new Xeno-canto recordings for a species.

    Returns the number of target recordings added.
    """
    xc_ids = xenocanto.get_xc_ids(config, ebird_6_code, call_type)

    # Skip recordings we already have *before* truncating, so asking for N
    # recordings gets N new ones rather than N candidates that may all be dupes.
    existing_xc_ids = db.get_target_recording_xc_ids()
    new_xc_ids = [xc_id for xc_id in xc_ids if int(xc_id) not in existing_xc_ids]
    skipped = len(xc_ids) - len(new_xc_ids)
    if skipped:
        logger.debug("skipping %d xc id(s) already present in the database", skipped)

    added = 0
    for xc_id in new_xc_ids[:num_recordings]:
        audio = audio_io.load_xc_audio(f"xc{xc_id}", SAMPLE_RATE)

        # A single peak is enough: we do not need multiple target recordings
        # out of one Xeno-canto recording.
        peaks = audio_utils.slice_peaked_audio(
            audio,
            sample_rate_hz=SAMPLE_RATE,
            interval_length_s=WINDOW_SIZE_S,
            max_intervals=1,
        )
        for peak in peaks:
            db.insert_target_recording(
                xc_id=int(xc_id),
                filename=None,
                label=ebird_6_code,
                audio=audio[peak[0] : peak[1]],
            )
            added += 1

    logger.info("added %d target recording(s) for %s", added, ebird_6_code)
    return added
