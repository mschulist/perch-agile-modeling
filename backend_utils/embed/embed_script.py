from etils import epath
from ml_collections import config_dict
import numpy as np
import tensorflow as tf
import tqdm
import logging
from chirp import audio_utils
from chirp.inference import embed_lib
from chirp.inference import tf_examples


def embed_config(
    output_dir: epath.PathLike,
    source_file_patterns: list[str],
    file_id_depth: int = 1,
):
    """
    Generate configuration for embedding.

    Args:
        output_dir (epath.PathLike): The output directory where the embeddings will be saved.
        source_file_patterns (list[str]): List of file patterns to match the source files.

    Returns:
        config_dict.ConfigDict: The configuration object for embedding.

    """
    # Attention-based 5s model.
    config = config_dict.ConfigDict()
    config.embed_fn_config = config_dict.ConfigDict()
    config.embed_fn_config.model_config = config_dict.ConfigDict()

    config.output_dir = str(epath.Path(output_dir))
    config.source_file_patterns = source_file_patterns

    config.shard_len_s = -1
    config.num_shards_per_file = -1
    config.start_shard_idx = 0

    config.embed_fn_config.model_key = "taxonomy_model_tf"
    config.embed_fn_config.model_config.window_size_s = 5.0
    config.embed_fn_config.model_config.hop_size_s = 5.0
    config.embed_fn_config.model_config.sample_rate = 32000
    config.embed_fn_config.model_config.tfhub_version = 8
    config.embed_fn_config.model_config.model_path = ""

    # Only write embeddings to reduce size.
    config.embed_fn_config.write_embeddings = True
    config.embed_fn_config.write_logits = False
    config.embed_fn_config.write_separated_audio = False
    config.embed_fn_config.write_raw_audio = False

    # Number of parent directories to include in the filename.
    config.embed_fn_config.file_id_depth = file_id_depth

    return config


def main(
    output_dir: epath.PathLike,
    source_file_patterns: list[str],
    file_id_depth: int = 1,
):

    config = embed_config(
        output_dir=output_dir,
        source_file_patterns=source_file_patterns,
        file_id_depth=file_id_depth,
    )

    try:
        # Set up the embedding function, including loading models.
        embed_fn = embed_lib.EmbedFn(**config.embed_fn_config)
        logging.info("\n\nLoading model(s)...")
        embed_fn.setup()

        # Create output directory and write the configuration.
        output_dir = epath.Path(config.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        embed_lib.maybe_write_config(config, output_dir)

        # Create SourceInfos.
        source_infos = embed_lib.create_source_infos(
            config.source_file_patterns,
            shard_len_s=config.get("shard_len_s", -1.0),
            num_shards_per_file=config.get("num_shards_per_file", -1),
        )
        logging.info(f"Found {len(source_infos)} source infos.")

        logging.info("\n\nTest-run of model...")
        window_size_s = config.embed_fn_config.model_config.window_size_s
        sr = config.embed_fn_config.model_config.sample_rate
        z = np.zeros([int(sr * window_size_s)])
        embed_fn.embedding_model.embed(z)
        logging.info("Setup complete!")
    except Exception as e:
        logging.info(f"Failed to setup embedding function: {e}")
        return

    # Uses multiple threads to load audio before embedding.
    # This tends to be faster, but can fail if any audio files are corrupt.

    min_file_size = 1_000_000  # 1 MB

    embed_fn.min_audio_s = 1.0
    succ, fail = 0, 0

    existing_embedding_ids = embed_lib.get_existing_source_ids(
        output_dir, "embeddings-*"
    )

    new_source_infos = embed_lib.get_new_source_infos(
        source_infos, existing_embedding_ids, config.embed_fn_config.file_id_depth
    )

    filtered_source_infos = []

    for s in new_source_infos:
        size = epath.Path(s.filepath).stat().length
        if size < min_file_size:
            continue
        filtered_source_infos.append(s)

    new_source_infos = filtered_source_infos

    logging.info(
        f"Found {len(existing_embedding_ids)} existing embedding ids."
        f"Processing {len(new_source_infos)} new source infos."
    )

    try:
        audio_loader = lambda fp, offset: audio_utils.load_audio_window(
            fp,
            offset,
            sample_rate=config.embed_fn_config.model_config.sample_rate,
            window_size_s=config.get("shard_len_s", -1.0),
        )
        audio_iterator = audio_utils.multi_load_audio_window(
            filepaths=[s.filepath for s in new_source_infos],
            offsets=[s.shard_num * s.shard_len_s for s in new_source_infos],
            audio_loader=audio_loader,
        )
        with tf_examples.EmbeddingsTFRecordMultiWriter(
            output_dir=output_dir, num_files=config.get("tf_record_shards", 1)
        ) as file_writer:
            for source_info, audio in tqdm.tqdm(
                zip(new_source_infos, audio_iterator), total=len(new_source_infos)
            ):
                file_id = source_info.file_id(config.embed_fn_config.file_id_depth)
                offset_s = source_info.shard_num * source_info.shard_len_s
                example = embed_fn.audio_to_example(file_id, offset_s, audio)
                if example is None:
                    fail += 1
                    continue
                file_writer.write(example.SerializeToString())
                succ += 1
                file_writer.flush()
    finally:
        del audio_iterator
    logging.info(f"\n\nSuccessfully processed {succ} source_infos, failed {fail} times.")


if __name__ == "__main__":
    import argparse

    logging.info("Available GPUs:")
    logging.info(tf.config.list_physical_devices("GPU"))

    parser = argparse.ArgumentParser()
    parser.add_argument("--output_dir", type=epath.Path, required=True)
    parser.add_argument("--source_file_patterns", type=str, nargs="+", required=True)
    parser.add_argument("--file_id_depth", type=int, default=1)
    args = parser.parse_args()

    main(args.output_dir, args.source_file_patterns, args.file_id_depth)
