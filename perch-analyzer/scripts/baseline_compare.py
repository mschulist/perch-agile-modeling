from perch_hoplite.db import sqlite_usearch_impl
from pathlib import Path
import numpy as np
from perch_hoplite.taxonomy import namespace_db
import polars as pl
from perch_hoplite.agile import metrics
from tqdm import tqdm

namespace = namespace_db.load_db()


hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create("data/hoplite")

species_mapping = namespace.mappings.get("ebird2022_clements_to_species")
if species_mapping is None:
    raise ValueError("Missing taxonomy mapping: ebird2022_clements_to_species")
ebirdcode_to_species_mapping = species_mapping.mapped_pairs

WORK_DIR = Path("data/baseline_test")

ebirdcode_to_species_mapping = {
    k.lower(): v for k, v in ebirdcode_to_species_mapping.items()
}


def load_logits_with_mapping(
    file_path: Path, mapping: dict[str, str], source_name: str
):
    df = pl.read_csv(file_path).with_columns(
        class_key=pl.col("class").cast(pl.String).str.to_lowercase().str.strip_chars()
    )

    mapping_keys = list(mapping.keys())
    unmapped = (
        df.select(pl.col("class_key").unique().sort())
        .filter(~pl.col("class_key").is_in(mapping_keys))
        .get_column("class_key")
        .to_list()
    )

    if unmapped:
        preview = ", ".join(unmapped[:20])
        raise ValueError(
            f"{source_name}: {len(unmapped)} unmapped class keys. First 20: {preview}"
        )

    return df.with_columns(label=pl.col("class_key").replace_strict(mapping)).drop(
        "class_key"
    )


perch_logits = load_logits_with_mapping(
    WORK_DIR / "perch_outputs.csv", ebirdcode_to_species_mapping, "perch_outputs"
)
birdnet_logits = load_logits_with_mapping(
    WORK_DIR / "birdnet_outputs.csv", ebirdcode_to_species_mapping, "birdnet_outputs"
)
transfer_logits = pl.read_csv(WORK_DIR / "transfer_outputs.csv")


def get_label_for_window_id(window_id: int):
    anns = hoplite_db.get_window_annotations(window_id)

    labels = [x.label for x in anns]
    return list(set([x.split("_")[0] for x in labels]))


