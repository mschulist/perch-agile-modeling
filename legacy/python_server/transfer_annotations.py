from lib.perch_utils.projects import load_hoplite_db
from ml_collections import config_dict
from tqdm import tqdm


old_db = load_hoplite_db(1)
new_db = load_hoplite_db(2)

annotations = old_db.get_all_annotations()

for ann in tqdm(annotations):
    window = old_db.get_window(ann.window_id)
    recording = old_db.get_recording(window.recording_id)

    filename = recording.filename
    offsets = window.offsets

    new_window = new_db.match_window_ids(
        recordings_filter=config_dict.create(eq=dict(filename=filename)),
        windows_filter=config_dict.create(eq=dict(offsets=offsets)),
    )

    if not new_window:
        print(ann, window, recording, "not found")
        continue

    new_db.insert_annotation(
        new_window[0],
        ann.label,
        label_type=ann.label_type,
        provenance=ann.provenance,
        skip_duplicates=True,
    )

new_db.commit()
print(
    f"inserted {len(new_db.get_all_annotations())} annotations into new db; old db has {len(old_db.get_all_annotations())} annotations"
)
