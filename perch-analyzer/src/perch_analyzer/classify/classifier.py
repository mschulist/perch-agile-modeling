"""Training a custom linear classifier on the annotated windows.

This is the only part of the library that needs TensorFlow, so
`perch_hoplite.agile.classifier` is imported lazily inside `train_classifier`
rather than at module scope.
"""

from datetime import datetime as dt

import numpy as np
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB

from perch_analyzer.classify.linear_model import LinearClassifier
from perch_analyzer.config import config
from perch_analyzer.db import db

RNG = 123


def train_classifier(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    analyzer_db: db.AnalyzerDB,
    throwaway_classes: list[str],
    train_ratio: float,
    learning_rate: float,
    weak_neg_rate: float,
    num_train_steps: int,
) -> int:
    # Imported here because it pulls in TensorFlow, which no other command needs.
    from perch_hoplite.agile import classifier
    from perch_hoplite.agile.classifier_data import AgileDataManager

    throwaway = set(throwaway_classes)
    target_labels = tuple(x for x in hoplite_db.get_all_labels() if x not in throwaway)
    if not target_labels:
        raise ValueError(
            "No labels left to train on. Annotate some windows first, or drop "
            "some entries from --throwaway_classes."
        )

    data_manager = AgileDataManager(
        target_labels=target_labels,
        db=hoplite_db,
        batch_size=128,
        weak_negatives_batch_size=128,
        min_eval_examples=1,
        train_ratio=train_ratio,
        rng=np.random.default_rng(RNG),
    )

    linear_classifier, metrics = classifier.train_linear_classifier(
        data_manager=data_manager,
        learning_rate=learning_rate,
        weak_neg_weight=weak_neg_rate,
        num_train_steps=num_train_steps,
    )

    return analyzer_db.insert_classifier(
        datetime=dt.now(),
        embedding_model=config.embedding_model,
        labels=list(target_labels),
        train_ratio=train_ratio,
        learning_rate=learning_rate,
        weak_neg_rate=weak_neg_rate,
        num_train_steps=num_train_steps,
        rng=RNG,
        metrics=metrics,
        linear_classifier=LinearClassifier.from_hoplite(linear_classifier),
    )
