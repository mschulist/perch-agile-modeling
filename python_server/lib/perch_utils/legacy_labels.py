import tempfile
from python_server.lib.db.db import AccountsDB
from python_server.lib.models import PossibleExample
from python_server.lib.perch_utils.search import (
    get_possible_example_audio_path,
    get_possible_example_image_path,
)
from python_server.lib.perch_utils.usearch_hoplite import SQLiteUsearchDBExt
from perch_hoplite.db import interface
from etils import epath
import numpy as np

from librosa import display as librosa_display
import matplotlib.pyplot as plt
from perch_hoplite.agile import embedding_display
from scipy.io import wavfile
from perch_hoplite import audio_io as audio_utils
from tqdm import tqdm


class LegacyLabels:
    def __init__(
        self,
        db: AccountsDB,
        hoplite_db: SQLiteUsearchDBExt,
        label_dir: str | epath.Path,
        project_id: int,
        annotator: str,
        precompute_search_dir: str | epath.Path,
        sample_rate: int = 32000,
    ):
        self.db = db
        self.hoplite_db = hoplite_db
        self.label_dir = epath.Path(label_dir)
        self.project_id = project_id
        self.annotator = annotator
        self.precompute_search_dir = epath.Path(precompute_search_dir)
        self.sample_rate = sample_rate

    def add_labels_to_new_db(self):
        """
        Given the directory in the "folders of folders" format, add the labels to the new database.
        """
        labels = self.label_dir.glob("*")
        for label in tqdm(labels):
            label_name = label.name
            for file in label.glob("*.wav"):
                filename, offset_s = file.name.split("___")
                offset_s = offset_s.split(".")[0]
                # TODO: this is a temp hack to get the correct filename...
                year = file.name.split("_")[1][0:4]
                filename = f"{year}/{filename}.wav"
                embed_id = self.get_embedding_id_from_filename_and_offset(
                    filename, int(offset_s)
                )
                if embed_id is None:
                    print(f"Embedding not found for {filename} at {offset_s}")
                    continue
                embed_id = int.from_bytes(embed_id, "little")  # type: ignore

                # This will never label 2 things with the same embedding id, which is
                # probably a bug, but fine for now.
                if (
                    self.db.get_possible_example_by_embed_id(embed_id, self.project_id)
                    is not None
                ):
                    print(f"Embedding {embed_id} already in the database.")
                    continue
                self.add_labeled_example_to_db(
                    file, filename, int(offset_s), label_name, embed_id
                )
                self.hoplite_db.commit()

    def get_embedding_id_from_filename_and_offset(self, filename: str, offset_s: int):
        """
        Given a filename and an offset in seconds, return the embedding id.
        """
        ids = self.hoplite_db.get_embeddings_by_source(
            str(self.project_id), filename, np.array([offset_s])
        )
        if len(ids) == 0:
            return None
        return ids[0]

    def add_labeled_example_to_db(
        self,
        file: epath.Path,
        filename: str,
        offset_s: int,
        label: str,
        embedding_id: int,
    ):
        """
        Add a labeled example to the accounts database. This requires us to call
        the `add_possible_example` method of the accounts db. We will also need to
        finish the possible example because we are not actually planning on annotating
        it again.

        After adding the example to the db, we need to load the audio recording from the file,
        create the spectrogram and save it to the precompute search directory.
        """
        # TODO: this is a temp hack to get the correct filename...
        possible_example = PossibleExample(
            project_id=self.project_id,
            score=-100,  # This is a placeholder value...
            timestamp_s=offset_s,
            filename=filename,
            embedding_id=embedding_id,
        )
        self.db.add_possible_example(possible_example)

        # we need to get the example from the db to get the id
        possible_example = self.db.get_possible_example_by_embed_id(
            embedding_id, self.project_id
        )
        if possible_example is None:
            raise ValueError("Failed to get possible example from the database.")
        if possible_example.id is None:
            raise ValueError(
                "Failed to get possible example from the database. Must have an ID."
            )
        self.db.finish_possible_example(possible_example)

        label_obj = interface.Label(
            embedding_id=embedding_id,
            label=label,
            type=interface.LabelType.POSITIVE,
            provenance=self.annotator,
        )

        self.hoplite_db.insert_label(label_obj)
        self.flush_labeled_example_to_disk(file, possible_example.id)

    def flush_labeled_example_to_disk(self, file: epath.Path, possible_example_id: int):
        """
        Given the file (from the legacy folders of folders structure) and the possible example id,
        (from the annotations db), save the audio and image results to the precompute search directory.
        """
        audio_output_filepath = get_possible_example_audio_path(
            possible_example_id, self.precompute_search_dir
        )

        audio_slice = audio_utils.load_audio_window_soundfile(
            str(file),
            offset_s=0,
            window_size_s=5.0,
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
        with epath.Path(image_output_filepath).open("wb") as f:
            plt.savefig(f)
        plt.close()
