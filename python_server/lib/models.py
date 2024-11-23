from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship


class ProjectContributor(SQLModel, table=True):
    __tablename__ = "project_contributors"  # type: ignore

    project_id: Optional[int] = Field(
        default=None, foreign_key="projects.id", primary_key=True
    )
    user_id: Optional[int] = Field(
        default=None, foreign_key="users.id", primary_key=True
    )


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True)
    hashed_password: str

    owned_projects: List["Project"] = Relationship(
        back_populates="owner",
        sa_relationship_kwargs={"foreign_keys": "[Project.owner_id]"},
    )
    contributing_projects: List["Project"] = Relationship(
        back_populates="contributors", link_model=ProjectContributor
    )


class UserResponse(BaseModel):
    """
    We do not return the hashed password in the response.
    """

    name: str
    email: str


class Project(SQLModel, table=True):
    __tablename__ = "projects"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    owner_id: Optional[int] = Field(default=None, foreign_key="users.id")

    owner: Optional[User] = Relationship(
        back_populates="owned_projects",
        sa_relationship_kwargs={"foreign_keys": "[Project.owner_id]"},
    )
    contributors: List[User] = Relationship(
        back_populates="contributing_projects", link_model=ProjectContributor
    )
    finished_target_recordings: List["FinishedTargetRecording"] = Relationship(
        back_populates="project"
    )
    finished_possible_examples: List["FinishedPossibleExample"] = Relationship(
        back_populates="project"
    )
    possible_examples: List["PossibleExample"] = Relationship(back_populates="project")


class TargetRecording(SQLModel, table=True):
    """
    Table to store all of the target recordings for all projects. Target recordings are from xc and are
    used to search the ARU dataset for similar recordings.

    Multiple projects may want to look for the same species, so we don't want to duplicate effort.

    The species is the ebird 6-code from the xeno-canto recording, e.g. "swathr" (we convert to ebird 6-codes).
    When humans look at the recordings, they might want to put a more specific label on them, e.g. "swathr_call".

    The call type is the xeno-canto call type, which may or may not be accurate. It is just there so that
    humans can get some diversity in the examples they want to attempt to find in their own data.
    """

    __tablename__ = "target_recordings"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    xc_id: str = Field(index=True)
    species: str = Field(index=True)
    call_type: str = Field(index=True)
    timestamp_s: float = Field(index=True)

    finished_target_recordings: List["FinishedTargetRecording"] = Relationship(
        back_populates="target_recording"
    )
    possible_examples: List["PossibleExample"] = Relationship(
        back_populates="target_recording"
    )


class FinishedTargetRecording(SQLModel, table=True):
    """
    Table to store all of the target recordings that have already been used to search the dataset.
    """

    __tablename__ = "finished_target_recordings"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    target_recording_id: Optional[int] = Field(
        default=None, foreign_key="target_recordings.id"
    )
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")

    target_recording: Optional[TargetRecording] = Relationship(
        back_populates="finished_target_recordings"
    )
    project: Optional[Project] = Relationship(
        back_populates="finished_target_recordings"
    )


class PossibleExample(SQLModel, table=True):
    """
    Table to store all of the possible examples for all projects.

    These are the recordings from the ARU dataset that are "similar" to the target recordings for a particular species.
    """

    __tablename__ = "possible_examples"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(index=True)
    timestamp_s: float = Field(index=True)
    score: float = Field(index=True)
    embedding_id: int = Field(index=True, unique=True)

    target_recording_id: Optional[int] = Field(
        default=None, foreign_key="target_recordings.id"
    )
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")

    target_recording: Optional[TargetRecording] = Relationship(
        back_populates="possible_examples"
    )
    project: Optional[Project] = Relationship(back_populates="possible_examples")

    finished_possible_examples: List["FinishedPossibleExample"] = Relationship(
        back_populates="possible_example"
    )


class FinishedPossibleExample(SQLModel, table=True):
    """
    Table to store all of the possible examples that have already been labeled by humans.
    """

    __tablename__ = "finished_possible_examples"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    possible_example_id: Optional[int] = Field(
        default=None, foreign_key="possible_examples.id"
    )
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id")

    possible_example: Optional[PossibleExample] = Relationship(
        back_populates="finished_possible_examples"
    )
    project: Optional[Project] = Relationship(
        back_populates="finished_possible_examples"
    )


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str


class PossibleExampleResponse(BaseModel):
    embedding_id: int
    filename: str
    timestamp_s: float
    score: float
    image_path: str
    audio_path: str
    target_species: str
    target_call_type: str


class AnnotatedRecording(BaseModel):
    """
    We provide a list of species labels because a recording may have multiple species in it.

    Provenance is the name of the person who labeled the example.

    The embedding_id is the id of the embedding in the hoplite db.

    The image_path and audio_path are the paths to the image and audio of the recording.

    The timestamp_s is the timestamp of the recording in seconds.

    The filename is the filename of the recording (also called source in hoplite).
    """

    filename: str
    timestamp_s: float
    species_labels: List[str]
    embedding_id: int
    image_path: str
    audio_path: str
