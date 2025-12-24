from typing import Iterator, List, Optional, Tuple
import numpy as np
from python_server.lib.auth import get_temp_gs_url
from python_server.lib.db.db import AccountsDB
from python_server.lib.models import (
    ClassifierResult,
    ClassifierResultResponse,
    ClassifierRun,
)
from python_server.lib.perch_utils.search import (
    get_possible_example_audio_path,
    get_possible_example_image_path,
)
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt
from datetime import datetime

import pyarrow as pa
import pyarrow.parquet as pq
import polars as pl
from tqdm import tqdm
from etils import epath

from perch_hoplite.agile import classifier_data, classifier
from ml_collections import config_dict

THROWAWAY_CLASSES = set("review")


def get_eval_metrics_path(params_path: str | epath.Path, run_id: int):
    """
    Given run id, get the eval metrics path
    """
    if str(params_path).startswith("gs://"):
        return get_temp_gs_url(f"{str(params_path)}/{run_id}_eval_scores.npz")
    return epath.Path(params_path) / str(run_id) / f"{run_id}_eval_scores.npz"


def get_classifier_params_path(params_path: str | epath.Path, run_id: int):
    """
    Given run id, get the classifier params path
    """
    if str(params_path).startswith("gs://"):
        return get_temp_gs_url(f"{str(params_path)}/{run_id}_params.json")
    return epath.Path(params_path) / str(run_id) / f"{run_id}_params.json"


def get_classifier_predictions_path(classify_path: str | epath.Path, run_id: int):
    return epath.Path(classify_path) / str(run_id) / "predictions.parquet"


