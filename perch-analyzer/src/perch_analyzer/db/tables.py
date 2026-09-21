from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Classifier(Base):
    __tablename__ = "classifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    datetime: Mapped[str] = mapped_column()
    embedding_model: Mapped[str] = mapped_column()
    labels: Mapped[list[str]] = mapped_column(JSON)
    train_ratio: Mapped[float] = mapped_column()
    rng: Mapped[int | None] = mapped_column(nullable=True)
    # Vestigial: perch-hoplite's AgileDataManager no longer caps training
    # examples per label. Kept (with a default) so existing databases, whose
    # column is NOT NULL, still accept inserts.
    max_train_examples_per_label: Mapped[int] = mapped_column(default=0)
    learning_rate: Mapped[float] = mapped_column()
    weak_neg_rate: Mapped[float] = mapped_column()
    num_train_steps: Mapped[int] = mapped_column()


class ClassifierOutput(Base):
    __tablename__ = "classifier_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    classifier_id: Mapped[int] = mapped_column(ForeignKey("classifiers.id"))


class ClassifierOutputWindow(Base):
    __tablename__ = "classifier_output_windows"

    id: Mapped[int] = mapped_column(primary_key=True)
    classifier_output_id: Mapped[int] = mapped_column(
        ForeignKey("classifier_outputs.id")
    )
    window_id: Mapped[int] = mapped_column(nullable=False, unique=False)
    logit: Mapped[float] = mapped_column(nullable=False, unique=False)
    label: Mapped[str] = mapped_column(nullable=False, unique=False)


class TargetRecording(Base):
    __tablename__ = "target_recordings"

    id: Mapped[int] = mapped_column(primary_key=True)
    xc_id: Mapped[int | None] = mapped_column(nullable=True, unique=False)
    filename: Mapped[str | None] = mapped_column(nullable=True, unique=False)
    label: Mapped[str] = mapped_column()
    finished: Mapped[bool] = mapped_column(default=False)
