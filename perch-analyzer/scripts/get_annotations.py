from collections import defaultdict

from ml_collections import config_dict
from perch_hoplite.db import sqlite_usearch_impl
from tqdm import tqdm

hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite")

species = [
    "amerob",
    "bkbwoo",
    "btywar",
    "comnig",
    "dusfly",
    "herthr",
    "herwar",
    "lazbun",
    "mouqua",
    "olsfly",
    "rebnut",
    "rebsap",
    "soogro1",
    "westan",
    "wewpew",
]

call_types = ["song", "call"]

species_all = [f"{s}_{t}" for s in species for t in call_types]

year = 2021

annotations = hoplite_db.get_all_annotations(
    config_dict.create(isin=dict(label=species_all))
)

years = defaultdict(int)

for ann in annotations:
    recording = hoplite_db.get_recording(ann.recording_id)
    y = recording.filename[0:4]
    years[y] += 1

print(years)
exit()


window_ids = hoplite_db.match_window_ids(
    annotations_filter=config_dict.create(isin=dict(label=species_all))
)

wanted_windows = []

for window_id in tqdm(window_ids):
    window = hoplite_db.get_window(window_id)
    recording = hoplite_db.get_recording(window.recording_id)
    annotation = hoplite_db.get_all_annotations(
        config_dict.create(
            approx=dict(offsets=window.offsets),
            eq=dict(recording_id=recording.id),
        )
    )[0]

    if "2021" in recording.filename:
        print(recording.filename, annotation.label)
        wanted_windows.append(window_id)

print(wanted_windows)
