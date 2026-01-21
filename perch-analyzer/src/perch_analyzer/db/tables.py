from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


class Base(DeclarativeBase):
    pass


class Classifier(Base):
    __tablename__ = "classifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    datetime: Mapped[str] = mapped_column()
    embedding_model: Mapped[str] = mapped_column()


class ClassifierOutput(Base):
    __tablename__ = "classifier_outputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    classifier_id: Mapped[int] = mapped_column(ForeignKey("classifiers.id"))
