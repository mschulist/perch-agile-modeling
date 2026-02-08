from perch_hoplite.db import sqlite_usearch_impl
from ml_collections import config_dict
from datetime import datetime as dt
import sqlite3

hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite")

BATCH_SIZE = 32678


def get_windows_faster(cursor: sqlite3.Cursor, window_ids: list[int]):
    """Returns list[(window_id, recording_id, offsets)]"""

    placeholders = ",".join("?" * len(window_ids))
    cursor.execute(
        f"""
        SELECT *
        FROM windows
        WHERE id IN ({placeholders})
        """,
        window_ids,
    )
    results = cursor.fetchall()

    return results


before = dt.now()

batch_window_ids = list(range(1, BATCH_SIZE + 1))
filenames: list[str] = []
offsets: list[float] = []

windows = hoplite_db.get_all_windows(
    filter=config_dict.create(isin=dict(id=batch_window_ids))
)

recording_id_to_filename: dict[int, str] = {}

recording_ids: set[int] = set([window.recording_id for window in windows])

for recording_id in recording_ids:
    if recording_id not in recording_id_to_filename:
        recording = hoplite_db.get_recording(recording_id)
        recording_id_to_filename[recording_id] = recording.filename

for window in windows:
    filenames.append(recording_id_to_filename[window.recording_id])
    offsets.append(float(window.offsets[0]))

print(f"took {dt.now() - before}")
