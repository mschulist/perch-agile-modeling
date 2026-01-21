import numpy as np
import perch_hoplite.agile.classifier as classifier
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_hoplite.agile.classifier_data import AgileDataManager
from perch_analyzer.config import config
from perch_analyzer.db import db
from datetime import datetime as dt

RNG = 123


def train_classifier(
    config: config.Config, hoplite_db: SQLiteUSearchDB, analyzer_db: db.AnalyzerDB
) -> int:
    target_labels = tuple(
        x for x in hoplite_db.get_all_labels() if x not in config.throwaway_classes
    )
    data_manager = AgileDataManager(
        target_labels=target_labels,
        db=hoplite_db,
        batch_size=128,
        weak_negatives_batch_size=128,
        min_eval_examples=1,
        train_ratio=config.train_ratio,
        rng=np.random.default_rng(RNG),
    )

    linear_classifier, metrics = classifier.train_linear_classifier(
        data_manager=data_manager,
        learning_rate=config.learning_rate,
        weak_neg_weight=config.weak_neg_rate,
        num_train_steps=config.num_train_steps,
    )

    # TODO: get the correct embedding model
    return analyzer_db.insert_classifier(
        datetime=dt.now(),
        embedding_model=str(hoplite_db.get_metadata("embedding_model")),
        labels=target_labels,
        train_ratio=config.train_ratio,
        max_train_examples_per_label=config.max_train_examples_per_label,
        learning_rate=config.learning_rate,
        weak_neg_rate=config.weak_neg_rate,
        num_train_steps=config.num_train_steps,
        rng=RNG,
        metrics=metrics,
        linear_classifier=linear_classifier,
    )
