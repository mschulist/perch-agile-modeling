from typing import List, Optional
from chirp.projects.hoplite import interface
from matplotlib.pyplot import annotate
from python_server.lib.db.db import AccountsDB
from etils import epath

from python_server.lib.models import AnnotatedRecording
from python_server.lib.perch_utils.search import (
    get_possible_example_audio_path,
    get_possible_example_image_path,
)


class ExploreAnnotations:
    """
    Using the precompute search dir (as all of the annotated recordings are there),
    this class will allow the user to explore the annotations of the possible examples.

    For example, say a user wants to see all of the possible examples that have been annotated
    for a given species to make sure that there are not any mistakes.

    This is the most important part of this agile modeling process. It allows us to ensure that our
    model is only being trained on the finest of data.
    """

    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: interface.GraphSearchDBInterface,
        project_id: int,
        precompute_search_dir: str,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.precompute_search_dir = epath.Path(precompute_search_dir)

    def get_annotations_summary(self):
        """
        Get a summary of the annotations for the given project.

        For each species, list the number of possible examples that have been annotated.
        """
        return self.hoplite_db.get_class_counts()

    def get_annotations_by_label(self, label: str) -> List[AnnotatedRecording]:
        """
        Get the annotations by the given label. Here label usually corresponds to the species code
        (although it does not necessarily have to, such as an unknown label).

        Args:
            species_code: The species code to get the annotations for.

        Returns:
            List of AnnotatedRecordings for the given species.
        """
        embedding_ids = self.hoplite_db.get_embeddings_by_label(label=label)
        if len(embedding_ids) == 0:
            return []

        # we need to go through each id and find out if there are any other labels with the same embedding id
        # if we have, then we need to get the label for that embedding id
        # TODO: ideally, there would be a more efficient way to do this (joins in the db), but that
        # would require changing the hoplite db interface...

        annotated_recordings: List[AnnotatedRecording] = []
        for embedding_id in embedding_ids:
            annotated_recording = self._get_annotated_recording_by_embedding_id(embedding_id)
            if annotated_recording is not None:
                annotated_recordings.append(annotated_recording)

        return annotated_recordings

    def _get_annotated_recording_by_embedding_id(
        self, embedding_id: int
    ) -> Optional[AnnotatedRecording]:
        """
        Helper method to get the AnnotatedRecording for the given embedding id.
        """

        labels_list: List[str] = []
        labels = self.hoplite_db.get_labels(embedding_id=embedding_id)
        for label in labels:
            labels_list.append(label.label)

        possible_example = self.db.get_possible_example_by_embed_id(embedding_id)
        if possible_example is None or possible_example.id is None:
            return None

        image_path = get_possible_example_image_path(
            possible_example.id, self.precompute_search_dir
        )
        audio_path = get_possible_example_audio_path(
            possible_example.id, self.precompute_search_dir
        )

        return AnnotatedRecording(
            embedding_id=embedding_id,
            species_labels=labels_list,
            filename=possible_example.filename,
            timestamp_s=possible_example.timestamp_s,
            audio_path=str(audio_path),
            image_path=str(image_path),
        )
