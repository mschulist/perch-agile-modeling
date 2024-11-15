from pyexpat import model
import tempfile
from typing import List, Sequence
from scipy.io import wavfile

from numpy import isin
from python_server.lib.db.db import AccountsDB
from etils import epath
from chirp.projects.hoplite import interface, score_functions, brutalism, search_results
from chirp.projects.zoo import model_configs
from chirp import audio_utils
from python_server.lib.models import PossibleExample, TargetRecording
from python_server.lib.perch_utils.target_recordings import (
    GatherTargetRecordings,
    get_target_recording_path,
)
import numpy as np


def get_possible_example_image_path(
    possible_example_id: int, precompute_search_dir: epath.Path
) -> epath.Path:
    """
    Get the path to the image for the possible example with the given id.
    """
    return precompute_search_dir / f"{possible_example_id}.png"


def get_possible_example_audio_path(
    possible_example_id: int, precompute_search_dir: epath.Path
) -> epath.Path:
    """
    Get the path to the audio for the possible example with the given id.
    """
    return precompute_search_dir / f"{possible_example_id}.wav"


class GatherPossibleExamples:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: interface.GraphSearchDBInterface,
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
        perch_model_config = hoplite_db.get_metadata("model_config")
        model_key = perch_model_config.model_key
        if not isinstance(model_key, str):
            raise ValueError("Model key must be a string.")
        model_class = model_configs.MODEL_CLASS_MAP[model_key]
        self.embedding_model = model_class.from_config(perch_model_config)

        self.sample_rate = self.embedding_model.sample_rate

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
            results, scores = self.search_hoplite_db(target_recording, num_examples_per_comb)

            # 3. Save the possible examples to the precompute search directory
            for result, score in zip(results, scores):
                self.save_search_result(result, score, target_recording)

    def get_target_recordings(
        self, species_codes: List[str], call_types: List[str], num_examples: int
    ) -> Sequence[TargetRecording]:
        """
        Get the list of target recordings from the db.
        """
        targets = GatherTargetRecordings(self.db, self.target_path)
        targets.process_req_for_targets(species_codes, call_types, num_examples, self.project_id)

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
        score_fn = score_functions.get_score_fn("dot")
        results, scores = brutalism.threaded_brute_search(
            db=self.hoplite_db,
            query_embedding=target_embedding,
            search_list_size=num_examples,
            score_fn=score_fn,  # type: ignore
        )

        return results, scores

    def save_search_result(
        self,
        search_result: search_results.SearchResult,
        score: float,
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
        source = self.hoplite_db.get_embedding_source(search_result.embedding_id)
        possible_example = PossibleExample(
            project_id=self.project_id,
            score=score,
            timestamp_s=source.offsets[0] // self.sample_rate,
            filename=source.source_id,
            target_recording_id=target_recording.id,
            target_recording=target_recording,
        )

        possible_example_id = self.db.add_possible_example(possible_example)

        if possible_example_id is None:
            raise ValueError("Failed to add possible example to the database.")

        output_filepath = get_possible_example_audio_path(
            possible_example_id, self.precompute_search_dir
        )

        audio_slice = audio_utils.load_audio_window_soundfile(
            source.source_id,
            offset_s=source.offsets[0],
            window_size_s=5.0,  # TODO: make this a parameter, not hard coded (although probably fine)
            sample_rate=self.sample_rate,
        )

        with tempfile.NamedTemporaryFile() as tmp_file:
            wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio_slice))
            epath.Path(tmp_file.name).copy(output_filepath)
