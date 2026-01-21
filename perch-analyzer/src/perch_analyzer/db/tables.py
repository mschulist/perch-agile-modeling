from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column


class Base(DeclarativeBase):
    pass


class Classifier(Base):
    __tablename__ = "classifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    datetime: Mapped[str] = mapped_column()
    embedding_model: Mapped[str] = mapped_column()
    labels: Mapped[tuple[str, ...]] = mapped_column()
    train_ratio: Mapped[float] = mapped_column()
    rng: Mapped[int | None] = mapped_column(nullable=True)
    max_train_examples_per_label: Mapped[int] = mapped_column()
    learning_rate: Mapped[float] = mapped_column()
    weak_neg_rate: Mapped[float] = mapped_column()
    num_train_steps: Mapped[int] = mapped_column()


class ClassifierOutput(Base):
    __tablename__ = "classifier_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    classifier_id: Mapped[int] = mapped_column(ForeignKey("classifiers.id"))
