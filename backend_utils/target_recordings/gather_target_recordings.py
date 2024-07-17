from etils import epath
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
import argparse
import logging
from chirp.taxonomy import namespace_db
import requests
from time import sleep
import tempfile
from scipy.io import wavfile
from chirp import audio_utils
import numpy as np


class GatherTargetRecordings(beam.DoFn):
    def __init__(
        self,
        n: int,
        target_path: epath.PathLike,
        types: list[str] = ["song", "call"],
        sample_rate: int = 32000,
        window_s: int = 5,
        max_len: int = 60,
    ):
        """
        Initialize the GatherTargetRecordings class.

        Args:
            n (int): Number of target recordings to gather for each species.
            target_path (epath.Path): Path to the target directory.
            types (list[str], optional): List of recording types to consider. Defaults to ["song", "call"].
            sample_rate (int, optional): Sample rate of the recordings. Defaults to 32000.
            window_s (int, optional): Window size in samples. Defaults to 5.
            max_len (int, optional): Maximum length of the recordings in seconds. Defaults to 60.
        """

        self.n = n
        self.target_path = epath.Path(target_path)
        self.target_path.mkdir(exist_ok=True, parents=True)
        self.sample_rate = sample_rate
        self.window_s = window_s
        self.types = types
        self.max_len = max_len
        self.existing_xc_ids = self.get_existing_targets()

    def get_existing_targets(self) -> list[str]:
        """
        Retrieves the existing target IDs from the target path.

        Returns:
            A list of existing target IDs.
        """
        recordings = [f.stem for f in self.target_path.glob("*/*.wav")]
        existing_ids = [f.split("_")[0].replace("xc", "") for f in recordings]
        return existing_ids

    def convert_code_to_xc_scientific_name(self, species_code: str) -> str:
        """
        Converts the species code to the scientific name used in Xeno-Canto.

        Codes are the 6-character codes used in the eBird taxonomy database.

        Args:
            species_code (str): The species code.

        Returns:
            str: The scientific name.
        """

        db = namespace_db.load_db()
        mapping = db.mappings["xenocanto_11_2_to_ebird2022_species"]
        # We need to reverse this mapping because we need eBird code -> XC scientific name
        # XC uses a different checklist than eBird
        r_mapping = {v: k for k, v in mapping.mapped_pairs.items()}
        sci_name = r_mapping.get(species_code, None)
        if sci_name is None:
            logging.warning(f"Could not find scientific name for {species_code}")
        return sci_name

    def filter_xc_response(self, response: dict) -> list[str]:
        """
        Filters the XC response to obtain a list of XC IDs.

        Args:
            response (dict): The XC response containing the recordings.

        Returns:
            list[str]: A list of XC IDs.

        """
        xc_ids: list[str] = []
        species = "no recordings found -> no species found"
        if len(response["recordings"]) > 0:
            species = response["recordings"][0]["en"]
        logging.info(f"Found {len(response['recordings'])} recordings for {species}")
        for recording in response["recordings"]:
            if len(xc_ids) >= self.n:
                break
            if recording["id"] in self.existing_xc_ids:
                logging.info(f"Skipping existing target {recording['id']}")
                continue
            xc_ids.append(f'xc{recording["id"]}')
        return xc_ids

    def get_xc_ids(self, scientific_name: str, voc_type: str) -> list[str]:
        """
        Retrieves the Xeno-Canto IDs for recordings matching the given scientific name and vocalization type.

        Args:
            scientific_name (str): The scientific name of the bird species.
            voc_type (str): The type of vocalization.

        Returns:
            list[str]: A list of Xeno-Canto IDs for the matching recordings.
        """

        url = f'https://www.xeno-canto.org/api/2/recordings?query={scientific_name} type:"{voc_type}" len:1-{self.max_len}'

        status_code = 0
        while status_code != 200:
            response = requests.get(url)
            status_code = response.status_code
            if response.status_code != 200:
                logging.info(
                    f"Failed to get response from {url} (probably rate limited), trying again..."
                )
                sleep(0.25)

        ids = self.filter_xc_response(response.json())
        return ids

    def download_target_recording(self, xc_id: str, voc_type: str, species_code: str):
        """
        Downloads the target recording identified by the given parameters.

        We currently only download the first peak of the recording, as multiple peaks
        will result in very similar searches when we use these target recordings to
        search the ARU recordings.

        Args:
            xc_id (str): The ID of the target recording in the Xeno-canto.
            voc_type (str): The type of vocalization.
            species_code (str): The code representing the species.

        Returns:
            None
        """

        try:
            audio = audio_utils.load_xc_audio(xc_id, sample_rate=self.sample_rate)
            peaks = audio_utils.slice_peaked_audio(
                audio=audio,
                sample_rate_hz=self.sample_rate,
                interval_length_s=self.window_s,
                max_intervals=1,
            )
            for i, peak in enumerate(peaks):
                audio_slice = audio[peak[0] : peak[1]]
                label_path = f"{species_code}_{voc_type}"
                output_path = self.target_path / label_path
                output_path.mkdir(parents=True, exist_ok=True)
                filename = f"{xc_id}_{i}.wav"
                output_filepath = output_path / filename
                with tempfile.NamedTemporaryFile() as tmp_file:
                    wavfile.write(
                        tmp_file.name, self.sample_rate, np.float32(audio_slice)
                    )
                    epath.Path(tmp_file.name).copy(output_filepath)
        except Exception as e:
            logging.info(f"Error processing xc id {xc_id}: {e}")
            logging.info(
                "This error is likely due to the xeno-canto recordiing being unavailable."
            )

    def process_targets(self, species_code: str):
        """
        Processes the target recordings for the given species codes.

        Returns:
            None
        """
        scientific_name = self.convert_code_to_xc_scientific_name(species_code)
        logging.info(f"Getting recordings for {species_code}: {scientific_name}")
        for voc_type in self.types:
            xc_ids = self.get_xc_ids(scientific_name, voc_type)
            for xc_id in xc_ids:
                self.download_target_recording(xc_id, voc_type, species_code)

    def process(self, species_code: str):
        self.process_targets(species_code=species_code)
        return None


