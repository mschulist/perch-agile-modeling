import tempfile
from typing import List, Sequence
from scipy.io import wavfile

from ml_collections import config_dict
from librosa import display as librosa_display
import matplotlib.pyplot as plt

from python_server.lib.auth import get_temp_gs_url
from python_server.lib.db.db import AccountsDB
from etils import epath
from hoplite.db import sqlite_usearch_impl, interface
from hoplite.zoo import model_configs
from hoplite.agile import embedding_display
import hoplite.audio_io as audio_utils

from python_server.lib.models import PossibleExample, TargetRecording
from python_server.lib.perch_utils.target_recordings import (
    GatherTargetRecordings,
    get_target_recording_path,
)
import numpy as np


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
        hoplite_db: sqlite_usearch_impl.SQLiteUsearchDB,
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
        model_class = model_configs.MODEL_CLASS_MAP[model_key]
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
                embed_id = int.from_bytes(close_result.key, "little")  # type: ignore
                if self.db.get_possible_example_by_embed_id(embed_id, self.project_id):
                    # skip if we already have this example
                    print(f"Skipping example {embed_id} as it already exists.")
                    continue
                self.save_search_result(
                    embed_id, close_result.distance, target_recording
                )

            # finish the targer recording: ie we have searched for all possible examples
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
        embedding_id: int,
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

        source = self.hoplite_db.get_embedding_source(embedding_id)
        possible_example = PossibleExample(
            project_id=self.project_id,
            score=score,
            timestamp_s=source.offsets[0],
            filename=source.source_id,
            target_recording_id=target_recording.id,
            target_recording=target_recording,
            embedding_id=embedding_id,
        )

        possible_example_id = self.db.add_possible_example(possible_example)

        if possible_example_id is None:
            raise ValueError("Failed to add possible example to the database.")

        # save the audio and image results
        self.flush_search_result_to_disk(source, possible_example_id)

    def flush_search_result_to_disk(
        self, embedding_source: interface.EmbeddingSource, possible_example_id: int
    ):
        """
        Save the audio and image results to the precompute search directory.

        Args:
            embedding_source: Embedding source to save.
            possible_example_id: Id of the possible example.
        """
        # First, load the audio and save it to the precompute search directory
        audio_output_filepath = get_possible_example_audio_path(
            possible_example_id, self.precompute_search_dir
        )

        audio_slice = audio_utils.load_audio_window_soundfile(
            f"{self.base_path}/{embedding_source.source_id}",
            offset_s=embedding_source.offsets[0],
            window_size_s=5.0,  # TODO: make this a parameter, not hard coded (although probably fine)
            sample_rate=self.sample_rate,
        )

        with tempfile.NamedTemporaryFile() as tmp_file:
            wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio_slice))
            epath.Path(tmp_file.name).copy(audio_output_filepath)

        # Second, get the spectrogram and save it to the precompute search directory
        image_output_filepath = get_possible_example_image_path(
            possible_example_id, self.precompute_search_dir
        )

        melspec_layer = embedding_display.get_melspec_layer(self.sample_rate)
        if audio_slice.shape[0] < self.sample_rate / 100 + 1:
            # Center pad if audio is too short.
            zs = np.zeros([self.sample_rate // 10], dtype=audio_slice.dtype)
            audio_slice = np.concatenate([zs, audio_slice, zs], axis=0)
        melspec = melspec_layer(audio_slice).T  # type: ignore

        librosa_display.specshow(
            melspec,
            sr=self.sample_rate,
            y_axis="mel",
            x_axis="time",
            hop_length=self.sample_rate // 100,
            cmap="Greys",
        )
        # for some reason, librosa has decided to make the y-axis inverted...
        # so we need to invert it back
        plt.gca().invert_yaxis()
        with epath.Path(image_output_filepath).open("wb") as f:
            plt.savefig(f)
        plt.close()
