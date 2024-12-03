import concurrent.futures
import tempfile
import threading
from typing import Any, List, Optional, Tuple
import concurrent
import numpy as np
import pyiceberg.table
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.expressions import (
    LessThanOrEqual,
    And,
    GreaterThanOrEqual,
    EqualTo,
    NotIn,
)
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
from scipy.io import wavfile
import matplotlib.pyplot as plt
import librosa.display as librosa_display

import pyarrow as pa
from tqdm import tqdm
from etils import epath

from chirp.projects.agile2 import classifier_data, classifier, embedding_display
from chirp.projects.hoplite import interface
from chirp import audio_utils


def get_eval_metrics_path(params_path: str | epath.Path, run_id: int):
    """
    Given run id, get the eval metrics path
    """
    if str(params_path).startswith("gs://"):
        return get_temp_gs_url(f"{str(params_path)}/{run_id}.json")
    return epath.Path(params_path) / f"{run_id}_eval_scores.npz"


def worker_initializer(state: dict[str, Any]):
    name = threading.current_thread().name
    state[f"{name}db"] = state["db"].thread_split()


class ClassifyFromLabels:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        project_id: int,
        warehouse_path: str,
        classifier_params_path: str,
        params: np.ndarray | None = None,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.warehouse_path = warehouse_path
        self.classifier_params_path = epath.Path(classifier_params_path)

        self.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # TODO: maybe make this a parameter...
        self.labels = tuple([x for x in self.hoplite_db.get_classes() if x != "review"])

        self.data_manager = self.get_data_manager()

        if params is None:
            self.params, self.eval_scores = self.train_classifier(self.data_manager)

    def get_data_manager(self):
        """
        Returns the DataManager for the labels
        """

        return classifier_data.AgileDataManager(
            target_labels=self.labels,
            db=self.hoplite_db,
            train_ratio=0.9,
            min_eval_examples=1,
            batch_size=128,
            weak_negatives_batch_size=128,
            rng=np.random.default_rng(),
        )

    def train_classifier(self, data_manager: classifier_data.AgileDataManager):
        """
        Trains a linear classifier using the data manager

        Adds the classifier to the database along with the evaluation scores
        """

        params, eval_scores = classifier.train_linear_classifier(
            data_manager=data_manager,
            learning_rate=1e-3,
            weak_neg_weight=0.05,
            l2_mu=0.0,
            num_train_steps=128,
            loss_name="bce",
        )

        classifier_run = ClassifierRun(
            project_id=self.project_id,
            datetime=self.datetime,
        )

        self.db.add_classifier(classifier_run)

        classifier_run_id = self.db.get_classifier_run_id_by_datetime(
            self.datetime, self.project_id
        )

        np.savez(
            self.classifier_params_path / f"{classifier_run_id}_params.npz", **params
        )
        np.savez(
            self.classifier_params_path / f"{classifier_run_id}_eval_scores.npz",
            **eval_scores,
        )

        return params, eval_scores

    def classify_worker_function(self, embed_ids: np.ndarray, state: dict[str, Any]):
        """
        Given a list of embed_ids, classify the embeddings

        State contains relevant information to classify, such as a db connection, parameters, etc.
        """
        name = threading.current_thread().name
        emb_ids, embeddings = state[f"{name}db"].get_embeddings(embed_ids)
        logits = np.asarray(classifier.infer(state["params"], embeddings))

        sources: List[str] = []
        for emb_id in emb_ids:
            source = state[f"{name}db"].get_embedding_source(emb_id)
            sources.append(source.source_id)

        num_embeddings = logits.shape[0]
        num_classes = logits.shape[1]

        if num_classes != len(self.labels):
            raise ValueError(
                "Number of classes in the classifier does not match the number of labels"
            )

        # make these all have shape (num_embeddings * num_classes,)
        sources_repeated = np.repeat(sources, num_classes)
        emb_ids_repeated = np.repeat(emb_ids, num_classes)
        logits_flat = logits.flatten()

        labels_repeated = np.tile(self.labels, num_embeddings)

        table = pa.table(
            {
                "source": sources_repeated,
                "embedding_id": emb_ids_repeated,
                "label": labels_repeated,
                "logit": logits_flat,
            }
        )

        return table

    def threaded_classify(
        self,
        iceberg_table: pyiceberg.table.Table,
        batch_size: int = 4096,
        max_workers: int = 12,
        table_size: int = 100_000,
    ):
        """
        Performs a threaded classification of the embeddings in the database
        """
        state = {}
        state["db"] = self.hoplite_db
        state["params"] = self.params

        self.hoplite_db.commit()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max_workers,
            initializer=worker_initializer,
            initargs=(state,),
        ) as executor:
            ids = self.hoplite_db.get_embedding_ids()
            futures = []
            for q in range(0, ids.shape[0], batch_size):
                futures.append(
                    executor.submit(
                        self.classify_worker_function,
                        ids[q : q + batch_size],
                        state,
                    )
                )

            current_table = None

            for f in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc="Classifying",
            ):
                try:
                    table = f.result()
                    if current_table is None:
                        current_table = table
                    else:
                        current_table = pa.concat_tables([current_table, table])

                    if current_table.num_rows >= table_size:
                        iceberg_table.append(current_table)
                        current_table = None
                except Exception as e:
                    print(f"Exception in future: {e}")
                    continue

            if current_table is not None and current_table.num_rows > 0:
                iceberg_table.append(current_table)

    def create_iceberg_table(self):
        """
        Creates an iceberg table with the schema for the classification results
        """
        catalog = SqlCatalog(
            "default",
            **{
                "uri": f"sqlite:///{self.warehouse_path}/pyiceberg_catalog.db",
                "warehouse": f"file://{self.warehouse_path}",
            },
        )
        if not catalog._namespace_exists(str(self.project_id)):
            catalog.create_namespace(str(self.project_id))

        schema = pa.schema(
            [
                pa.field("source", pa.string()),
                pa.field("logit", pa.float32()),
                pa.field("embedding_id", pa.int64()),
                pa.field("label", pa.string()),
            ]
        )
        # the table name is the datetime when the classifier started to run
        table = catalog.create_table(f"{self.project_id}.{self.datetime}", schema)
        return table


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
        warehouse_path: str,
        precompute_classify_path: str,
        sample_rate: int = 32000,
    ):
        """
        classify_datetime: datetime when the classification was run
        """
        self.db = db
        self.project_id = project_id
        self.warehouse_path = warehouse_path
        self.precompute_classify_path = epath.Path(precompute_classify_path)
        self.classify_datetime = classify_datetime
        self.sample_rate = sample_rate
        self.hoplite_db = hoplite_db

        self.base_path = hoplite_db.get_metadata("audio_sources").audio_globs[0][  # type: ignore
            "base_path"
        ]

        self.iceberg_table = self.get_iceberg_table()
        classifier_run_id = self.db.get_classifier_run_id_by_datetime(
            self.classify_datetime, self.project_id
        )
        if classifier_run_id is None:
            raise ValueError("Could not find classifier run id")
        self.classifier_run_id = classifier_run_id

    def get_iceberg_table(self):
        """
        Get the iceberg table
        """
        catalog = SqlCatalog(
            "default",
            **{
                "uri": f"sqlite:///{self.warehouse_path}/pyiceberg_catalog.db",
                "warehouse": f"file://{self.warehouse_path}",
            },
        )
        table = catalog.load_table(f"{self.project_id}.{self.classify_datetime}")
        return table

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
            lbs = (
                self.iceberg_table.scan()
                .to_duckdb("default")
                .execute("SELECT DISTINCT label FROM default")
                .fetchall()
            )
            # lbs is a list of tuples, so we just want the first element
            labels = [lb[0] for lb in lbs]

        # if we are getting the max logits from the range, scanning cannot do that
        # so we need to get all of the records and then select the max "manually"
        limit = num_per_logit_range if not max_logits else None
        for label in labels:
            existing_embed_ids_for_label = (
                self.db.get_precompute_classify_embed_ids_by_label(
                    label,
                    self.project_id,
                )
            )
            for logit_range in logit_ranges:
                start, end = logit_range
                table = self.iceberg_table.scan(
                    row_filter=And(
                        GreaterThanOrEqual("logit", start),
                        LessThanOrEqual("logit", end),
                        EqualTo("label", label),
                        NotIn("embedding_id", existing_embed_ids_for_label),
                    ),
                    limit=limit,
                ).to_pandas()
                if max_logits:
                    table = (
                        table.sort_values(by="logit", ascending=False)
                        .reset_index()
                        .iloc[0 : min(num_per_logit_range, table.shape[0])]
                    )
                for _, row in table.iterrows():
                    embedding_id = row["embedding_id"]
                    logit = row["logit"]
                    label = row["label"]
                    self.add_precompute_classify_result(
                        embedding_id=embedding_id,
                        logit=logit,
                        label=label,
                    )

    def add_precompute_classify_result(
        self, embedding_id: int, logit: float, label: str
    ):
        """
        Add a precomputed classification result to the database and
        save the audio and image results to the precompute classify directory
        """
        embed_source = self.hoplite_db.get_embedding_source(embedding_id)
        classifier_result = ClassifierResult(
            filename=embed_source.source_id,
            timestamp_s=embed_source.offsets[0],
            logit=logit,
            embedding_id=embedding_id,
            label=label,
            project_id=self.project_id,
            classifier_run_id=self.classifier_run_id,
        )
        self.db.add_classifier_result(classifier_result)

        precompute_classify = self.db.get_classifier_result_by_embed_id_and_label(
            embedding_id, label
        )
        if precompute_classify is None:
            raise ValueError("Could not find precompute classify id")
        if precompute_classify.id is None:
            raise ValueError("Could not find precompute classify id")

        print(embedding_id, label, precompute_classify.id)
        self.flush_classify_result_to_disk(embed_source, precompute_classify.id)

    def flush_classify_result_to_disk(
        self, embedding_source: interface.EmbeddingSource, precompute_classify_id: int
    ):
        """
        Save the audio and image results to the precompute classify directory.

        Args:
            embedding_source: The embedding source to save the audio and image for.
            precompute_example_id: Id of the precompute classify example.
        """
        # First, load the audio and save it to the precompute classify directory
        # we can reuse the same function even though it probably is not named correctly
        audio_output_filepath = get_possible_example_audio_path(
            precompute_classify_id, self.precompute_classify_path
        )

        audio_slice = audio_utils.load_audio_window_soundfile(
            f"{self.base_path}/{embedding_source.source_id}",
            offset_s=embedding_source.offsets[0],
            window_size_s=5.0,  # TODO: make this a parameter, not hard coded (although probably fine)
            sample_rate=self.sample_rate,
        )

        with tempfile.NamedTemporaryFile() as tmp_file:
            wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio_slice))
            epath.Path(tmp_file.name).copy(audio_output_filepath)

        # Second, get the spectrogram and save it to the precompute classify directory
        image_output_filepath = get_possible_example_image_path(
            precompute_classify_id, self.precompute_classify_path
        )

        melspec_layer = embedding_display.get_melspec_layer(self.sample_rate)
        if audio_slice.shape[0] < self.sample_rate / 100 + 1:
            # Center pad if audio is too short.
            zs = np.zeros([self.sample_rate // 10], dtype=audio_slice.dtype)
            audio_slice = np.concatenate([zs, audio_slice, zs], axis=0)
        melspec = melspec_layer(audio_slice).T  # type: ignore

        librosa_display.specshow(
            melspec,
            sr=self.sample_rate,
            y_axis="mel",
            x_axis="time",
            hop_length=self.sample_rate // 100,
            cmap="Greys",
        )
        plt.savefig(image_output_filepath)
        plt.close()


class ExamineClassifications:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        project_id: int,
        precompute_classify_path: str,
        classifier_run_id: int,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.precompute_classify_path = epath.Path(precompute_classify_path)
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
            if result.id is None:
                raise ValueError("Result id is None")
            if result.project_id is None:
                raise ValueError("Result project id is None")

            annotated_labels = [
                label.label for label in self.hoplite_db.get_labels(result.embedding_id)
            ]
            classifier_results.append(
                ClassifierResultResponse(
                    annotated_labels=annotated_labels,
                    id=result.id,
                    embedding_id=result.embedding_id,
                    label=result.label,
                    logit=result.logit,
                    timestamp_s=result.timestamp_s,
                    filename=result.filename,
                    project_id=result.project_id,
                    classifier_run_id=result.classifier_run_id,
                    image_path=str(
                        get_possible_example_image_path(
                            result.id, self.precompute_classify_path
                        )
                    ),
                    audio_path=str(
                        get_possible_example_audio_path(
                            result.id, self.precompute_classify_path
                        )
                    ),
                )
            )
        return classifier_results
