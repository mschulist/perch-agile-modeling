import numpy as np
import perch_hoplite.agile.classifier as classifier
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_hoplite.agile.classifier_data import AgileDataManager
from perch_analyzer.config import config
from perch_analyzer.db import db
from datetime import datetime as dt

RNG = 123


def train_classifier(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    analyzer_db: db.AnalyzerDB,
    throwaway_classes: list[str],
    train_ratio: float,
    max_train_examples_per_label: int,
    learning_rate: float,
    weak_neg_rate: float,
    num_train_steps: int,
) -> int:
    target_labels = tuple(
        x for x in hoplite_db.get_all_labels() if x not in throwaway_classes
    )
    data_manager = AgileDataManager(
        target_labels=target_labels,
        db=hoplite_db,
        batch_size=128,
        weak_negatives_batch_size=128,
        min_eval_examples=1,
        train_ratio=train_ratio,
        rng=np.random.default_rng(RNG),
        max_train_examples_per_label=max_train_examples_per_label,
    )

    linear_classifier, metrics = classifier.train_linear_classifier(
        data_manager=data_manager,
        learning_rate=learning_rate,
        weak_neg_weight=weak_neg_rate,
        num_train_steps=num_train_steps,
    )

    # TODO: get the correct embedding model
    return analyzer_db.insert_classifier(
        datetime=dt.now(),
        embedding_model=config.embedding_model,
        labels=target_labels,
        train_ratio=train_ratio,
        max_train_examples_per_label=max_train_examples_per_label,
        learning_rate=learning_rate,
        weak_neg_rate=weak_neg_rate,
        num_train_steps=num_train_steps,
        rng=RNG,
        metrics=metrics,
        linear_classifier=linear_classifier,
    )
