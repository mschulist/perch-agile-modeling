import tempfile
from typing import List
from perch_hoplite.db import interface
from python_server.lib.db.db import AccountsDB
from etils import epath

from python_server.lib.models import AnnotatedWindow
from python_server.lib.perch_utils.search import (
    get_possible_example_audio_path,
    get_possible_example_image_path,
)
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt

from perch_hoplite.agile import embedding_display
import perch_hoplite.audio_io as audio_utils
from scipy.io import wavfile
from librosa import display as librosa_display
import matplotlib.pyplot as plt
import numpy as np
from ml_collections import config_dict


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
        hoplite_db: SQLiteUsearchDBExt,
        project_id: int,
        precompute_search_dir: str,
        provenance: str,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.project_id = project_id
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.provenance = provenance

    def get_annotations_summary(self):
        """
        Get a summary of the annotations for the given project.

        For each species, list the number of possible examples that have been annotated.
        """
        return self.hoplite_db.count_each_label()

    def get_annotations_by_label(self, label: str) -> List[AnnotatedWindow]:
        """
        Get the annotations by the given label. Here label usually corresponds to the species code
        (although it does not necessarily have to, such as an unknown label).

        Args:
            label: The species code to get the annotations for.

        Returns:
            List of AnnotatedWindows for the given species.
        """
        window_ids = self.hoplite_db.match_window_ids(
            annotations_filter=config_dict.create(eq={"label": label})
        )
        if len(window_ids) == 0:
            return []

        # new hoplite DB, thanks!!
        # Go through each window (that has been annotated with the label of interest) and
        # find all of the annotations for that window
        annotated_recordings: List[AnnotatedWindow] = []
        for window_id in window_ids:
            window = self.hoplite_db.get_window(window_id)

            if window is not None:
                recording = self.hoplite_db.get_recording(window.recording_id)
                labels = self.hoplite_db.get_all_annotations(
                    config_dict.create(eq={"window_id", window.id})
                )
                annotated_window = AnnotatedWindow(
                    filename=recording.filename,
                    timestamp_s=window.offsets[0],
                    embedding_id=window.id,
                    species_labels=[lab.label for lab in labels],
                    audio_path=str(
                        get_possible_example_audio_path(
                            window.id, self.precompute_search_dir, True
                        )
                    ),
                    image_path=str(
                        get_possible_example_image_path(
                            window.id, self.precompute_search_dir, True
                        )
                    ),
                )
                annotated_recordings.append(annotated_window)
            else:
                # TODO: some handling here, maybe not needed after full switch to new hoplite DB
                raise ValueError(
                    f"Could not find annotated recording for embedding id {window_id}"
                )

        return annotated_recordings

    def _remove_label(self, window_id: int, label: str):
        """
        Remove the given label from the given embedding id.

        Ideally, this is not directly called from the api as it could be dangerous.

        User should call change_annotation instead for more safety.

        Args:
            embedding_id: The embedding id to remove the label from.
            label: The label to remove.
        """

        # first get the annotation that matches the window_id and label
        annotations = self.hoplite_db.get_all_annotations(
            config_dict.create(eq={"window_id": window_id, "label": label})
        )
        # make sure that we have a single annotation
        if len(annotations) == 0:
            print(
                f"no annotation with window_id={window_id}, label={label}, so this is a no op"
            )
            return
        if len(annotations) > 1:
            raise ValueError(
                f"there is more than one annoation with window_id={window_id}, label={label}"
            )
        self.hoplite_db.remove_annotation(annotations[0].id)

    def change_annotation(self, window_id: int, new_labels: List[str]):
        """
        Change the annotation for the given embedding id from the to the new labels.

        Because we allow for multiple labels for a given embedding id, we need to make sure that
        we are only changing the labels that we want to change.

        To do this, we take the "detect" which labels are different and then remove the old labels
        that have changed and add the new labels that have changed.

        Args:
            embedding_id: The embedding id to change the annotation for.
            new_labels: The new labels to change to.
        """
        old_labels_set = {
            x.label
            for x in self.hoplite_db.get_all_annotations(
                config_dict.create(eq={"window_id": window_id})
            )
        }
        new_labels_set = set(new_labels)

        labels_to_remove = old_labels_set - new_labels_set
        labels_to_add = new_labels_set - old_labels_set

        for label in labels_to_remove:
            self._remove_label(window_id, label)

        for label in labels_to_add:
            self.hoplite_db.insert_annotation(
                window_id=window_id,
                label=label,
                label_type=interface.LabelType.POSITIVE,
                provenance=self.provenance,
            )

        self.hoplite_db.commit()


def flush_window_to_disk(
    recording: interface.Recording,
    window: interface.Window,
    precompute_search_dir: str,
    sample_rate: int,
    base_path: str,
):
    """
    Save the audio and image results to the precompute search directory.
    """
    # First, load the audio and save it to the precompute classify directory
    # we can reuse the same function even though it probably is not named correctly
    audio_output_filepath = get_possible_example_audio_path(
        window.id, epath.Path(precompute_search_dir)
    )

    audio_slice = audio_utils.load_audio_window_soundfile(
        f"{base_path}/{recording.filename}",
        offset_s=window.offsets[0],
        window_size_s=5.0,  # TODO: make this a parameter, not hard coded (although probably fine)
        sample_rate=sample_rate,
    )

    with tempfile.NamedTemporaryFile() as tmp_file:
        wavfile.write(tmp_file.name, sample_rate, np.float32(audio_slice))
        epath.Path(tmp_file.name).copy(audio_output_filepath)

    # Second, get the spectrogram and save it to the precompute classify directory
    image_output_filepath = get_possible_example_image_path(
        window.id, epath.Path(precompute_search_dir)
    )

    melspec_layer = embedding_display.get_melspec_layer(sample_rate)
    if audio_slice.shape[0] < sample_rate / 100 + 1:
        # Center pad if audio is too short.
        zs = np.zeros([sample_rate // 10], dtype=audio_slice.dtype)
        audio_slice = np.concatenate([zs, audio_slice, zs], axis=0)
    melspec = melspec_layer(audio_slice).T  # type: ignore

    librosa_display.specshow(
        melspec,
        sr=sample_rate,
        y_axis="mel",
        x_axis="time",
        hop_length=sample_rate // 100,
        cmap="Greys",
    )
    # for some reason librosa displays the image upside down
    plt.gca().invert_yaxis()
    with epath.Path(image_output_filepath).open("wb") as f:
        plt.savefig(f)
    plt.close()
