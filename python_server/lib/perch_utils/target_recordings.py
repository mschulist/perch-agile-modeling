import time
from typing import Any, Sequence
from etils import epath
import numpy as np
import requests

from python_server.lib.db.db import AccountsDB
from python_server.lib.models import TargetRecording
import tempfile
from scipy.io import wavfile
from chirp import audio_utils

from chirp.taxonomy import namespace_db

TARGET_RECORDINGS_PATH = epath.Path("data/target_recordings")


def get_target_recording_path(target_recording_id: int) -> epath.Path:
    """
    Get the path to the target recording with the given id.
    """
    return TARGET_RECORDINGS_PATH / f"{target_recording_id}.wav"


class GatherTargetRecordings:
    def __init__(
        self,
        db: AccountsDB,
        n: int,
        target_recordings_path: epath.Path,
        sample_rate: int = 32000,
        window_s: float = 5.0,
        max_len_s: float = 60.0,
    ):
        """
        Initialize the GatherTargetRecordings class.

        This class will is designed to gather target recordings for the Perch model.

        The db is used to get the list of previously gathered target recordings as well as
        insert the new target recordings gathered into the db.

        Args:
            db: AccountsDB instance
            n: Number of target recordings to gather.
            target_recordings_path: Path to the target recordings.
            sample_rate: Sample rate of the target recordings.
            window_s: Window size in seconds.
            max_len_s: Maximum length of the target recordings in seconds.
        """
        self.db = db
        self.n = n
        self.target_recordings_path = target_recordings_path
        self.sample_rate = sample_rate
        self.window_s = window_s
        self.max_len_s = max_len_s

    def get_existing_target_recordings(self) -> Sequence[TargetRecording]:
        """
        Get the list of previously gathered target recordings from the db.
        """
        return self.db.get_target_recordings()

    def convert_xc_sci_to_ebird_6_code(self, xc_scientific_name: str) -> str:
        """
        Convert the scientific name to an ebird 6 code. To be used after gathering the target recordings.
        """
        name_db = namespace_db.load_db()

        mapping = name_db.mappings.get("xenocanto_11_2_to_ebird2022_species", None)
        if mapping is None:
            raise ValueError("Mapping not found. This error should never happen:/")

        ebird_6_code = mapping.mapped_pairs.get(xc_scientific_name, None)
        if ebird_6_code is None:
            raise ValueError(f"Mapping not found for {xc_scientific_name}.")
        return ebird_6_code

    def convert_ebird_6_code_to_xc_sci_name(self, ebird_6_code: str) -> str:
        """
        Convert the ebird 6 code to the scientific name. To be used after gathering the target recordings.
        """
        name_db = namespace_db.load_db()

        mapping = name_db.mappings.get("xenocanto_11_2_to_ebird2022_species", None)
        if mapping is None:
            raise ValueError("Mapping not found. This error should never happen:/")

        reversed_mapping = {v: k for k, v in mapping.mapped_pairs.items()}

        xc_sci_name = reversed_mapping.get(ebird_6_code, None)
        if xc_sci_name is None:
            raise ValueError(f"Mapping not found for {ebird_6_code}.")
        return xc_sci_name

    def get_xc_ids(self, scientific_name: str, voc_type: str) -> Sequence[str]:
        """
        Queries the xeno-canto API and returns a list of xeno-canto ids for the given species and vocalization type.

        Args:
            scientific_name: Scientific name of the species.
            voc_type: Vocalization type of the species.

        Returns:
            List of xeno-canto ids.
        """

        url = f'https://www.xeno-canto.org/api/2/recordings?query={scientific_name} type:"{voc_type}" len:1-{self.max_len_s}'

        status_code = 0
        response = None
        while status_code != 200:
            response = requests.get(url)
            status_code = response.status_code
            time.sleep(1)

        if not response:
            raise ValueError(
                f"Failed to get response from xeno-canto API for {scientific_name} {voc_type}."
            )
        response_json = response.json()
        return self.filter_xc_response(response_json)

    def filter_xc_response(self, response_json: dict[str, Any]) -> Sequence[str]:
        """
        Filters the xeno-canto API response and returns a list of xeno-canto ids.

        Args:
            response_json: JSON response from the xeno-canto API.

        Returns:
            List of xeno-canto ids.
        """
        xc_ids: list[str] = []
        for recording in response_json["recordings"]:
            xc_ids.append(recording["id"])
        return xc_ids

    def download_target_recording(self, xc_id: str, call_type: str, species_code: str) -> None:
        """
        Given a xeno-canto id and relevant metadata, download the target recording and
        add it to the target_recordings database (so that we know we've already downloaded it).

        Args:
            xc_id: Xeno-canto id of the recording.
            call_type: Vocalization type of the recording.
            species_code: Species code of the recording.
        """
        try:
            audio = audio_utils.load_xc_audio(xc_id, sample_rate=self.sample_rate)
            peaks = audio_utils.slice_peaked_audio(
                audio=audio,
                sample_rate_hz=self.sample_rate,
                interval_length_s=self.window_s,
                max_intervals=1,
            )
            for peak in peaks:
                audio_slice = audio[peak[0] : peak[1]]
                timestamp_s: int = peak[0] // self.sample_rate
                target_recording = TargetRecording(
                    xc_id=xc_id, species=species_code, call_type=call_type, timestamp_s=timestamp_s
                )
                target_recording_id = self.db.add_target_recording(target_recording)
                if target_recording_id is None:
                    raise ValueError("Failed to add target recording to the database.")

                output_filepath = get_target_recording_path(target_recording_id)
                with tempfile.NamedTemporaryFile() as tmp_file:
                    wavfile.write(tmp_file.name, self.sample_rate, np.float32(audio_slice))
                    epath.Path(tmp_file.name).copy(output_filepath)
        except Exception as e:
            print(f"Error processing xc id {xc_id}: {e}")
            print("This error is likely due to the xeno-canto recording being unavailable.")
