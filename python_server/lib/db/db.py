from sqlmodel import SQLModel, create_engine, Session, select
from typing import Optional
from python_server.lib.models import Project, User

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