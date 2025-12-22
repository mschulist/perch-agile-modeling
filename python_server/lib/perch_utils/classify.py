import tempfile
from typing import Iterator, List, Optional, Tuple
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
    PossibleExample,
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

from perch_hoplite.agile import classifier_data, classifier, embedding_display
from perch_hoplite.db import interface
from perch_hoplite import audio_io as audio_utils
from ml_collections import config_dict

THROWAWAY_CLASSES = set("review")


def get_eval_metrics_path(params_path: str | epath.Path, run_id: int):
    """
    Given run id, get the eval metrics path
    """
    if str(params_path).startswith("gs://"):
        return get_temp_gs_url(f"{str(params_path)}/{run_id}_eval_scores.npz")
    return epath.Path(params_path) / f"{run_id}_eval_scores.npz"


def get_classifier_params_path(params_path: str | epath.Path, run_id: int):
    """
    Given run id, get the classifier params path
    """
    if str(params_path).startswith("gs://"):
        return get_temp_gs_url(f"{str(params_path)}/{run_id}_params.json")
    return epath.Path(params_path) / f"{run_id}_params.json"


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
        warehouse_path: str,
        classifier_params_path: str,
        linear_classifier: classifier.LinearClassifier | None = None,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.warehouse_path = warehouse_path
        self.classifier_params_path = epath.Path(classifier_params_path)

        self.datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

        linear_classifier, eval_scores = classifier.train_linear_classifier(
            data_manager=data_manager,
            learning_rate=1e-3,
            weak_neg_weight=0.05,
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

        linear_classifier.save(
            str(self.classifier_params_path / f"{classifier_run_id}_params.json")
        )
        np.savez(
            self.classifier_params_path / f"{classifier_run_id}_eval_scores.npz",
            *eval_scores,
        )

        return linear_classifier, eval_scores

    def threaded_classify(
        self,
        iceberg_table: pyiceberg.table.Table,
        batch_size: int = 4096,
        table_size: int = 100_000,
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

        current_table = None

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

            # Create flattened arrays for PyArrow table (matching Iceberg schema)
            filenames_repeated = np.repeat(filenames, num_classes)
            window_ids_repeated = np.repeat(batch_ids, num_classes)
            offsets_repeated = np.repeat(offsets, num_classes).astype(np.float32)
            logits_flat = logits.flatten().astype(np.float32)
            labels_repeated = np.tile(self.labels, num_embeddings)

            batch_table = pa.table(
                {
                    "filename": filenames_repeated,
                    "logit": logits_flat,
                    "timestamp_s": offsets_repeated,
                    "window_id": window_ids_repeated,
                    "label": labels_repeated,
                }
            )

            # Accumulate tables
            if current_table is None:
                current_table = batch_table
            else:
                current_table = pa.concat_tables([current_table, batch_table])

            # When we have enough rows, write to Iceberg
            if current_table.num_rows >= table_size:
                try:
                    iceberg_table.append(current_table)
                    print(f"Wrote {current_table.num_rows} rows to Iceberg")
                    current_table = None
                except Exception as e:
                    print(f"Exception writing to iceberg: {e}")
                    raise

        # Write any remaining data
        if current_table is not None and current_table.num_rows > 0:
            try:
                iceberg_table.append(current_table)
                print(f"Wrote final {current_table.num_rows} rows to Iceberg")
            except Exception as e:
                print(f"Exception writing final batch to iceberg: {e}")
                raise

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
                pa.field("filename", pa.string()),
                pa.field("logit", pa.float32()),
                pa.field("timestamp_s", pa.float32()),
                pa.field("window_id", pa.int64()),
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
        precompute_search_dir: str,
        classifier_params_path: str,
        sample_rate: int = 32000,
    ):
        """
        classify_datetime: datetime when the classification was run
        """
        self.db = db
        self.project_id = project_id
        self.warehouse_path = warehouse_path
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.classify_datetime = classify_datetime
        self.sample_rate = sample_rate
        self.hoplite_db = hoplite_db
        self.classifier_params_path = epath.Path(classifier_params_path)

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

        self.linear_model = classifier.LinearClassifier.load(
            str(self.classifier_params_path / f"{self.classifier_run_id}_params.json")
        )
        self.all_labels = self.linear_model.classes

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
            labels = list(self.all_labels)

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
                        NotIn("window_id", existing_embed_ids_for_label),
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

        possible_example = self.db.get_possible_example_by_embed_id(
            window_id, self.project_id
        )

        recording = self.hoplite_db.get_recording(window.recording_id)

        if possible_example is None or possible_example.id is None:
            # We need to add the classifier result to the possible_examples and finished_possible_examples
            # table so that IF we label the example, the precomputed spectrogram and audio are already there

            possible_example = PossibleExample(
                project_id=self.project_id,
                score=logit,
                embedding_id=window_id,
                timestamp_s=recording.offsets[0],
                filename=recording.filename,
            )
            self.db.add_possible_example(possible_example)

            # we need to get the example from the db to get the id
            possible_example = self.db.get_possible_example_by_embed_id(
                window_id, self.project_id
            )
            if possible_example is None:
                raise ValueError("Failed to get possible example from the database.")
            if possible_example.id is None:
                raise ValueError(
                    "Failed to get possible example from the database. Must have an ID."
                )
            self.db.finish_possible_example(possible_example)

            self.flush_classify_result_to_disk(window, possible_example.id)

        # Now that the example is entered as a possible example, we can enter it as a classifier result

        classifier_result = ClassifierResult(
            filename=recording.filename,
            timestamp_s=window.offsets[0],
            logit=logit,
            embedding_id=window_id,
            label=label,
            project_id=self.project_id,
            classifier_run_id=self.classifier_run_id,
            possible_example_id=possible_example.id,
        )
        self.db.add_classifier_result(classifier_result)

    def flush_classify_result_to_disk(
        self, window: interface.Window, possible_example_id: int
    ):
        """
        Save the audio and image results to the precompute classify directory.

        We use the possible example id so that we do not need to write the file twice.

        Args:
            embedding_source: The embedding source to save the audio and image for.
            possible_example_id: Id of the possible example in the database.
        """
        # First, load the audio and save it to the precompute classify directory
        # we can reuse the same function even though it probably is not named correctly
        audio_output_filepath = get_possible_example_audio_path(
            possible_example_id, self.precompute_search_dir
        )

        audio_slice = audio_utils.load_audio_window_soundfile(
            f"{self.base_path}/{self.hoplite_db.get_recording(window.recording_id).filename}",
            offset_s=window.offsets[0],
            window_size_s=5.0,  # TODO: make this a parameter, not hard coded (although probably fine)
            sample_rate=self.sample_rate,
        )

        with tempfile.NamedTemporaryFile() as tmp_file:
            wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio_slice))
            epath.Path(tmp_file.name).copy(audio_output_filepath)

        # Second, get the spectrogram and save it to the precompute classify directory
        image_output_filepath = get_possible_example_image_path(
            possible_example_id, self.precompute_search_dir
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
        plt.gca().invert_yaxis()
        with epath.Path(image_output_filepath).open("wb") as f:
            plt.savefig(f)
        plt.close()


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
            if result.possible_example_id is None:
                raise ValueError("Result possible example id is None")
            if result.project_id is None:
                raise ValueError("Result project id is None")

            annotated_labels = [
                label.label
                for label in self.hoplite_db.get_all_annotations(
                    config_dict.create(eq=dict(window_id=result.embedding_id))
                )
                # label.label for label in self.hoplite_db.get_labels(result.embedding_id)
            ]
            classifier_results.append(
                ClassifierResultResponse(
                    annotated_labels=annotated_labels,
                    id=result.possible_example_id,
                    embedding_id=result.embedding_id,
                    label=result.label,
                    logit=result.logit,
                    timestamp_s=result.timestamp_s,
                    filename=result.filename,
                    project_id=result.project_id,
                    classifier_run_id=result.classifier_run_id,
                    image_path=str(
                        get_possible_example_image_path(
                            result.possible_example_id,
                            self.precompute_search_dir,
                            temp_url=True,
                        )
                    ),
                    audio_path=str(
                        get_possible_example_audio_path(
                            result.possible_example_id,
                            self.precompute_search_dir,
                            temp_url=True,
                        )
                    ),
                )
            )
        return classifier_results
