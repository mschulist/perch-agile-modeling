from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from perch_hoplite.db import sqlite_usearch_impl
from sklearn.manifold import TSNE
from tqdm import tqdm

desired_labels = {
    "westan_song",
    "bkbwoo_call",
    "herwar_song",
    "towsol_song",
    "soogro1_song",
    "herthr_song",
    "haiwoo_call",
    "gockin_call",
    "brncre_call",
    "gockin_song",
}


@dataclass
class AnnotationWithEmbedding:
    window_id: int
    label: str
    embedding: np.ndarray


hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite")

WORK_DIR = Path("data/baseline_test")
WORK_DIR.mkdir(exist_ok=True, parents=True)


with open(WORK_DIR / "annotated_window_ids.txt") as f:
    annotated_window_ids = []
    for line in f.readlines():
        annotated_window_ids.append(int(line))


annotations: list[AnnotationWithEmbedding] = []

embds = hoplite_db.get_embeddings_batch(annotated_window_ids)

for i, window_id in tqdm(
    enumerate(annotated_window_ids), total=len(annotated_window_ids)
):
    embedding = embds[i]
    anns = hoplite_db.get_window_annotations(window_id)

    for annotation in anns:
        if annotation.label not in desired_labels:
            continue
        ann = AnnotationWithEmbedding(window_id, annotation.label, embedding)
        annotations.append(ann)


embeddings = np.array([x.embedding for x in annotations])
labels = [x.label for x in annotations]

tsne_embeddings = TSNE().fit_transform(embeddings)

plt.figure(figsize=(12, 8))
unique_labels = np.array(sorted(set(labels)))
label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
label_indices = np.array([label_to_idx[label] for label in labels])

scatter = plt.scatter(
    tsne_embeddings[:, 0],
    tsne_embeddings[:, 1],
    c=label_indices,
    cmap=plt.get_cmap("tab10", len(unique_labels)),
    alpha=0.6,
    vmin=-0.5,
    vmax=len(unique_labels) - 0.5,
)
cbar = plt.colorbar(scatter, ticks=range(len(unique_labels)))
cbar.set_ticklabels(unique_labels.tolist())
cbar.set_label("Label")
plt.xlabel("t-SNE 1")
plt.ylabel("t-SNE 2")
plt.title("t-SNE Visualization of Embeddings")
plt.savefig(WORK_DIR / "tsne_plot.pdf", bbox_inches="tight")
plt.show()
