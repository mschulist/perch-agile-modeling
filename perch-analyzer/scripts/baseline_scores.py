from pathlib import Path

import numpy as np
from ml_collections import config_dict
from perch_hoplite import audio_io
from perch_hoplite.db import sqlite_usearch_impl
from perch_hoplite.taxonomy import namespace_db
from perch_hoplite.zoo import model_configs
from tqdm import tqdm

namespace = namespace_db.load_db()

print(namespace.mappings.keys())


hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite")

WORK_DIR = Path("data/baseline_test")
WORK_DIR.mkdir(exist_ok=True, parents=True)

annotations = hoplite_db.get_all_annotations()

class_names = hoplite_db.get_all_labels()
species = set([x.split("_")[0] for x in class_names])

ebirdcode_to_species_mapping = namespace.mappings.get("ebird2022_clements_to_species")

species_perch = [
    ebirdcode_to_species_mapping.reverse().mapped_pairs.get(x) for x in species
]


print(species_perch)


def get_annotated_window_ids():
    # window_ids is the list of window ids that have annotations
    window_ids = []

    file = WORK_DIR / "annotated_window_ids.txt"

    if file.exists():
        with file.open("r") as f:
            for line in f.readlines():
                window_ids.append(int(line.strip()))
        return list(set(window_ids))

    for ann in tqdm(annotations):
        window_ids_gathered = hoplite_db.get_all_windows(
            filter=config_dict.create(
                approx=dict(offsets=ann.offsets),
                eq=dict(recording_id=ann.recording_id),
            )
        )
        assert len(window_ids_gathered) == 1

        window_ids.append(window_ids_gathered[0].id)

    with open(WORK_DIR / "annotated_window_ids.txt", "w") as f:
        for window_id in window_ids:
            f.write(f"{window_id}\n")

    return window_ids


window_ids = get_annotated_window_ids()

# now we get the score from Perch 2.0 and BirdNET 2.1

perch_model = model_configs.load_model_by_name("perch_v2")
birdnet_model = model_configs.load_model_by_name("birdnet_V2.3")

ARU_base_path = Path("/home/mschulist/caples_sound/ARU_data_all")

perch_classes = perch_model.class_list["labels"].classes

perch_logits_mask = np.zeros(len(perch_classes), dtype=np.bool)
for i, label in enumerate(perch_classes):
    if label.lower() in species_perch:
        perch_logits_mask[i] = True

perch_classes_subset = np.array(perch_classes)[perch_logits_mask]

with open(WORK_DIR / "birdnet_classes.txt") as f:
    birdnet_classes = []
    for line in f.readlines():
        birdnet_classes.append(line.split("_")[0])

birdnet_logits_mask = np.zeros(len(birdnet_classes), dtype=np.bool)
for i, label in enumerate(birdnet_classes):
    if label.lower() in species_perch:
        birdnet_logits_mask[i] = True

birdnet_classes_subset = np.array(birdnet_classes)[birdnet_logits_mask]

with open(WORK_DIR / "perch_outputs.csv", "w") as f:
    f.write("window_id,class,logit\n")

with open(WORK_DIR / "birdnet_outputs.csv", "w") as f:
    f.write("window_id,class,logit\n")


for window_id in tqdm(window_ids):
    window = hoplite_db.get_window(window_id)
    recording = hoplite_db.get_recording(window.recording_id)
    filename = recording.filename

    full_path = str(ARU_base_path / filename)

    perch_audio = audio_io.load_audio_window(
        full_path, window.offsets[0], perch_model.sample_rate, 5
    )

    birdnet_audio = audio_io.load_audio_window(
        full_path, window.offsets[0], birdnet_model.sample_rate, 3
    )

    perch_output = perch_model.embed(perch_audio)
    birdnet_output = birdnet_model.embed(birdnet_audio)

    perch_logits = perch_output.logits["label"][0][perch_logits_mask]
    birdnet_logits = birdnet_output.logits["birdnet_v2_1"][0][0][birdnet_logits_mask]

    with open(WORK_DIR / "perch_outputs.csv", "a") as f:
        for i, logit in enumerate(perch_logits):
            f.write(f"{window_id},{perch_classes_subset[i]},{logit}\n")

    with open(WORK_DIR / "birdnet_outputs.csv", "a") as f:
        for i, logit in enumerate(birdnet_logits):
            f.write(f"{window_id},{birdnet_classes_subset[i]},{logit}\n")
