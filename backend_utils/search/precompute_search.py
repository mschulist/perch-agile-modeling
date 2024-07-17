import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from etils import epath
import argparse
import numpy as np
from etils import epath
from chirp.inference.search import search
from chirp.inference.search import bootstrap
from chirp import audio_utils
from etils import epath
from chirp.inference.search.display import get_melspec_layer, plot_melspec
import matplotlib.pyplot as plt
from scipy.io import wavfile
import tempfile
import os


class PrecomputeSearchTargets(beam.DoFn):
    def __init__(
        self,
        bootstrap_config: bootstrap.BootstrapConfig,
        precompute_dir: epath.PathLike,
    ):
        """
        Initializes the PrecomputeSearchTargets object.

        Args:
            bootstrap_config (bootstrap.BootstrapConfig): The bootstrap configuration object.
            precompute_dir (epath.PathLike): The path to the precompute directory.
        """

        self.bootstrap_config = bootstrap_config
        self.precompute_dir = epath.Path(precompute_dir)
        self.sample_rate = self.bootstrap_config.model_config["sample_rate"]

    def precompute_example(
        self,
        species: str,
        filepath: epath.Path,
        timestamp_s: float,
        audio: np.ndarray | None = None,
    ):
        """
        Precomputes and saves a mel spectrogram and a WAV file for a given audio segment.

        Args:
            species (str): The species of the audio.
            filepath (epath.Path ): The path to the audio file.
            timestamp_s (float): The starting timestamp of the audio segment.
            audio (np.ndarray | None, optional): The audio data. Defaults to None.

            If you provide an audio, you still must provide a filepath and timestamp_s,
            but the audio will be used instead of loading the audio from the filepath.
        """

        filename = filepath.name
        melspec_path = epath.Path(self.precompute_dir) / epath.Path(
            f"{filename}^_^{timestamp_s}^_^{species}.png"
        )
        wav_path = epath.Path(self.precompute_dir) / epath.Path(
            f"{filename}^_^{timestamp_s}^_^{species}.wav"
        )

        if melspec_path.exists() and wav_path.exists():
            return

        # load audio
        if audio is None:
            start = int(timestamp_s * self.sample_rate)
            end = int((timestamp_s + 5) * self.sample_rate)
            audio = audio_utils.load_audio(filepath, self.sample_rate)[start:end]

        melspec_layer = get_melspec_layer(self.sample_rate)
        if audio.shape[0] < self.sample_rate / 100 + 1:
            # Center pad if audio is too short.
            zs = np.zeros([self.sample_rate // 10], dtype=audio.dtype)
            audio = np.concatenate([zs, audio, zs], axis=0)
        melspec = melspec_layer.apply({}, audio[np.newaxis, :])[0]
        plot_melspec(melspec, sample_rate=self.sample_rate, frame_rate=100)

        # save melspec
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp_file:
            plt.savefig(tmp_file.name)
            epath.Path(tmp_file.name).copy(melspec_path)
            plt.close()

        # save wav
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_file:
            wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio))
            epath.Path(tmp_file.name).copy(wav_path)

    def search_single_recording(
        self,
        recording_path: epath.Path,
        target_score: float | None,
        project_state: bootstrap.BootstrapState,
    ) -> search.TopKSearchResults:
        """
        Searches for a single recording in the embeddings dataset.

        Args:
            recording_path (epath.Path): The path to the recording file.
            target_score (float | None): The target score to filter the search results. If None, all results are returned.
            project_state (BootstrapState): The state of the project.

        Returns:
            results (TopKSearchResults): The search results.
        """

        audio = audio_utils.load_audio_file(recording_path, self.sample_rate)
        outputs = project_state.embedding_model.embed(audio)
        query = outputs.pooled_embeddings("first", "first")

        ds = project_state.create_embeddings_dataset(shuffle_files=True)
        results, _ = search.search_embeddings_parallel(
            embeddings_dataset=ds,
            query_embedding_batch=query,
            hop_size_s=self.bootstrap_config.embedding_hop_size_s,
            top_k=10,
            target_score=target_score,
            score_fn="mip",
        )

        return results

    def precompute_search(
        self,
        search_results: search.TopKSearchResults,
        project_state: bootstrap.BootstrapState,
        species_code: str,
    ) -> None:
        """
        Precomputes the spectrograms and audio files for the search results.

        Args:
            search_results (List[SearchResult]): The search results.
            project_state (BootstrapState): The BootstrapState from the embeddings.
            species_code (str): The species code.
        """

        results_iterator = project_state.search_results_audio_iterator(
            search_results=search_results,
        )

        for result in results_iterator:
            audio = result.audio
            if audio is None:
                continue
            filepath = epath.Path(result.filename)
            timestamp_s = float(result.timestamp_offset)

            self.precompute_example(
                species=species_code,
                filepath=filepath,
                timestamp_s=timestamp_s,
                audio=audio,
            )

    def precompute_search_single_target(
        self,
        recording_path: epath.PathLike,
        target_score: float | None,
        species_code: str,
    ) -> None:
        """
        Precomputes the search results for a single target recording.

        Args:
            recording_path (epath.PathLike): The path to the target recording file. Must be 5 seconds long.
            target_score (float | None): The target score to filter the search results. If None, all results are returned.
            bootstrap_config (BootstrapConfig): The configuration for bootstrapping.
            species_code (str): The species code.
            precompute_dir (epath.Path): The directory to save the precomputed files.
        """

        project_state = bootstrap.BootstrapState(config=self.bootstrap_config)

        search_results = self.search_single_recording(
            recording_path=epath.Path(recording_path),
            target_score=target_score,
            project_state=project_state,
        )

        self.precompute_search(
            search_results=search_results,
            project_state=project_state,
            species_code=species_code,
        )

    def process_target_recording(
        self,
        target_recording_path: epath.PathLike,
    ):
        """
        Process a single target recording. Not for use in Beam.
        Replicates the Beam process method for a single target recording.

        Args:
            target_recording_path (epath.PathLike): The path to the target recording.
        """

        species = os.path.basename(os.path.dirname(target_recording_path)).split("_")[0]
        self.precompute_search_single_target(
            recording_path=target_recording_path,
            target_score=None,
            species_code=species,
        )

    def process(self, target_recording_path: epath.PathLike):
        """
        Process the target recording path. This is the method that is called by Beam.

        Args:
            target_recording_path (epath.PathLike): The path to the target recording.

        Returns:
            Generator: A generator that yields the target recording path.
        """

        species = os.path.basename(os.path.dirname(target_recording_path)).split("_")[0]
        self.precompute_search_single_target(
            recording_path=target_recording_path,
            target_score=None,
            species_code=species,
        )
        yield target_recording_path