def batched_embedding_iterator(
    db: SQLiteUsearchDBExt,
    window_ids: np.ndarray,
    batch_size: int = 1024,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Iterate over embeddings in batches."""
    for q in range(0, len(window_ids), batch_size):
        batch_ids = window_ids[q : q + batch_size]
        batch_embs = db.get_embeddings_batch(batch_ids)
        yield batch_ids, batch_embs


class ClassifyFromLabels:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        project_id: int,
        classify_path: str,
        linear_classifier: classifier.LinearClassifier | None = None,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.classify_path = epath.Path(classify_path)

        self.datetime = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.labels = tuple(
            [x for x in self.hoplite_db.get_all_labels() if x not in THROWAWAY_CLASSES]
        )

        self.data_manager = self.get_data_manager()

        self.linear_model = linear_classifier
        if self.linear_model is None:
            self.linear_model, self.eval_scores = self.train_classifier(
                self.data_manager
            )

    def get_data_manager(self):
        """
        Returns the DataManager for the labels
        """

        return classifier_data.AgileDataManager(
            target_labels=self.labels,
            db=self.hoplite_db,
            train_ratio=0.5,
            min_eval_examples=1,
            batch_size=128,
            weak_negatives_batch_size=128,
            rng=np.random.default_rng(),
            max_train_examples_per_label=15,
        )

    def train_classifier(self, data_manager: classifier_data.AgileDataManager):
        """
        Trains a linear classifier using the data manager

        Adds the classifier to the database along with the evaluation scores
        """

        linear_classifier, eval_scores = classifier.train_linear_classifier(
            data_manager=data_manager,
            learning_rate=1e-3,
            weak_neg_weight=0.00,
            num_train_steps=128,
        )

        classifier_run = ClassifierRun(
            project_id=self.project_id,
            datetime=self.datetime,
        )

        self.db.add_classifier(classifier_run)

        classifier_run_id = self.db.get_classifier_run_id_by_datetime(
            self.datetime, self.project_id
        )

        if classifier_run_id is None:
            raise ValueError("classifier run id is None")

        linear_classifier.save(
            str(get_classifier_params_path(self.classify_path, classifier_run_id))
        )
        np.savez(
            str(get_classifier_params_path(self.classify_path, classifier_run_id)),
            **eval_scores,
            allow_pickle=True,
        )

        return linear_classifier, eval_scores

    def threaded_classify(
        self,
        batch_size: int = 4096,
    ):
        """
        Performs classification of the embeddings in the database.

        Args:
            iceberg_table: The iceberg table to write results to
            batch_size: Number of embeddings to process per batch
            table_size: Size of accumulated table before writing to iceberg
        """
        self.hoplite_db.commit()

        # Get all window ids to classify
        window_ids = np.array(self.hoplite_db.match_window_ids())

        schema = pa.schema(
            [
                pa.field("filename", pa.string()),
                pa.field("logit", pa.float32()),
                pa.field("timestamp_s", pa.float32()),
                pa.field("window_id", pa.int64()),
                pa.field("label", pa.string()),
            ]
        )

        classifier_run_id = self.db.get_classifier_run_id_by_datetime(
            self.datetime, self.project_id
        )

        if classifier_run_id is None:
            raise ValueError("classifier run id is None")

        writer = pq.ParquetWriter(
            get_classifier_predictions_path(self.classify_path, classifier_run_id),
            schema,
            compression="zstd",
        )

        # Process embeddings in batches
        for batch_ids, batch_embs in tqdm(
            batched_embedding_iterator(self.hoplite_db, window_ids, batch_size),
            total=len(window_ids) // batch_size + 1,
            desc="Classifying and writing",
        ):
            # Do inference
            logits = np.asarray(self.linear_model(batch_embs))  # type: ignore

            # Get source information for each embedding
            filenames: List[str] = []
            offsets: List[float] = []

            for window_id in batch_ids:
                window = self.hoplite_db.get_window(int(window_id))
                filenames.append(
                    self.hoplite_db.get_recording(window.recording_id).filename
                )
                offsets.append(float(window.offsets[0]))

            num_embeddings = logits.shape[0]
            num_classes = logits.shape[1]

            if num_classes != len(self.labels):
                raise ValueError(
                    "Number of classes in the classifier does not match the number of labels"
                )

            filenames_repeated = np.repeat(filenames, num_classes)
            window_ids_repeated = np.repeat(batch_ids, num_classes)
            offsets_repeated = np.repeat(offsets, num_classes).astype(np.float32)
            logits_flat = logits.flatten().astype(np.float32)
            labels_repeated = np.tile(self.labels, num_embeddings)

            batch_table = pl.DataFrame(
                {
                    "filename": filenames_repeated,
                    "logit": logits_flat,
                    "timestamp_s": offsets_repeated,
                    "window_id": window_ids_repeated,
                    "label": labels_repeated,
                },
                schema=schema,
            )

            writer.write_table(batch_table.to_arrow())


class SearchClassifications:
    """
    Class to search the classification results

    The goal is to get a subset of the classification results to examine
    and label
    """

    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        classify_datetime: str,
        project_id: int,
        classify_path: str,
    ):
        """
        classify_datetime: datetime when the classification was run
        """
        self.db = db
        self.project_id = project_id
        self.classify_datetime = classify_datetime
        self.classify_path = epath.Path(classify_path)
        self.hoplite_db = hoplite_db

        self.base_path = hoplite_db.get_metadata("audio_sources").audio_globs[0][  # type: ignore
            "base_path"
        ]

        classifier_run_id = self.db.get_classifier_run_id_by_datetime(
            self.classify_datetime, self.project_id
        )
        if classifier_run_id is None:
            raise ValueError("Could not find classifier run id")
        self.classifier_run_id = classifier_run_id

        self.linear_model = classifier.LinearClassifier.load(
            str(get_classifier_params_path(self.classify_path, self.classifier_run_id))
        )
        self.all_labels = self.linear_model.classes

        self.lazy_table = pl.scan_parquet(
            str(
                get_classifier_predictions_path(
                    self.classify_path, self.classifier_run_id
                )
            )
        )

    def precompute_classify_results(
        self,
        logit_ranges: Tuple[Tuple[float, float], ...],
        num_per_label: int,
        max_logits: bool = False,
        labels: Optional[List[str]] = None,
    ):
        """
        Precompute a subset of the classification results to examine

        Args:
            num_per_label: number of samples per label to examine
            max_logits: whether to take the maximum logits from each range
            labels: list of labels to examine. If None, all labels are examined
        """
        num_per_logit_range = num_per_label // len(logit_ranges)
        if num_per_logit_range == 0:
            raise ValueError(
                "num_per_label must be greater than the number of logit ranges"
            )
        if labels is None:
            labels = list(self.all_labels)

        # if we are getting the max logits from the range, scanning cannot do that
        # so we need to get all of the records and then select the max "manually"
        # TODO: make this faster...
        limit = num_per_logit_range
        for label in labels:
            existing_embed_ids_for_label = (
                self.db.get_precompute_classify_embed_ids_by_label(
                    label,
                    self.project_id,
                )
            )
            for logit_range in logit_ranges:
                start, end = logit_range
                table = (
                    self.lazy_table.filter(
                        (pl.col("logit") > start)
                        & (pl.col("logit") < end)
                        & (pl.col("label") == label)
                        & ~(pl.col("window_id").is_in(existing_embed_ids_for_label))
                    )
                    .head(limit)
                    .collect()
                )

                for row in table.iter_rows(named=True):
                    window_id = row["window_id"]
                    logit = row["logit"]
                    label = row["label"]
                    self.add_precompute_classify_result(
                        window_id=window_id,
                        logit=logit,
                        label=label,
                    )

    def add_precompute_classify_result(self, window_id: int, logit: float, label: str):
        """
        Add a precomputed classification result to the database and
        save the audio and image results to the precompute search directory
        """
        window = self.hoplite_db.get_window(window_id)
        recording = self.hoplite_db.get_recording(window.recording_id)

        classifier_result = ClassifierResult(
            filename=recording.filename,
            timestamp_s=window.offsets[0],
            logit=logit,
            embedding_id=window_id,
            label=label,
            project_id=self.project_id,
            classifier_run_id=self.classifier_run_id,
            possible_example_id=-1,  # no longer used
        )
        self.db.add_classifier_result(classifier_result)


class ExamineClassifications:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        project_id: int,
        precompute_search_dir: str,
        classifier_run_id: int,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.classifier_run_id = classifier_run_id

    def get_classifier_results(self):
        """
        Get all of the precomputed results from a single classifier
        """
        results = self.db.get_classifier_results(
            self.classifier_run_id, self.project_id
        )
        classifier_results: List[ClassifierResultResponse] = []
        for result in results:
            if result.project_id is None:
                raise ValueError(f"classifier result project id is None: {result}")
            annotated_labels = [
                label.label
                for label in self.hoplite_db.get_all_annotations(
                    config_dict.create(eq=dict(window_id=result.embedding_id))
                )
            ]
            classifier_results.append(
                ClassifierResultResponse(
                    annotated_labels=annotated_labels,
                    id=result.id if result.id else -1,
                    embedding_id=result.embedding_id,
                    label=result.label,
                    logit=result.logit,
                    timestamp_s=result.timestamp_s,
                    filename=result.filename,
                    project_id=result.project_id,
                    classifier_run_id=result.classifier_run_id,
                    image_path=str(
                        get_possible_example_image_path(
                            result.embedding_id,
                            self.precompute_search_dir,
                            temp_url=True,
                        )
                    ),
                    audio_path=str(
                        get_possible_example_audio_path(
                            result.embedding_id,
                            self.precompute_search_dir,
                            temp_url=True,
                        )
                    ),
                )
            )
        return classifier_results
