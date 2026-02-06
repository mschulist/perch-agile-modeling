import dataclasses
from perch_hoplite.db import sqlite_usearch_impl, interface
import numpy as np
from ml_collections import config_dict
from tqdm import tqdm

old_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite_old")
new_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
    "data/hoplite", sqlite_usearch_impl.get_default_usearch_config(1536)
)

# new_recordings = new_db.get_all_recordings()
# old_recordings = old_db.get_all_recordings()

# assert len(new_recordings) == len(old_recordings)

# for i in tqdm(range(len(new_recordings))):
#     assert new_recordings[i] == old_recordings[i]

# new_windows = new_db.get_all_windows()
# old_windows = old_db.get_all_windows()

# assert len(new_windows) == len(old_windows)


@dataclasses.dataclass
class Annotation:
    """Annotation info."""

    id: int
    window_id: int
    label: str
    label_type: interface.LabelType
    provenance: str


def np_list_to_list(np_list):
    return np.frombuffer(np_list, dtype=np.float32).tolist()


def get_all_annotations(cursor):
    cursor.execute("select * from annotations")

    annotations: list[Annotation] = []
    columns = [col[0] for col in cursor.description]
    for result in cursor.fetchall():
        annotation = Annotation(**dict(zip(columns, result)))
        annotation.label_type = interface.LabelType(annotation.label_type)
        annotations.append(annotation)
    return annotations


print(len(new_db.get_all_annotations()))
old_cursor = old_db._get_cursor()
print(len(get_all_annotations(old_cursor)))

exit()


# old_cursor = old_db._get_cursor()
# # print(np_list_to_list(old_db.get_window(1).offsets))
# # print(get_all_annotations(old_cursor))
# # exit()

old_metadata = old_db.get_metadata(None)


for k, v in old_metadata.items():
    new_db.insert_metadata(k, v)

new_db.commit()

deployments = list(old_db.get_all_deployments())
deployments.sort(key=lambda x: x.id)

for deployment in deployments:
    new_db.insert_deployment(deployment.name, deployment.project)

new_db.commit()

recordings = list(old_db.get_all_recordings())
recordings.sort(key=lambda x: x.id)

for recording in tqdm(recordings):
    new_db.insert_recording(
        recording.filename, recording.datetime, recording.deployment_id
    )

new_db.commit()

windows = list(old_db.get_all_windows())
windows.sort(key=lambda x: x.id)

for window in tqdm(windows):
    new_db.insert_window(window.recording_id, np_list_to_list(window.offsets))

new_db.commit()

old_cursor = old_db._get_cursor()

annotations = get_all_annotations(old_cursor)
annotations.sort(key=lambda x: x.id)

for annotation in tqdm(annotations):
    window = new_db.get_window(annotation.window_id)

    new_db.insert_annotation(
        recording_id=window.recording_id,
        offsets=window.offsets,
        label=annotation.label,
        label_type=annotation.label_type,
        provenance=annotation.provenance,
    )

new_db.commit()
