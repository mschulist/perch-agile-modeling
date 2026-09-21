"""Run a trained classifier over every embedded window in the project."""

import logging
import math

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from ml_collections import config_dict
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from tqdm import tqdm

from perch_analyzer.classify.linear_model import batched_embedding_iterator
from perch_analyzer.db.db import AnalyzerDB

logger = logging.getLogger(__name__)

BATCH_SIZE = 32678

ARROW_SCHEMA = pa.schema(
    [
        pa.field("filename", pa.string()),
        pa.field("logit", pa.float32()),
        pa.field("timestamp_s", pa.float32()),
        pa.field("window_id", pa.int64()),
        pa.field("label", pa.string()),
    ]
)


def classify(
    classifier_id: int,
    hoplite_db: SQLiteUSearchDB,
    analyzer_db: AnalyzerDB,
) -> int:
    classifier = analyzer_db.get_classifier(classifier_id)
    classifier_output_id = analyzer_db.insert_classifier_output(classifier_id)
    classifier_output = analyzer_db.get_classifier_output(classifier_output_id)

    logger.info(
        "classifying with classifier_id=%d into classifier_output_id=%d",
        classifier_id,
        classifier_output_id,
    )

    linear_model = classifier.linear_classifier
    labels = list(linear_model.classes)
    num_classes = len(labels)

    window_ids = np.array(hoplite_db.match_window_ids())

    # Recordings are few relative to windows, so resolve every filename once
    # up front rather than re-querying inside the batch loop.
    recording_filenames = {
        recording.id: recording.filename
        for recording in hoplite_db.get_all_recordings()
    }

    num_batches = math.ceil(len(window_ids) / BATCH_SIZE)
    emb_iter = batched_embedding_iterator(hoplite_db, window_ids, batch_size=BATCH_SIZE)

    with pq.ParquetWriter(
        classifier_output.parquet_path, ARROW_SCHEMA, compression="zstd"
    ) as writer:
        for batch_window_ids, batch_embs in tqdm(
            emb_iter, total=num_batches, desc="Classifying and writing"
        ):
            logits = np.asarray(linear_model(batch_embs))
            if logits.shape[1] != num_classes:
                raise ValueError(
                    "Number of classes in the classifier does not match the "
                    "number of labels"
                )

            batch_ids = [int(i) for i in batch_window_ids]
            windows = hoplite_db.get_all_windows(
                filter=config_dict.create(isin=dict(id=batch_ids))
            )
            # Index by window id: the query is free to return rows in any order,
            # but the logit rows follow `batch_window_ids`.
            window_by_id = {window.id: window for window in windows}

            filenames = []
            offsets = []
            for window_id in batch_window_ids:
                window = window_by_id[int(window_id)]
                filenames.append(recording_filenames[window.recording_id])
                offsets.append(float(window.offsets[0]))

            writer.write_table(
                pa.table(
                    {
                        "filename": pa.array(
                            np.repeat(filenames, num_classes), type=pa.string()
                        ),
                        "logit": pa.array(
                            logits.reshape(-1).astype(np.float32), type=pa.float32()
                        ),
                        "timestamp_s": pa.array(
                            np.repeat(offsets, num_classes).astype(np.float32),
                            type=pa.float32(),
                        ),
                        "window_id": pa.array(
                            np.repeat(batch_window_ids, num_classes), type=pa.int64()
                        ),
                        "label": pa.array(
                            np.tile(labels, logits.shape[0]), type=pa.string()
                        ),
                    },
                    schema=ARROW_SCHEMA,
                )
            )

    return classifier_output_id
