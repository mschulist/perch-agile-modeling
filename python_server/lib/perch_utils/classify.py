import concurrent.futures
import threading
from typing import Any, List
import concurrent
import numpy as np
import pyiceberg.table
from pyiceberg.catalog.sql import SqlCatalog
from python_server.lib.db.db import AccountsDB
from python_server.lib.models import ClassifierRun
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt
from datetime import datetime

import pyarrow as pa
from tqdm import tqdm
from etils import epath

from chirp.projects.agile2 import classifier_data, classifier


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

        self.data_manager = self.get_data_manager()

        if params is None:
            self.params, self.eval_scores = self.train_classifier(self.data_manager)

    def get_data_manager(self):
        """
        Returns the DataManager for the labels
        """

        return classifier_data.AgileDataManager(
            target_labels=None,
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
            num_train_steps=2,
            loss_name="bce",
        )

        classifier_run = ClassifierRun(
            project_id=self.project_id,
            datetime=self.datetime,
        )

        self.db.add_classifier(classifier_run)

        np.savez(self.classifier_params_path / f"{self.datetime}_params.npz", **params)
        np.savez(
            self.classifier_params_path / f"{self.datetime}_eval_scores.npz",
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
        logits = classifier.infer(state["params"], embeddings)

        # we need to get the source (filename) of the embeddings
        # this might be able to be done with a single sql query, but not sure
        sources: List[str] = []
        for emb_id in emb_ids:
            source = state[f"{name}db"].get_embedding_source(emb_id)
            sources.append(source)

        table = pa.table({"source": sources, "logit": logits, "embedding_id": emb_ids})
        return table

    def threaded_classify(
        self,
        iceberg_table: pyiceberg.table.Table,
        batch_size: int = 4096,
        max_workers: int = 12,
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

            for f in tqdm(
                concurrent.futures.as_completed(futures),
                total=len(futures),
                desc="Classifying",
            ):
                table = f.result()
                iceberg_table.append(table)

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
            ]
        )
        # the table name is the datetime when the classifier started to run
        table = catalog.create_table(f"{self.project_id}.{self.datetime}", schema)
        return table
