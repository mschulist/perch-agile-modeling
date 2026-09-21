from collections.abc import Sequence
from datetime import datetime as dt
from typing import Any

import numpy as np
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import perch_analyzer.db.tables as tables
from perch_analyzer.classify.linear_model import LinearClassifier
from perch_analyzer.config import config

SAMPLE_RATE = 32000


def linear_classifier_path(classifiers_dir: str, classifier_id: int):
    return f"{classifiers_dir}/{classifier_id}_classifier.json"


def metrics_path(classifiers_dir: str, classifier_id: int):
    return f"{classifiers_dir}/{classifier_id}_metrics.npz"


def classifier_output_path(classifier_outputs_dir: str, classifier_output_id: int):
    return f"{classifier_outputs_dir}/{classifier_output_id}.parquet"


def get_target_recording_path(target_recordings_dir: str, target_recording_id: int):
    return f"{target_recordings_dir}/{target_recording_id}.wav"


def _load_metrics(path: str) -> dict[str, Any]:
    """Read a metrics npz into a plain dict, without leaving the file open."""
    with np.load(path) as npz:
        return {key: npz[key] for key in npz.files}


class ClassifierOutputWindow(BaseModel):
    id: int
    classifier_output_id: int
    window_id: int
    label: str
    logit: float


class ClassifierInfo(BaseModel):
    """A classifier's metadata and metrics, without its (large) weights.

    This is what list views need.  Use `AnalyzerDB.get_classifier` when you
    actually intend to run the classifier.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    datetime: dt
    embedding_model: str
    labels: list[str]
    train_ratio: float
    rng: int | None
    learning_rate: float
    weak_neg_rate: float
    num_train_steps: float
    metrics: dict[str, Any]  # TODO: make this an object, not a dict


class Classifier(ClassifierInfo):
    linear_classifier: LinearClassifier


class ClassifierOutput(BaseModel):
    id: int
    classifier_id: int
    parquet_path: str


class TargetRecording(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: int
    xc_id: int | None
    filename: str | None
    label: str
    audio: np.ndarray


class AnalyzerDB:
    def __init__(self, config: config.Config):
        self.config = config
        self.engine = create_engine(f"sqlite:///{config.data_path}/{config.db_path}")
        tables.Base.metadata.create_all(self.engine)

    # --- Paths -------------------------------------------------------------

    @property
    def _classifiers_dir(self) -> str:
        return f"{self.config.data_path}/{self.config.classifiers_dir}"

    @property
    def _classifier_outputs_dir(self) -> str:
        return f"{self.config.data_path}/{self.config.classifier_outputs_dir}"

    @property
    def _target_recordings_dir(self) -> str:
        return f"{self.config.data_path}/{self.config.target_recordings_dir}"

    # --- Classifiers -------------------------------------------------------

    def _classifier_info(self, row: tables.Classifier) -> ClassifierInfo:
        return ClassifierInfo(
            id=row.id,
            datetime=dt.fromisoformat(row.datetime),
            embedding_model=row.embedding_model,
            metrics=_load_metrics(metrics_path(self._classifiers_dir, row.id)),
            labels=list(row.labels),
            num_train_steps=row.num_train_steps,
            learning_rate=row.learning_rate,
            rng=row.rng,
            train_ratio=row.train_ratio,
            weak_neg_rate=row.weak_neg_rate,
        )

    def get_classifier_info(self, classifier_id: int) -> ClassifierInfo:
        """Get a classifier's metadata and metrics, without loading its weights."""
        with Session(self.engine) as session:
            stmt = select(tables.Classifier).where(
                tables.Classifier.id == classifier_id
            )
            return self._classifier_info(session.execute(stmt).scalar_one())

    def get_classifier(self, classifier_id: int) -> Classifier:
        info = self.get_classifier_info(classifier_id)
        linear_classifier = LinearClassifier.load(
            linear_classifier_path(self._classifiers_dir, classifier_id)
        )
        return Classifier(**info.model_dump(), linear_classifier=linear_classifier)

    def get_all_classifiers(self) -> list[ClassifierInfo]:
        """List every classifier's metadata and metrics, weights excluded."""
        with Session(self.engine) as session:
            stmt = select(tables.Classifier).order_by(tables.Classifier.id)
            rows = session.execute(stmt).scalars().all()
            return [self._classifier_info(row) for row in rows]

    def insert_classifier(
        self,
        datetime: dt,
        embedding_model: str,
        labels: list[str],
        train_ratio: float,
        rng: int | None,
        learning_rate: float,
        weak_neg_rate: float,
        num_train_steps: float,
        metrics: dict[str, Any],  # TODO: make this an object, not a dict
        linear_classifier: LinearClassifier,
    ) -> int:
        with Session(self.engine) as session:
            db_classifier = tables.Classifier(
                datetime=datetime.isoformat(),
                embedding_model=embedding_model,
                labels=labels,
                train_ratio=train_ratio,
                rng=rng,
                learning_rate=learning_rate,
                weak_neg_rate=weak_neg_rate,
                num_train_steps=num_train_steps,
            )

            session.add(db_classifier)
            session.flush()
            classifier_id = db_classifier.id

            # Save the classifier and metrics files
            linear_classifier.save(
                linear_classifier_path(self._classifiers_dir, classifier_id)
            )
            np.savez(
                metrics_path(self._classifiers_dir, classifier_id),
                **metrics,
            )

            session.commit()
            return classifier_id

    # --- Classifier outputs ------------------------------------------------

    def get_classifier_output(self, classifier_output_id: int) -> ClassifierOutput:
        with Session(self.engine) as session:
            stmt = select(tables.ClassifierOutput).where(
                tables.ClassifierOutput.id == classifier_output_id
            )
            row = session.execute(stmt).scalar_one()

            return ClassifierOutput(
                id=classifier_output_id,
                classifier_id=row.classifier_id,
                parquet_path=classifier_output_path(
                    self._classifier_outputs_dir, classifier_output_id
                ),
            )

    def insert_classifier_output(self, classifier_id: int) -> int:
        with Session(self.engine) as session:
            db_classifier_output = tables.ClassifierOutput(classifier_id=classifier_id)
            session.add(db_classifier_output)
            session.commit()
            return db_classifier_output.id

    def get_all_classifier_outputs(self, classifier_id: int) -> list[ClassifierOutput]:
        with Session(self.engine) as session:
            stmt = (
                select(tables.ClassifierOutput)
                .where(tables.ClassifierOutput.classifier_id == classifier_id)
                .order_by(tables.ClassifierOutput.id)
            )
            return [
                ClassifierOutput(
                    id=row.id,
                    classifier_id=row.classifier_id,
                    parquet_path=classifier_output_path(
                        self._classifier_outputs_dir, row.id
                    ),
                )
                for row in session.execute(stmt).scalars().all()
            ]

    # --- Target recordings -------------------------------------------------

    def _load_target_audio(self, target_recording_id: int) -> np.ndarray:
        from perch_hoplite import audio_io

        return audio_io.load_audio_file(
            get_target_recording_path(self._target_recordings_dir, target_recording_id),
            SAMPLE_RATE,
        )

    def get_target_recording(self, target_recording_id: int) -> TargetRecording:
        with Session(self.engine) as session:
            stmt = select(tables.TargetRecording).where(
                tables.TargetRecording.id == target_recording_id
            )
            row = session.execute(stmt).scalar_one()

            return TargetRecording(
                id=row.id,
                xc_id=row.xc_id,
                filename=row.filename,
                label=row.label,
                audio=self._load_target_audio(row.id),
            )

    def insert_target_recording(
        self,
        xc_id: int | None,
        filename: str | None,
        label: str,
        audio: np.ndarray,
    ) -> int:
        from scipy.io import wavfile

        with Session(self.engine) as session:
            db_target_recording = tables.TargetRecording(
                xc_id=xc_id,
                filename=filename,
                label=label,
            )

            session.add(db_target_recording)
            session.flush()

            wavfile.write(
                get_target_recording_path(
                    self._target_recordings_dir, db_target_recording.id
                ),
                SAMPLE_RATE,
                audio,
            )

            session.commit()
            return db_target_recording.id

    def get_all_target_recordings(
        self, include_finished: bool
    ) -> list[TargetRecording]:
        """List target recordings, decoding each one's audio.

        Callers that only need metadata should use
        `get_target_recording_xc_ids` instead of paying for the file reads.
        """
        with Session(self.engine) as session:
            stmt = select(tables.TargetRecording)
            if not include_finished:
                stmt = stmt.where(tables.TargetRecording.finished.is_(False))

            return [
                TargetRecording(
                    id=row.id,
                    xc_id=row.xc_id,
                    filename=row.filename,
                    label=row.label,
                    audio=self._load_target_audio(row.id),
                )
                for row in session.execute(stmt).scalars().all()
            ]

    def get_target_recording_xc_ids(self) -> set[int]:
        """Get the Xeno-canto ids of every target recording already stored."""
        with Session(self.engine) as session:
            stmt = select(tables.TargetRecording.xc_id).where(
                tables.TargetRecording.xc_id.is_not(None)
            )
            return {
                xc_id
                for xc_id in session.execute(stmt).scalars().all()
                if xc_id is not None
            }

    def count_target_recordings(self, include_finished: bool) -> int:
        with Session(self.engine) as session:
            stmt = select(func.count()).select_from(tables.TargetRecording)
            if not include_finished:
                stmt = stmt.where(tables.TargetRecording.finished.is_(False))
            return session.execute(stmt).scalar_one()

    def set_finish_target_recording(self, target_recording_id: int, finished: bool):
        with Session(self.engine) as session:
            stmt = select(tables.TargetRecording).where(
                tables.TargetRecording.id == target_recording_id
            )
            db_target_recording = session.execute(stmt).scalar_one()
            db_target_recording.finished = finished
            session.commit()

            return db_target_recording.id

    # --- Classifier output windows -----------------------------------------

    def insert_classifier_output_window(
        self, classifier_output_id: int, window_id: int, logit: float, label: str
    ) -> int:
        with Session(self.engine) as session:
            row = tables.ClassifierOutputWindow(
                classifier_output_id=classifier_output_id,
                window_id=window_id,
                logit=logit,
                label=label,
            )
            session.add(row)
            session.commit()
            return row.id

    def insert_classifier_output_windows(
        self,
        classifier_output_id: int,
        windows: Sequence[tuple[int, float, str]],
    ) -> int:
        """Insert (window_id, logit, label) triples in a single transaction."""
        if not windows:
            return 0
        with Session(self.engine) as session:
            session.add_all(
                tables.ClassifierOutputWindow(
                    classifier_output_id=classifier_output_id,
                    window_id=window_id,
                    logit=logit,
                    label=label,
                )
                for window_id, logit, label in windows
            )
            session.commit()
            return len(windows)

    def get_classifier_output_window(
        self, classifier_output_window_id: int
    ) -> ClassifierOutputWindow:
        with Session(self.engine) as session:
            stmt = select(tables.ClassifierOutputWindow).where(
                tables.ClassifierOutputWindow.id == classifier_output_window_id
            )
            row = session.execute(stmt).scalar_one()

            return ClassifierOutputWindow(
                id=row.id,
                classifier_output_id=row.classifier_output_id,
                window_id=row.window_id,
                label=row.label,
                logit=row.logit,
            )

    def get_all_classifier_output_windows(
        self,
        classifier_output_id: int,
        window_id: int | None = None,
        label: str | None = None,
    ) -> list[ClassifierOutputWindow]:
        with Session(self.engine) as session:
            stmt = select(tables.ClassifierOutputWindow).where(
                tables.ClassifierOutputWindow.classifier_output_id
                == classifier_output_id
            )

            if window_id is not None:
                stmt = stmt.where(tables.ClassifierOutputWindow.window_id == window_id)
            if label is not None:
                stmt = stmt.where(tables.ClassifierOutputWindow.label == label)

            return [
                ClassifierOutputWindow(
                    id=row.id,
                    window_id=row.window_id,
                    label=row.label,
                    logit=row.logit,
                    classifier_output_id=row.classifier_output_id,
                )
                for row in session.execute(stmt).scalars().all()
            ]

    def get_classifier_output_labels(self, classifier_output_id: int) -> list[str]:
        """Get the distinct labels present in a classifier output's windows."""
        with Session(self.engine) as session:
            stmt = (
                select(tables.ClassifierOutputWindow.label)
                .where(
                    tables.ClassifierOutputWindow.classifier_output_id
                    == classifier_output_id
                )
                .distinct()
                .order_by(tables.ClassifierOutputWindow.label)
            )
            return list(session.execute(stmt).scalars().all())

    def get_existing_output_window_keys(
        self, classifier_output_id: int
    ) -> set[tuple[int, str]]:
        """Get the (window_id, label) pairs already stored for an output."""
        with Session(self.engine) as session:
            stmt = select(
                tables.ClassifierOutputWindow.window_id,
                tables.ClassifierOutputWindow.label,
            ).where(
                tables.ClassifierOutputWindow.classifier_output_id
                == classifier_output_id
            )
            return {(row.window_id, row.label) for row in session.execute(stmt)}
