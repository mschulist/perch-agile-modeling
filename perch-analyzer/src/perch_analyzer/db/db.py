from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import perch_analyzer.db.tables as tables
from pydantic import BaseModel
from datetime import datetime as dt
from typing import Any
from perch_hoplite.agile import classifier
from perch_analyzer.config import config
import numpy as np


def linear_classifier_path(classifiers_dir: str, classifier_id: int):
    return f"{classifiers_dir}/{classifier_id}_classifier.json"


def metrics_path(classifiers_dir: str, classifier_id: int):
    return f"{classifiers_dir}/{classifier_id}_metrics.npz"


def classifier_output_path(classifier_outputs_dir: str, classifier_output_id: int):
    return f"{classifier_outputs_dir}/{classifier_output_id}.parquet"


class Classifier(BaseModel):
    id: int
    datetime: dt
    embedding_model: str
    metrics: dict[str, Any]  # TODO: make this an object, not a dict
    linear_classifier: classifier.LinearClassifier


class ClassifierOutput(BaseModel):
    id: int
    classifier_id: int
    parquet_path: str


class AnalyzerDB:
    def __init__(self, config: config.Config):
        self.config = config
        self.engine = create_engine(config.db_path)
        tables.Base.metadata.create_all(self.engine)

    def get_classifier(self, classifier_id: int) -> Classifier:
        with Session(self.engine) as session:
            stmt = select(tables.Classifier).where(
                tables.Classifier.id == classifier_id
            )
            db_classifier = session.execute(stmt).scalar_one()

            # now we load the metrics and linear_classifier based on the id
            linear_classifier = classifier.LinearClassifier.load(
                linear_classifier_path(self.config.classifiers_dir, classifier_id)
            )

            metrics = np.load(metrics_path(self.config.classifiers_dir, classifier_id))

            return Classifier(
                id=classifier_id,
                datetime=dt.fromisoformat(db_classifier.datetime),
                embedding_model=db_classifier.embedding_model,
                linear_classifier=linear_classifier,
                metrics=metrics,
            )

    def insert_classifier(self, classifier: Classifier) -> int:
        with Session(self.engine) as session:
            db_classifier = tables.Classifier(
                datetime=classifier.datetime.isoformat(),
                embedding_model=classifier.embedding_model,
            )

            session.add(db_classifier)

        session.flush()
        classifier_id = db_classifier.id

        # Save the classifier and metrics files
        classifier.linear_classifier.save(
            linear_classifier_path(self.config.classifiers_dir, classifier_id)
        )
        np.savez(
            metrics_path(self.config.classifiers_dir, classifier_id),
            **classifier.metrics,
        )

        session.commit()
        return classifier_id

    def get_classifier_output(self, classifier_output_id: int) -> ClassifierOutput:
        with Session(self.engine) as session:
            stmt = select(tables.ClassifierOutput).where(
                tables.ClassifierOutput.id == classifier_output_id
            )

            db_classifier_output = session.execute(stmt).scalar_one()

            return ClassifierOutput(
                id=classifier_output_id,
                classifier_id=db_classifier_output.classifier_id,
                parquet_path=classifier_output_path(
                    self.config.classifier_outputs_dir, classifier_output_id
                ),
            )

    def insert_classifier_output(self, classifier_output: ClassifierOutput) -> int:
        with Session(self.engine) as session:
            db_classifier_output = tables.ClassifierOutput(
                classifier_id=classifier_output.classifier_id
            )

            session.add(db_classifier_output)

        session.flush()

        return db_classifier_output.id
