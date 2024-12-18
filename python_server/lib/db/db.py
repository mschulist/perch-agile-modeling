from sqlmodel import SQLModel, and_, create_engine, Session, not_, select, col
from typing import Optional, Sequence
from python_server.lib.models import (
    ClassifierResult,
    ClassifierRun,
    FinishedTargetRecording,
    PossibleExample,
    Project,
    ProjectContributor,
    TargetRecording,
    User,
    FinishedPossibleExample,
)


class AccountsDB:
    def __init__(self, db_name: str = "data/database.db"):
        sqlite_url = f"sqlite:///{db_name}"
        self.engine = create_engine(sqlite_url)
        self.session = Session(self.engine, expire_on_commit=False)

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

    def get_all_projects(self) -> Sequence[Project]:
        with Session(self.engine) as session:
            statement = select(Project)
            projects = session.exec(statement).all()
            return projects

    def get_project_contributors(self, project_id: int) -> Sequence[ProjectContributor]:
        with Session(self.engine) as session:
            statement = select(ProjectContributor).where(
                ProjectContributor.project_id == project_id
            )
            contributors = session.exec(statement).all()
            return contributors

    def get_projects_by_user(self, user_id: int) -> Sequence[ProjectContributor]:
        with Session(self.engine) as session:
            statement = select(ProjectContributor).where(
                ProjectContributor.user_id == user_id
            )
            projects = session.exec(statement).all()
            return projects

    def get_target_recordings(
        self,
        species_code: Optional[str],
        call_type: Optional[str],
        project_id: Optional[int],
    ) -> Sequence[TargetRecording]:
        """
        Get the list of previously gathered target recordings from the db that have not already been used by the project.

        Args:
            species_code: Species code of the target recordings.
            call_type: Call type of the target recordings.
            project_id: ID of the project.
        """
        with Session(self.engine) as session:
            subquery = (
                select(FinishedTargetRecording.target_recording_id)
                .where(FinishedTargetRecording.project_id == project_id)
                .subquery()
            )

            statement = select(TargetRecording).where(
                not_(
                    col(TargetRecording.id).in_(select(subquery.c.target_recording_id))
                )
            )

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

    def get_target_recording(
        self, target_recording_id: int
    ) -> Optional[TargetRecording]:
        """
        Get the target recording with the given id.

        Args:
            target_recording_id: The id of the target recording to get.

        Returns:
            The target recording with the given id.
        """
        with Session(self.engine) as session:
            statement = select(TargetRecording).where(
                TargetRecording.id == target_recording_id
            )
            target_recording = session.exec(statement).first()
            return target_recording

    def finish_target_recording(
        self, target_recording_id: int, project_id: int
    ) -> None:
        """
        Finish the target recording with the given id.

        Just adds the target recording to the finished_target_recordings table.

        Args:
            target_recording_id: The id of the target recording to finish.
            project_id: The id of the project that the target recording is being used for.
        """
        with Session(self.engine) as session:
            finished_target_recording = FinishedTargetRecording(
                target_recording_id=target_recording_id, project_id=project_id
            )
            session.add(finished_target_recording)
            session.commit()

    def get_finished_targets(
        self, project_id: int
    ) -> Sequence[FinishedTargetRecording]:
        """
        Get the list of finished target recordings for the given project.

        Args:
            project_id: The id of the project to get the finished target recordings for.

        Returns:
            The list of finished target recordings for the given project.
        """
        with Session(self.engine) as session:
            statement = select(FinishedTargetRecording).where(
                FinishedTargetRecording.project_id == project_id
            )
            finished_targets = session.exec(statement).all()
            return finished_targets

    def add_possible_example(self, possible_example: PossibleExample):
        """
        Adds a possible example to the database.

        Args:
            possible_example: The possible example to add to the database.

        Returns:
            The id of the possible example
        """
        with Session(self.engine) as session:
            pos_ex = session.merge(possible_example)
            session.add(pos_ex)
            session.commit()
            return pos_ex.id

    def get_possible_examples(self, project_id: int) -> Sequence[PossibleExample]:
        """
        Get the list of possible examples for the given project.

        Args:
            project_id: The id of the project to get the possible examples for.

        Returns:
            The list of possible examples for the given project.
        """
        with Session(self.engine) as session:
            statement = select(PossibleExample).where(
                PossibleExample.project_id == project_id
            )
            possible_examples = session.exec(statement).all()
            return possible_examples

    def get_next_possible_example(self, project_id) -> Optional[PossibleExample]:
        """
        Get the "next" possible example to annotate.

        This is just a "random" possible example that has not been annotated yet,
        meaning that it is not present in the finished_possible_examples table.

        Args:
            project_id: The id of the project to get the next possible example for.

        Returns:
            The next possible example to annotate.
        """
        with Session(self.engine) as session:
            subquery = (
                select(FinishedPossibleExample.possible_example_id)
                .where(FinishedPossibleExample.project_id == project_id)
                .subquery()
            )

            statement = select(PossibleExample).where(
                not_(
                    col(PossibleExample.id).in_(select(subquery.c.possible_example_id))
                )
            )

            possible_example = session.exec(statement).first()
            return possible_example

    def finish_possible_example(self, possible_example: PossibleExample):
        """
        Adds the possible example to the finished_possible_examples table.

        Args:
            possible_example: The possible example to finish.
        """
        if possible_example.id is None:
            raise ValueError("Possible example must have an id.")
        with Session(self.engine) as session:
            finished_possible_example = FinishedPossibleExample(
                possible_example_id=possible_example.id,
                project_id=possible_example.project_id,
            )
            session.add(finished_possible_example)
            session.commit()

    def get_possible_example_by_embed_id(
        self, embedding_id: int, project_id: int
    ) -> Optional[PossibleExample]:
        """
        Given an embedding id from the hoplite db, get the possible example from the accounts db.
        """

        with Session(self.engine) as session:
            statement = select(PossibleExample).where(
                and_(
                    PossibleExample.embedding_id == int(embedding_id),
                    PossibleExample.project_id == project_id,
                )
            )
            possible_example = session.exec(statement).first()
            return possible_example

    def add_classifier(self, classifier: ClassifierRun):
        """
        Adds a classifier run to the database.

        Args:
            classifier: The classifier run to add to the database.
        """
        with Session(self.engine) as session:
            session.add(classifier)
            session.commit()

    def add_classifier_result(self, classifier_result: ClassifierResult):
        """
        Adds a classifier result to the database.

        Args:
            classifier_result: The classifier result to add to the database.
        """
        with Session(self.engine) as session:
            session.add(classifier_result)
            session.commit()

    def get_classifier_result_by_embed_id_and_label(
        self, embed_id: int, label: str, project_id: int
    ) -> Optional[ClassifierResult]:
        """
        Given an embedding id and label from the hoplite db, get the classifier result from the accounts db.
        """

        with Session(self.engine) as session:
            statement = select(ClassifierResult).where(
                and_(
                    ClassifierResult.embedding_id == int(embed_id),
                    ClassifierResult.label == label,
                    ClassifierResult.project_id == project_id,
                )
            )
            classifier_result = session.exec(statement).first()
            return classifier_result

    def get_classifier_run_id_by_datetime(
        self, datetime: str, project_id: int
    ) -> Optional[int]:
        """
        Given a datetime and project id, get the classifier run id.
        """

        with Session(self.engine) as session:
            statement = select(ClassifierRun).where(
                and_(
                    ClassifierRun.datetime == datetime,
                    ClassifierRun.project_id == project_id,
                )
            )
            classifier_run = session.exec(statement).first()
            if classifier_run is None:
                return None
            return classifier_run.id

    def get_classifier_runs(self, project_id: int):
        """
        Get the classifier runs for the given project.
        """
        with Session(self.engine) as session:
            statement = select(ClassifierRun).where(
                ClassifierRun.project_id == project_id
            )
            classifier_runs = session.exec(statement).all()
            return classifier_runs

    def get_classifier_results(self, classifier_run_id: int, project_id: int):
        """
        Get the classifier results for the given classifier run and project.
        """
        with Session(self.engine) as session:
            statement = select(ClassifierResult).where(
                and_(
                    ClassifierResult.classifier_run_id == classifier_run_id,
                    ClassifierResult.project_id == project_id,
                )
            )
            classifier_results = session.exec(statement).all()
            return classifier_results

    def get_precompute_classify_embed_ids_by_label(self, label: str, project_id: int):
        """
        Get the embedding ids for the given label and project.
        """
        with Session(self.engine) as session:
            statement = select(ClassifierResult.embedding_id).where(
                and_(
                    ClassifierResult.label == label,
                    ClassifierResult.project_id == project_id,
                )
            )
            embed_ids = session.exec(statement).all()
            return embed_ids
