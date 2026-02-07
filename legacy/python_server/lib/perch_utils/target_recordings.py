import time
from typing import Any, Optional, Sequence
from etils import epath
import numpy as np
import requests

from python_server.lib.db.db import AccountsDB
from python_server.lib.models import TargetRecording
import tempfile
from scipy.io import wavfile
import perch_hoplite.audio_io as audio_utils
from .audio_utils import slice_peaked_audio

import os

from perch_hoplite.taxonomy import namespace_db

# TARGET_RECORDINGS_PATH = epath.Path("data/target_recordings")


def get_target_recording_path(
    target_recording_id: int, target_path: epath.Path
) -> epath.Path:
    """
    Get the path to the target recording with the given id.
    """
    return target_path / f"{target_recording_id}.wav"


class GatherTargetRecordings:
    def __init__(
        self,
        db: AccountsDB,
        target_path: epath.Path | str,
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
            target_path: Path to the target recordings.
            sample_rate: Sample rate of the target recordings.
            window_s: Window size in seconds.
            max_len_s: Maximum length of the target recordings in seconds.
        """
        self.db = db
        self.target_path = epath.Path(target_path)
        self.sample_rate = sample_rate
        self.window_s = window_s
        self.max_len_s = max_len_s

    def get_existing_target_recordings(
        self, species_code: str, call_type: str, project_id: Optional[int]
    ) -> Sequence[TargetRecording]:
        """
        Get the list of previously gathered target recordings from the db.

        Args:
            species_code: Species code of the target recordings.
            call_type: Call type of the target recordings.
            project_id: Project id to determine whether the target recording has been used.
        """
        return self.db.get_target_recordings(species_code, call_type, project_id)

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

    def get_xc_ids(self, scientific_name: str, call_type: str) -> Sequence[str]:
        """
        Queries the xeno-canto API and returns a list of xeno-canto ids for the given species and vocalization type.

        Args:
            scientific_name: Scientific name of the species.
            call_type: Vocalization type of the species.

        Returns:
            List of xeno-canto ids.
        """

        url = f'https://www.xeno-canto.org/api/2/recordings?query={scientific_name} type:"{call_type}" len:1-{self.max_len_s}'

        if "PYTEST_CURRENT_TEST" in os.environ:
            if scientific_name == "turdus migratorius":
                return ["168640", "364119"]
            elif scientific_name == "piranga ludoviciana":
                return ["1252", "324863"]

        status_code = 0
        response = None
        while status_code != 200:
            response = requests.get(url)
            status_code = response.status_code
            if status_code == 200:
                break
            time.sleep(0.25)

        if not response:
            raise ValueError(
                f"Failed to get response from xeno-canto API for {scientific_name}: {call_type}."
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

    def download_target_recording(
        self, xc_id: str, call_type: str, species_code: str
    ) -> None:
        """
        Given a xeno-canto id and relevant metadata, download the target recording and
        add it to the target_recordings database (so that we know we've already downloaded it).

        Args:
            xc_id: Xeno-canto id of the recording.
            call_type: Vocalization type of the recording.
            species_code: Species code of the recording.
        """
        try:
            audio = audio_utils.load_xc_audio(
                f"xc{xc_id}", sample_rate=self.sample_rate
            )
            peaks = slice_peaked_audio(
                audio=audio,
                sample_rate_hz=self.sample_rate,
                interval_length_s=self.window_s,
                max_intervals=1,
            )
            for peak in peaks:
                audio_slice = audio[peak[0] : peak[1]]
                timestamp_s: int = peak[0] // self.sample_rate
                target_recording = TargetRecording(
                    xc_id=xc_id,
                    species=species_code,
                    call_type=call_type,
                    timestamp_s=timestamp_s,
                )
                target_recording_id = self.db.add_target_recording(target_recording)
                if target_recording_id is None:
                    raise ValueError("Failed to add target recording to the database.")

                output_filepath = get_target_recording_path(
                    target_recording_id, self.target_path
                )
                with tempfile.NamedTemporaryFile() as tmp_file:
                    wavfile.write(
                        tmp_file.name, self.sample_rate, np.float32(audio_slice)
                    )
                    epath.Path(tmp_file.name).copy(output_filepath)
        except Exception as e:
            print(f"Error processing xc id {xc_id}: {e}")
            print(
                "This error is likely due to the xeno-canto recording being unavailable."
            )

    def process_req_for_targets(
        self,
        species_codes: Sequence[str],
        call_types: Sequence[str],
        num_targets: int,
        project_id: Optional[int],
    ) -> None:
        """
        Process the request for target recordings. Main method for this class.

        The request will take in the species codes and vocalization types and gather the target recordings.

        For example, if someone wants 5 recordings of "song" and "call" for each of their
        species of interest, calling this function will make sure that we have 5 recordings of each
        species and vocalization type in the database. So, calling this function 2 times with the same
        arguments should result in nothing happening the second time (assuming the db does its job).

        Args:
            species_codes: List of species codes.
            call_types: List of vocalization types.
            num_targets: Number of target recordings to gather.
            project_id: Project id to determine whether the target recording has been used.
        """
        for species in species_codes:
            for call in call_types:
                existing_target_recordings = self.get_existing_target_recordings(
                    species, call, project_id
                )
                if len(existing_target_recordings) >= num_targets:
                    continue
                xc_sci_name = self.convert_ebird_6_code_to_xc_sci_name(species)
                xc_ids = self.get_xc_ids(xc_sci_name, call)

                # Make sure that we don't download the same recording twice.
                # all existing target recordings includes from all projects,
                # whereas existing_target_recordings excludes targets that have already been used by the project.
                all_existing_targets = self.get_existing_target_recordings(
                    species, call, project_id=None
                )
                existing_xc_ids = {rec.xc_id for rec in all_existing_targets}
                new_xc_ids = [xc_id for xc_id in xc_ids if xc_id not in existing_xc_ids]

                total_existing = len(existing_target_recordings)

                while total_existing < num_targets:
                    for xc_id in new_xc_ids:
                        if total_existing >= num_targets:
                            break
                        self.download_target_recording(xc_id, call, species)
                        total_existing += 1
                    if total_existing < num_targets:
                        print(f"Ran out of xc_ids for {species}: {call}.")
                        break
