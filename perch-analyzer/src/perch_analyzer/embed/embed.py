from perch_analyzer.config import config
from perch_hoplite.db.sqlite_usearch_impl import SQLiteUSearchDB
from perch_hoplite.agile import embed, source_info
from perch_hoplite.zoo import model_configs
import logging

logger = logging.getLogger(__name__)


def embed_audio(
    config: config.Config,
    hoplite_db: SQLiteUSearchDB,
    ARU_base_path: str,
    ARU_file_glob: str,
):
    audio_glob = source_info.AudioSourceConfig(
        dataset_name=config.project_name,
        base_path=ARU_base_path,
        file_glob=ARU_file_glob,
    )
    logging.debug(f"audio_glob: {audio_glob}")

    preset_info = model_configs.get_preset_model_config(config.embedding_model)
    logging.debug(f"preset_info: {preset_info}")

    db_model_config = embed.ModelConfig(
        model_key=preset_info.model_key,
        embedding_dim=preset_info.embedding_dim,
        model_config=preset_info.model_config,
    )
    logging.debug(f"model_config: {db_model_config}")

    worker = embed.EmbedWorker(
        audio_sources=source_info.AudioSources((audio_glob,)),
        db=hoplite_db,
        model_config=db_model_config,
    )

    worker.process_all()
