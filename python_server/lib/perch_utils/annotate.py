from python_server.lib.db.db import AccountsDB
from chirp.projects.hoplite import interface

from etils import epath

from python_server.lib.models import PossibleExample


class AnnotatePossibleExamples:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: interface.GraphSearchDBInterface,
        precompute_search_dir: epath.Path | str,
        project_id: int,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.project_id = project_id

    def get_next_possible_example(self) -> PossibleExample:
        """
        Get the next possible example to annotate.
        """
        next_possible_example = self.db.get_next_possible_example(project_id=self.project_id)

        if next_possible_example is None:
            raise ValueError("No more possible examples to annotate.")

        return next_possible_example

    def finish_possible_example(self, possible_example: PossibleExample):
        """
        Finish annotating the possible example.
        """
        self.db.finish_possible_example(possible_example)

    def annotate_possible_example(
        self, possible_example: PossibleExample, annotation: str, provenance: str
    ):
        """
        Annotate the possible example. "Finishes" the possible example and
        adds it to the hoplite db as a labeled example.

        Args:
            possible_example: The possible example to annotate.
            annotation: The label for the possible example. This does not necessarily need
                to match the label of the possible example.
            provenance: The provenance of the label. Name of the person who labeled the example.
        """
        self.finish_possible_example(possible_example)
        label = interface.Label(
            embedding_id=possible_example.embedding_id,
            label=annotation,
            type=interface.LabelType.POSITIVE,
            provenance=provenance,
        )
        self.hoplite_db.insert_label(label)
