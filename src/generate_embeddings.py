from etils import epath
from ml_collections import config_dict
import numpy as np
import tensorflow as tf
import tqdm
import os

from chirp import audio_utils
from chirp.inference import embed_lib
from chirp.inference import tf_examples
import pandas as pd
import csv
import re

def make_embed_config(embeddings_path,
                      source_file_patterns,
                      file_id_depth=1):
    
    embeddings_path = epath.Path(embeddings_path)
    
    config = config_dict.ConfigDict()
    config.embed_fn_config = config_dict.ConfigDict()
    config.embed_fn_config.model_config = config_dict.ConfigDict()


    config.source_file_patterns = source_file_patterns
    config.output_dir = embeddings_path.as_posix()


    perch_tfhub_version = 8
    perch_model_path = ''

    config.embed_fn_config.model_key = 'taxonomy_model_tf'
    config.embed_fn_config.model_config.window_size_s = 5.0
    config.embed_fn_config.model_config.hop_size_s = 5.0
    config.embed_fn_config.model_config.sample_rate = 32000
    config.embed_fn_config.model_config.tfhub_version = perch_tfhub_version
    config.embed_fn_config.model_config.model_path = perch_model_path

    # Only write embeddings to reduce size.
    config.embed_fn_config.write_embeddings = True
    config.embed_fn_config.write_logits = False
    config.embed_fn_config.write_separated_audio = False
    config.embed_fn_config.write_raw_audio = False

    # Number of parent directories to include in the filename.
    config.embed_fn_config.file_id_depth = file_id_depth
    
    return config


def setup_model(config):
    # Set up the embedding function, including loading models.
    embed_fn = embed_lib.EmbedFn(**config.embed_fn_config)
    print('\n\nLoading model(s)...')
    embed_fn.setup()

    # Create output directory and write the configuration.
    output_dir = epath.Path(config.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    embed_lib.maybe_write_config(config, output_dir)

    # Create SourceInfos.
    source_infos = embed_lib.create_source_infos(
        config.source_file_patterns,
        num_shards_per_file=config.get('num_shards_per_file', -1),
        shard_len_s=config.get('shard_len_s', -1))
    print(f'Found {len(source_infos)} source infos.')

    print('\n\nTest-run of model...')
    window_size_s = config.embed_fn_config.model_config.window_size_s
    sr = config.embed_fn_config.model_config.sample_rate
    z = np.zeros([int(sr * window_size_s)])
    embed_fn.embedding_model.embed(z)
    print('Setup complete!')
    
    return embed_fn, source_infos


def embed_audio(embed_fn, 
                source_infos, 
                config,
                min_file_size=1_000_000,
                filter_by_size=False):
    
    output_dir = epath.Path(config.output_dir)
    
    embed_fn.min_audio_s = 1.0
    succ, fail = 0, 0

    existing_embedding_ids = embed_lib.get_existing_source_ids(
        output_dir, 'embeddings-*')

    new_source_infos = embed_lib.get_new_source_infos(
        source_infos, existing_embedding_ids, config.embed_fn_config.file_id_depth)

    filtered_source_infos = []

    for s in new_source_infos:
        if filter_by_size:
            size = os.stat(s.filepath).st_size
            if size < min_file_size:
                continue
            filtered_source_infos.append(s)
        else:
            filtered_source_infos.append(s)

    new_source_infos = filtered_source_infos

    print(f'Found {len(new_source_infos)} existing embedding ids.'
        f'Processing {len(new_source_infos)} new source infos. ')

    try:
        audio_loader = lambda fp, offset: audio_utils.load_audio_window(
            fp, offset, sample_rate=config.embed_fn_config.model_config.sample_rate,
            window_size_s=config.get('shard_len_s', -1.0))
        audio_iterator = audio_utils.multi_load_audio_window(
            filepaths=[s.filepath for s in new_source_infos],
            offsets=[s.shard_num * s.shard_len_s for s in new_source_infos],
            audio_loader=audio_loader,
        )
        with tf_examples.EmbeddingsTFRecordMultiWriter(
            output_dir=output_dir, num_files=config.get('tf_record_shards', 1)) as file_writer:
            for source_info, audio in tqdm.tqdm(
                zip(new_source_infos, audio_iterator), total=len(new_source_infos)):
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
        del(audio_iterator)
        print(f'\n\nSuccessfully processed {succ} source_infos, failed {fail} times.')

    fns = [fn for fn in output_dir.glob('embeddings-*')]
    ds = tf.data.TFRecordDataset(fns)
    parser = tf_examples.get_example_parser()
    ds = ds.map(parser)
    for ex in ds.as_numpy_iterator():
        print(ex['filename'])
        print(ex['embedding'].shape, flush=True)
        break