def run_pipeline(
    embeddings_path: epath.Path,
    precompute_dir: epath.Path,
    target_recordings_path: epath.Path,
    labeled_outputs_path: epath.Path,
    pipeline_args=None,
):
    options = PipelineOptions(pipeline_args)
    bootstrap_config = bootstrap.BootstrapConfig.load_from_embedding_path(
        embeddings_path=embeddings_path, annotated_path=labeled_outputs_path
    )

    target_recordings_globs = [str(p) for p in target_recordings_path.glob("*/*.wav")]

    with beam.Pipeline(options=options) as p:
        _ = (
            p
            | "CreateRecordingPaths" >> beam.Create(target_recordings_globs)
            | "ProcessRecordings"
            >> beam.ParDo(PrecomputeSearchTargets(bootstrap_config, precompute_dir))
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-ep", "--embeddings_path", type=epath.Path, required=True)
    parser.add_argument("-pd", "--precompute_dir", type=epath.Path, required=True)
    parser.add_argument(
        "-trp", "--target_recordings_path", type=epath.Path, required=True
    )
    parser.add_argument(
        "-lop", "--labeled_outputs_path", type=epath.Path, required=True
    )
    args, pipeline_args = parser.parse_known_args()

    run_pipeline(
        embeddings_path=args.embeddings_path,
        precompute_dir=args.precompute_dir,
        target_recordings_path=args.target_recordings_path,
        labeled_outputs_path=args.labeled_outputs_path,
        pipeline_args=pipeline_args,
    )
