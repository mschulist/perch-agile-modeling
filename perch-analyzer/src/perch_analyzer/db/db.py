from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import perch_analyzer.db.tables as tables
from pydantic import BaseModel, ConfigDict
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
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    datetime: dt
    embedding_model: str
    labels: tuple[str, ...]
    train_ratio: float
    rng: int | None
    max_train_examples_per_label: int
    learning_rate: float
    weak_neg_rate: float
    num_train_steps: float
    metrics: dict[str, Any]  # TODO: make this an object, not a dict
    linear_classifier: classifier.LinearClassifier


class ClassifierOutput(BaseModel):
    id: int
    classifier_id: int
    parquet_path: str


class TargetRecording(BaseModel):
    id: int
    xc_id: int | None
    filename: str | None
    label: str


class AnalyzerDB:
    def __init__(self, config: config.Config):
        self.config = config
        self.engine = create_engine(f"sqlite:///{config.data_path}/{config.db_path}")
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
                labels=tuple(db_classifier.labels),
                num_train_steps=db_classifier.num_train_steps,
                learning_rate=db_classifier.learning_rate,
                rng=db_classifier.rng,
                train_ratio=db_classifier.train_ratio,
                max_train_examples_per_label=db_classifier.max_train_examples_per_label,
                weak_neg_rate=db_classifier.weak_neg_rate,
            )

    def insert_classifier(
        self,
        datetime: dt,
        embedding_model: str,
        labels: tuple[str, ...],
        train_ratio: float,
        rng: int | None,
        max_train_examples_per_label: int,
        learning_rate: float,
        weak_neg_rate: float,
        num_train_steps: float,
        metrics: dict[str, Any],  # TODO: make this an object, not a dict
        linear_classifier: classifier.LinearClassifier,
    ) -> int:
        with Session(self.engine) as session:
            db_classifier = tables.Classifier(
                datetime=datetime.isoformat(),
                embedding_model=embedding_model,
                labels=labels,
                train_ratio=train_ratio,
                rng=rng,
                max_train_examples_per_label=max_train_examples_per_label,
                learning_rate=learning_rate,
                weak_neg_rate=weak_neg_rate,
                num_train_steps=num_train_steps,
            )

            session.add(db_classifier)

        session.flush()
        classifier_id = db_classifier.id

        # Save the classifier and metrics files
        linear_classifier.save(
            linear_classifier_path(self.config.classifiers_dir, classifier_id)
        )
        np.savez(
            metrics_path(self.config.classifiers_dir, classifier_id),
            **metrics,
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

    def insert_classifier_output(self, classifier_id: int) -> int:
        with Session(self.engine) as session:
            db_classifier_output = tables.ClassifierOutput(classifier_id=classifier_id)

            session.add(db_classifier_output)

        session.flush()

        return db_classifier_output.id

    def get_target_recording(self, target_recording_id: int) -> TargetRecording:
        with Session(self.engine) as session:
            stmt = select(tables.TargetRecording).where(
                tables.TargetRecording.id == target_recording_id
            )

            db_target_recording = session.execute(stmt).scalar_one()

            return TargetRecording(
                id=db_target_recording.id,
                xc_id=db_target_recording.xc_id,
                filename=db_target_recording.filename,
                label=db_target_recording.label,
            )

    def insert_target_recording(
        self, xc_id: int | None, filename: str | None, label: str
    ):
        with Session(self.engine) as session:
            db_target_recording = tables.TargetRecording(
                xc_id=xc_id,
                filename=filename,
                label=label,
            )

            session.add(db_target_recording)

        session.flush()

        return db_target_recording.id
