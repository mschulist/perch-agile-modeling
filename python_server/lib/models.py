from pydantic import BaseModel
from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship  # type: ignore


class ProjectContributor(SQLModel, table=True):
    __tablename__ = "project_contributors"  # type: ignore

    project_id: Optional[int] = Field(default=None, foreign_key="projects.id", primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", primary_key=True)


class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    email: str = Field(index=True)
    hashed_password: str

    owned_projects: List["Project"] = Relationship(
        back_populates="owner", sa_relationship_kwargs={"foreign_keys": "[Project.owner_id]"}
    )
    contributing_projects: List["Project"] = Relationship(
        back_populates="contributors", link_model=ProjectContributor
    )


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


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: str
