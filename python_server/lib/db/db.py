from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional, Sequence
from python_server.lib.models import FinishedTargetRecording, Project, TargetRecording, User


class AccountsDB:
    def __init__(self, db_name: str = "data/database.db"):
        sqlite_url = f"sqlite:///{db_name}"
        engine = create_engine(sqlite_url)
        self.engine = engine
        self.session = Session(engine)

    def setup(self):
        SQLModel.metadata.create_all(self.engine)

    def get_user(self, email: str) -> Optional[User]:
        with Session(self.engine) as session:
            statement = select(User).where(User.email == email)
            user = session.exec(statement).first()
            return user

    def create_project(self, project: Project):
        with Session(self.engine) as session:
            session.add(project)
            session.commit()

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def add_user(self, user: User):
        with Session(self.engine) as session:
            session.add(user)
            session.commit()

    def get_project(self, project_id: int) -> Optional[Project]:
        with Session(self.engine) as session:
            statement = select(Project).where(Project.id == project_id)
            project = session.exec(statement).first()
            return project

    def get_target_recordings(
        self, species_code: Optional[str], call_type: Optional[str], project_id: Optional[int]
    ) -> Sequence[TargetRecording]:
        """
        Get the list of previously gathered target recordings from the db that have not already been used by the project.

        Args:
            species_code: Species code of the target recordings.
            call_type: Call type of the target recordings.
            project_id: ID of the project.
        """
        with Session(self.engine) as session:
            statement = select(TargetRecording)

            if project_id is not None:
                statement.outerjoin(
                    FinishedTargetRecording,
                ).where(
                    FinishedTargetRecording.project_id == project_id
                ).where(FinishedTargetRecording.target_recording_id == TargetRecording.id)

            if species_code is not None:
                statement = statement.where(TargetRecording.species == species_code)
            if call_type is not None:
                statement = statement.where(TargetRecording.call_type == call_type)

            target_recordings = session.exec(statement).all()
            return target_recordings

    def add_target_recording(self, target_recording: TargetRecording):
        """
        Adds a target recording to the database.

        Args:
            target_recording: The target recording to add to the database.

        Returns:
            The id of the target recording
        """
        with Session(self.engine) as session:
            session.add(target_recording)
            session.commit()
            return target_recording.id

    def get_target_recording(self, target_recording_id: int) -> Optional[TargetRecording]:
        """
        Get the target recording with the given id.

        Args:
            target_recording_id: The id of the target recording to get.

        Returns:
            The target recording with the given id.
        """
        with Session(self.engine) as session:
            statement = select(TargetRecording).where(TargetRecording.id == target_recording_id)
            target_recording = session.exec(statement).first()
            return target_recording

    def finish_target_recording(self, target_recording_id: int) -> None:
        """
        Finish the target recording with the given id.

        Just adds the target recording to the finished_target_recordings table.

        Args:
            target_recording_id: The id of the target recording to finish.
        """
        with Session(self.engine) as session:
            finished_target_recording = FinishedTargetRecording(
                target_recording_id=target_recording_id
            )
            session.add(finished_target_recording)
            session.commit()
