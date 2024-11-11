from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional
from python_server.lib.models import Project, TargetRecording, User

DB_NAME = "data/database.db"
sqlite_url = f"sqlite:///{DB_NAME}"
engine = create_engine(sqlite_url)


class AccountsDB:
    def __init__(self):
        self.engine = engine
        self.session = Session(engine)

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

    def get_target_recordings(self):
        """
        Get the list of previously gathered target recordings from the db.
        """
        with Session(self.engine) as session:
            statement = select(TargetRecording)
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
