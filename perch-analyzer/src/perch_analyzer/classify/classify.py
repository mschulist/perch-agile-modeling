from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_hoplite.agile.classifier import batched_embedding_iterator
from perch_analyzer.db.db import AnalyzerDB

from tqdm import tqdm
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

BATCH_SIZE = 32678


def classify(
    classifier_id: int,
    hoplite_db: SQLiteUSearchDB,
    analyzer_db: AnalyzerDB,
):
    classifier = analyzer_db.get_classifier(classifier_id)
    classifier_output_id = analyzer_db.insert_classifier_output(classifier_id)
    classifier_output = analyzer_db.get_classifier_output(classifier_output_id)

    linear_model = classifier.linear_classifier
    parquet_filepath = classifier_output.parquet_path

    window_ids = np.array(hoplite_db.match_window_ids())

    arrow_schema = pa.schema(
        [
            pa.field("filename", pa.string()),
            pa.field("logit", pa.float32()),
            pa.field("timestamp_s", pa.float32()),
            pa.field("window_id", pa.int64()),
            pa.field("label", pa.string()),
        ]
    )

    labels = linear_model.classes
    label_ids = {cl: i for i, cl in enumerate(linear_model.classes)}
    target_label_ids = np.array([label_ids[lab] for lab in labels])

    writer = pq.ParquetWriter(parquet_filepath, arrow_schema, compression="zstd")

    def logits_fn(batch_embs: np.ndarray):
        return linear_model(batch_embs)[:, target_label_ids]

    emb_iter = batched_embedding_iterator(hoplite_db, window_ids, batch_size=BATCH_SIZE)

    for batch_idxes, batch_embs in tqdm(
        emb_iter,
        total=len(window_ids) // BATCH_SIZE,
        desc="Classifying and writing",
    ):
        logits = np.asarray(logits_fn(batch_embs))

        filenames: list[str] = []
        offsets: list[float] = []

        for window_id in batch_idxes:
            window = hoplite_db.get_window(int(window_id))
            filenames.append(hoplite_db.get_recording(window.recording_id).filename)
            offsets.append(float(window.offsets[0]))

        num_embeddings = logits.shape[0]
        num_classes = logits.shape[1]

        if num_classes != len(labels):
            raise ValueError(
                "Number of classes in the classifier does not match the number of labels"
            )

        filenames_repeated = np.repeat(filenames, num_classes)
        window_ids_repeated = np.repeat(batch_idxes, num_classes)
        offsets_repeated = np.repeat(offsets, num_classes).astype(np.float32)
        logits_flat = logits.flatten().astype(np.float32)
        labels_repeated = np.tile(labels, num_embeddings)

        arrow_table = pa.table(
            {
                "filename": pa.array(filenames_repeated, type=pa.string()),
                "logit": pa.array(logits_flat, type=pa.float32()),
                "timestamp_s": pa.array(offsets_repeated, type=pa.float32()),
                "window_id": pa.array(window_ids_repeated, type=pa.int64()),
                "label": pa.array(labels_repeated, type=pa.string()),
            },
            schema=arrow_schema,
        )
        writer.write_table(arrow_table)