def logits_and_multihot_for_windows(
    logits_df: pl.DataFrame,
    annotation_lookup,
    window_ids: list[int] | None = None,
    label_order: list[str] | None = None,
    fill_value: float = np.nan,
):
    """Build aligned logit and multi-hot annotation matrices.

    Args:
        logits_df: Polars DataFrame with columns: `window_id`, `label`, `logit`.
        annotation_lookup: Callable that takes `window_id` and returns labels for that window.
        window_ids: Optional explicit window order. Defaults to sorted unique window IDs in df.
        label_order: Optional explicit label order. Defaults to sorted unique labels in df.
        fill_value: Value used when a (label, window) score is missing.

    Returns:
        tuple[np.ndarray, np.ndarray, list[str], list[int]]:
            - logits: shape (n_labels, n_windows)
            - annotations: shape (n_labels, n_windows), binary multi-hot
            - labels: ordered labels for matrix row indices
            - windows: ordered window IDs for matrix column indices
    """
    required_cols = {"window_id", "label", "logit"}
    missing = required_cols.difference(logits_df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    if window_ids is None:
        windows = sorted(logits_df.get_column("window_id").unique().to_list())
    else:
        windows = list(window_ids)

    if label_order is None:
        labels = sorted(logits_df.get_column("label").unique().to_list())
    else:
        labels = list(label_order)

    window_to_col = {w: i for i, w in enumerate(windows)}
    label_to_row = {lab: i for i, lab in enumerate(labels)}

    logits = np.full(
        (len(labels), len(windows)), fill_value=fill_value, dtype=np.float32
    )
    annotations = np.zeros((len(labels), len(windows)), dtype=np.int8)

    for window_id, label, logit in logits_df.select(
        ["window_id", "label", "logit"]
    ).iter_rows():
        col = window_to_col.get(window_id)
        row = label_to_row.get(label)
        if col is None or row is None:
            continue

        if np.isnan(logits[row, col]):
            logits[row, col] = float(logit)
        else:
            logits[row, col] = max(logits[row, col], float(logit))

    for col, window_id in tqdm(enumerate(windows), total=len(windows)):
        for ann_label in annotation_lookup(window_id):
            row = label_to_row.get(ann_label)
            if row is not None:
                annotations[row, col] = 1

    return logits, annotations, labels, windows


def top1_accuracy_from_multihot(
    logits: np.ndarray, annotations: np.ndarray, k: int = 1
) -> float:
    """Top-k accuracy where prediction is correct if any top-k label is in true multi-hot labels."""
    if logits.shape != annotations.shape:
        raise ValueError(
            f"Shape mismatch: logits {logits.shape} vs annotations {annotations.shape}"
        )

    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")

    n_windows = logits.shape[1]
    if n_windows == 0:
        return float("nan")

    valid_window_mask = np.any(~np.isnan(logits), axis=0)
    if not np.any(valid_window_mask):
        return float("nan")

    k = min(k, logits.shape[0])

    logits_valid = np.where(
        np.isnan(logits[:, valid_window_mask]), -np.inf, logits[:, valid_window_mask]
    )
    true_valid = annotations[:, valid_window_mask]

    topk_rows = np.argpartition(logits_valid, -k, axis=0)[-k:, :]
    hits = np.any(
        true_valid[topk_rows, np.arange(true_valid.shape[1])[None, :]] == 1,
        axis=0,
    )
    return float(np.mean(hits))


perch_logit_matrix, perch_annotation_matrix, perch_labels, perch_windows = (
    logits_and_multihot_for_windows(
        perch_logits,
        get_label_for_window_id,
    )
)

birdnet_logit_matrix, birdnet_annotation_matrix, birdnet_labels, birdnet_windows = (
    logits_and_multihot_for_windows(
        birdnet_logits,
        get_label_for_window_id,
    )
)

transfer_logit_matrix, transfer_annotation_matrix, transfer_labels, transfer_windows = (
    logits_and_multihot_for_windows(transfer_logits, get_label_for_window_id)
)

perch_roc_auc = metrics.roc_auc(perch_logit_matrix.T, perch_annotation_matrix.T, sample_threshold=10)
birdnet_roc_auc = metrics.roc_auc(birdnet_logit_matrix.T, birdnet_annotation_matrix.T, sample_threshold=10)
transfer_roc_auc = metrics.roc_auc(
    transfer_logit_matrix.T, transfer_annotation_matrix.T, sample_threshold=10
)


perch_top1 = top1_accuracy_from_multihot(perch_logit_matrix, perch_annotation_matrix)
birdnet_top1 = top1_accuracy_from_multihot(
    birdnet_logit_matrix, birdnet_annotation_matrix
)
transfer_top1 = top1_accuracy_from_multihot(
    transfer_logit_matrix, transfer_annotation_matrix
)

perch_top3 = top1_accuracy_from_multihot(
    perch_logit_matrix, perch_annotation_matrix, k=3
)
birdnet_top3 = top1_accuracy_from_multihot(
    birdnet_logit_matrix, birdnet_annotation_matrix, k=3
)
transfer_top3 = top1_accuracy_from_multihot(
    transfer_logit_matrix, transfer_annotation_matrix, k=3
)

perch_cmap = metrics.cmap(perch_logit_matrix.T, perch_annotation_matrix.T)
birdnet_cmap = metrics.cmap(birdnet_logit_matrix.T, birdnet_annotation_matrix.T)
transfer_cmap = metrics.cmap(transfer_logit_matrix.T, transfer_annotation_matrix.T)


def write_individual_roc_auc_scores(
    output_path: Path,
    model_name: str,
    labels: list[str],
    roc_auc_result,
    mode: str = "a",
):
    individual_scores = roc_auc_result["individual"]

    with output_path.open(mode) as f:
        f.write(f"{model_name} individual ROC AUC scores\n")
        f.write("-" * 50 + "\n")

        for label, score in zip(labels, individual_scores):
            f.write(f"{label}: {score}\n")

        if len(labels) != len(individual_scores):
            f.write(
                "WARNING: labels and individual ROC AUC scores have different lengths. "
                f"labels={len(labels)}, scores={len(individual_scores)}\n"
            )

        f.write("\n")


individual_roc_auc_path = WORK_DIR / "individual_roc_auc_scores.txt"
write_individual_roc_auc_scores(
    individual_roc_auc_path,
    "perch",
    perch_labels,
    perch_roc_auc,
    mode="w",
)
write_individual_roc_auc_scores(
    individual_roc_auc_path,
    "birdnet",
    birdnet_labels,
    birdnet_roc_auc,
)
write_individual_roc_auc_scores(
    individual_roc_auc_path,
    "transfer",
    transfer_labels,
    transfer_roc_auc,
)


print(f"annotation matrix shape: {perch_annotation_matrix.shape}")


print(f"perch roc auc: {perch_roc_auc}")
print(f"birdnet roc auc: {birdnet_roc_auc}")
print(f"transfer roc auc: {transfer_roc_auc}")
print(f"perch top1: {perch_top1}")
print(f"birdnet top1: {birdnet_top1}")
print(f"transfer top1: {transfer_top1}")
print(f"perch top3: {perch_top3}")
print(f"birdnet top3: {birdnet_top3}")
print(f"transfer top3: {transfer_top3}")
print(f"perch cmap: {perch_cmap}")
print(f"birdnet cmap: {birdnet_cmap}")
print(f"transfer cmap: {transfer_cmap}")
