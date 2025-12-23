from typing import List, Optional

from python_server.lib.db.db import AccountsDB
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt

from perch_hoplite.db import interface

from etils import epath
from ml_collections import config_dict

from python_server.lib.models import PossibleExampleResponse
from python_server.lib.perch_utils.search import (
    get_possible_example_audio_path,
    get_possible_example_image_path,
)


class AnnotatePossibleExamples:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        precompute_search_dir: epath.Path | str,
        project_id: int,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.project_id = project_id

    def get_next_possible_example(self) -> interface.Annotation | None:
        """
        Get the next possible example to annotate.
        """
        annotations = self.hoplite_db.get_all_annotations(
            config_dict.create(eq=dict(label_type=interface.LabelType.POSSIBLE))
        )
        if len(annotations) == 0:
            return None

        return annotations[0]

    def finish_possible_example(self, annotation_id: int):
        """
        Finish annotating the possible example. The annotation id must have the possible label type
        """
        annotation = self.hoplite_db.get_annotation(annotation_id)
        assert annotation.label_type == interface.LabelType.POSSIBLE, (
            f"annotation must have POSSIBLE label type when finishing: {annotation}"
        )
        self.hoplite_db.remove_annotation(annotation_id)

    def annotate_possible_example(
        self,
        window_id: int,
        annotation: str,
        provenance: str,
    ):
        """
        Annotate the possible example.

        Args:
            window_id: The possible example window id to annotate
            annotation: The label for the possible example. This does not necessarily need
                to match the label of the possible example.
            provenance: The provenance of the label. Name of the person who labeled the example.
        """
        succ = self.hoplite_db.insert_annotation(
            window_id=window_id,
            label=annotation,
            label_type=interface.LabelType.POSITIVE,
            provenance=provenance,
        )
        if not succ:
            raise ValueError("Could not insert label.")
        return succ

    def annotate_possible_example_by_embedding_id(
        self,
        window_id: int,
        annotations: List[str],
        provenance: str,
    ):
        """
        Annotate the possible example by the embedding id

        The frontend does not have access to the entire PossibleExample object,
        so this method will assist in that case.

        We can also label a single embedding id with multiple labels if needed.

        Args:
            window_id: The window id to annotate.
            annotations: The list of labels for the embedding id.
            provenance: The provenance of the label. Name of the person who labeled the example.
        """
        if len(annotations) == 0:
            raise ValueError("Need at least one annotation.")
        for annotation in annotations:
            self.annotate_possible_example(window_id, annotation, provenance)

        possible_annotations = self.hoplite_db.get_all_annotations(
            config_dict.create(
                eq=dict(
                    label_type=interface.LabelType.POSSIBLE,
                    window_id=window_id,
                )
            )
        )
        for pa in possible_annotations:
            self.finish_possible_example(pa.id)
        self.hoplite_db.commit()

    def get_next_possible_example_with_data(self) -> Optional[PossibleExampleResponse]:
        """
        Get the next possible example to annotate with the audio and image paths.

        Meant to be used by the api to get the response for the next possible example.
        """
        annotation = self.get_next_possible_example()
        if annotation is None:
            return None
        window = self.hoplite_db.get_window(annotation.window_id)
        image_path = get_possible_example_image_path(
            window.id, self.precompute_search_dir
        )
        audio_path = get_possible_example_audio_path(
            window.id, self.precompute_search_dir
        )

        recording = self.hoplite_db.get_recording(window.recording_id)

        return PossibleExampleResponse(
            embedding_id=window.id,
            filename=recording.filename,
            timestamp_s=window.offsets[0],
            score=-1,  # score no longer used, what does the score even represent (besides cos(theta))?!
            image_path=str(image_path),
            audio_path=str(audio_path),
            target_species=annotation.label,
            target_call_type="",  # call type no longer used
        )
