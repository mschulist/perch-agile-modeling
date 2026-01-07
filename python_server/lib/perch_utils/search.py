from typing import List, Sequence

from ml_collections import config_dict

from python_server.lib.auth import get_temp_gs_url
from python_server.lib.db.db import AccountsDB
from etils import epath
from perch_hoplite.zoo import model_configs
import perch_hoplite.audio_io as audio_utils
from perch_hoplite.db import interface

from python_server.lib.models import TargetRecording
from python_server.lib.perch_utils.target_recordings import (
    GatherTargetRecordings,
    get_target_recording_path,
)

from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt

SEARCH_PROVENANCE = "searched_annotator"


def get_possible_example_image_path(
    possible_example_id: int, precompute_search_dir: epath.Path, temp_url: bool = False
) -> epath.Path | str:
    """
    Get the path to the image for the possible example with the given id.
    """
    if str(precompute_search_dir).startswith("gs://") and temp_url:
        return get_temp_gs_url(
            f"{str(precompute_search_dir)}/{possible_example_id}.png"
        )
    return precompute_search_dir / f"{possible_example_id}.png"


def get_possible_example_audio_path(
    possible_example_id: int, precompute_search_dir: epath.Path, temp_url: bool = False
) -> epath.Path | str:
    """
    Get the path to the audio for the possible example with the given id.
    """
    if str(precompute_search_dir).startswith("gs://") and temp_url:
        return get_temp_gs_url(
            f"{str(precompute_search_dir)}/{possible_example_id}.wav"
        )
    return precompute_search_dir / f"{possible_example_id}.wav"


class GatherPossibleExamples:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        precompute_search_dir: epath.Path | str,
        target_path: epath.Path | str,
        project_id: int,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.project_id = project_id
        self.target_path = epath.Path(target_path)

        # set up the embedding model for the hoplite db
        print("CONFIG", hoplite_db.get_metadata(None))
        perch_model_config = hoplite_db.get_metadata("model_config")
        # TODO: fix this crappy config
        if not isinstance(perch_model_config, config_dict.ConfigDict):
            raise ValueError("Model config must be a ConfigDict.")
        model_key = perch_model_config.model_key
        if not isinstance(model_key, str):
            raise ValueError("Model key must be a string.")
        model_class = model_configs.get_model_class(model_key)
        model_config = perch_model_config.model_config
        if not isinstance(model_config, config_dict.ConfigDict):
            raise ValueError("Inner nested model config must be a ConfigDict.")
        self.embedding_model = model_class.from_config(model_config)

        self.sample_rate = self.embedding_model.sample_rate

        self.base_path = hoplite_db.get_metadata("audio_sources").audio_globs[0][  # type: ignore
            "base_path"
        ]

    def get_possible_examples(
        self,
        species_codes: List[str],
        call_types: List[str],
        num_examples_per_comb: int,
        num_target_recordings: int = 5,
    ):
        """
        Get the possible examples for the given species codes and call types.

        This is the main method for this class, where we will go out and complete the following:
        - Get the target recordings for the given species code and call type.
        - Search our hoplite database for similar examples.
        - Save the possible examples to the precompute search directory.

        Args:
            species_codes: List of species codes.
            call_types: List of call types.
            num_examples_per_comb: Number of examples to get for each (species code, call type, target_recording) combination.
            num_target_recordings: Number of target recordings to get.
        """

        # 1. Get the target recordings
        target_recordings = self.get_target_recordings(
            species_codes, call_types, num_target_recordings
        )

        # 2. Search the hoplite database for similar examples
        # This may involve some parallelization...at some point
        for target_recording in target_recordings:
            close_results = self.search_hoplite_db(
                target_recording, num_examples_per_comb
            )

            # 3. Save the possible examples to the precompute search directory
            for close_result in close_results:
                window_id = int.from_bytes(close_result.key, "little")  # type: ignore
                if self.db.get_possible_example_by_embed_id(window_id, self.project_id):
                    # skip if we already have this example
                    print(f"Skipping example {window_id} as it already exists.")
                    continue

                self.save_search_result(window_id, target_recording)

            # finish the target recording: ie we have searched for all possible examples
            # and do not want to search for them again using the same target recording
            if target_recording.id is None:
                raise ValueError("Target recording must have an id.")
            self.db.finish_target_recording(target_recording.id, self.project_id)

    def get_target_recordings(
        self, species_codes: List[str], call_types: List[str], num_examples: int
    ) -> Sequence[TargetRecording]:
        """
        Get the list of target recordings from the db.
        """
        targets = GatherTargetRecordings(self.db, self.target_path)
        targets.process_req_for_targets(
            species_codes, call_types, num_examples, self.project_id
        )

        return self.db.get_target_recordings(
            species_code=None, call_type=None, project_id=self.project_id
        )

    def search_hoplite_db(self, target_recording: TargetRecording, num_examples: int):
        """
        Search the hoplite database for similar examples.
        """
        if target_recording.id is None:
            raise ValueError("Target recording must have an id.")
        target_path = get_target_recording_path(target_recording.id, self.target_path)
        target_audio = audio_utils.load_audio_file(target_path, self.sample_rate)

        # get the embedding for the target audio
        target_embedding = self.embedding_model.embed(target_audio).embeddings[0, 0]  # type: ignore

        # search the hoplite db for similar examples
        # we don't use the scores right now, but maybe in the future we could...
        close_results = self.hoplite_db.ui.search(target_embedding, num_examples)
        return close_results

    def save_search_result(
        self,
        window_id: int,
        target_recording: TargetRecording,
    ):
        """
        Save the search result to the precompute search directory and add to the database.

        Args:
            search_result: Search result to save.
            score: Score of the search result.
            target_recording: Target recording that the search result is associated with.
        """
        # insert into database
        window = self.hoplite_db.get_window(window_id)

        # add an annotation with the POSSIBLE label for the window
        self.hoplite_db.insert_annotation(
            window.id,
            target_recording.species,
            interface.LabelType.POSSIBLE,
            SEARCH_PROVENANCE,
        )
