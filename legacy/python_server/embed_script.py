from perch_hoplite.agile import embed
from perch_hoplite.agile import source_info
from perch_hoplite.agile import colab_utils

"""
We must run this inside of a conda env with the appropriate cuda libraries. 
I could not get it to work with uv, although I'm sure it might be possible.
We need to export the following before running to get it to work:
LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH"
This is because tensorflow expects the cuda libs to be in the root, not in the 
local env.
"""


def embed_audio(dry_run=True):
    audio_glob = source_info.AudioSourceConfig(
        dataset_name="caples",
        base_path="/home/mschulist/caples_sound/ARU_data_all/",
        file_glob="*/*.wav",
        min_audio_len_s=3,
    )

    db_path = "/home/mschulist/perch-agile-modeling/python_server/data/hoplite_db/hoplite_3.db"
    configs = colab_utils.load_configs(
        audio_sources=source_info.AudioSources((audio_glob,)),
        db_path=db_path,
        model_config_key="perch_v2",
        db_key="sqlite_usearch",
    )

    print(configs)

    db = configs.db_config.load_db()

    print(db.get_metadata(None))

    worker = embed.EmbedWorker(
        audio_sources=configs.audio_sources_config,
        db=db,
        model_config=configs.model_config,
    )

    if not dry_run:
        worker.process_all(target_dataset_name=audio_glob.dataset_name)


if __name__ == "__main__":
    embed_audio(False)