def run_pipeline(
    species_codes: list[str],
    species_codes_file: epath.PathLike,
    n: int,
    target_path: epath.PathLike,
    pipeline_args: list[str] = None,
    types: list[str] = ["song", "call"],
    sample_rate: int = 32000,
    window_s: int = 5,
    max_len: int = 60,
):
    """
    Runs the Apache Beam pipeline to gather target recordings for the given species codes.

    Args:
        species_codes (list[str]): List of species codes.
        species_codes_file (epath.Path, optional): Path to the species codes file. Defaults to None.
        n (int): Number of target recordings to gather for each species.
        target_path (epath.Path): Path to the target directory.
        types (list[str], optional): List of recording types to consider. Defaults to ["song", "call"].
        sample_rate (int, optional): Sample rate of the recordings. Defaults to 32000.
        window_s (int, optional): Window size in samples. Defaults to 5.
        max_len (int, optional): Maximum length of the recordings in seconds. Defaults to 60.

    Returns:
        None
    """

    if species_codes_file:
        with epath.Path(species_codes_file).open("r") as f:
            species_codes_from_file = f.read().splitlines()
        species_codes += species_codes_from_file

    options = PipelineOptions(pipeline_args)
    pipeline = beam.Pipeline(options=options)

    _ = (
        pipeline
        | "CreateTargetSpecies" >> beam.Create(species_codes)
        | "Gather Target Recordings"
        >> beam.ParDo(
            GatherTargetRecordings(
                n=n,
                target_path=target_path,
                types=types,
                sample_rate=sample_rate,
                window_s=window_s,
                max_len=max_len,
            )
        )
    )
    pipeline.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--species_codes", nargs="+", help="List of species codes.", default=[]
    )
    parser.add_argument(
        "--species_codes_file",
        type=epath.Path,
        help="Path to the species codes",
        default=None,
    )
    parser.add_argument(
        "--n", type=int, help="Number of target recordings to gather for each species."
    )
    parser.add_argument(
        "--target_path", type=epath.Path, help="Path to the target directory."
    )
    parser.add_argument(
        "--types",
        nargs="+",
        help="List of recording types to consider.",
        default=["song", "call"],
    )
    parser.add_argument(
        "--sample_rate", type=int, help="Sample rate of the recordings.", default=32000
    )
    parser.add_argument(
        "--window_s", type=int, help="Window size in samples.", default=5
    )
    parser.add_argument(
        "--max_len",
        type=int,
        help="Maximum length of the recordings in seconds.",
        default=60,
    )
    args, pipeline_args = parser.parse_known_args()

    run_pipeline(
        species_codes=args.species_codes,
        species_codes_file=args.species_codes_file,
        n=args.n,
        target_path=args.target_path,
        types=args.types,
        sample_rate=args.sample_rate,
        window_s=args.window_s,
        max_len=args.max_len,
        pipeline_args=pipeline_args,
    )
