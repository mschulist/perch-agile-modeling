from chirp import audio_utils
from chirp.inference.search import search
from chirp.inference.search import display
from chirp.inference.search import bootstrap
from scipy.io import wavfile
import os
from tqdm import tqdm
import numpy as np
import requests
import pandas as pd
from etils import epath
from typing import List

from IPython.display import clear_output

# Load the eBird taxonomy data
ebird_taxon = pd.read_csv('./taxonomy/ebird_taxonomy_v2022.csv')

def get_xc_ids(scientific_name: str, n: int, type: str) -> List[str]:
    endpoint = f'https://xeno-canto.org/api/2/recordings?query={scientific_name} type:"{type}"'
    r = requests.get(endpoint).json()
    ids: List[str] = [f'xc{recording["id"]}' for i, recording in enumerate(r['recordings']) if i < n]
    return ids

def get_target_recordings_species(
    species_code: str, 
    types: List[str], 
    n: int, 
    target_path: epath.Path, 
    sample_rate: int, 
    window_s: int):

    # get the current number of recordings for the given species
    n_recordings = {}
    for type in types:
        path = target_path / epath.Path(f'{species_code}_{type}')
        if not os.path.exists(path):
            n_recordings[type] = n
            path.mkdir(parents=True, exist_ok=True)
        n_files = len(os.listdir(path))
        print(f'existing recordings: {n_files}')
        n_recordings[type] = n_files + n
    
    scientific_name = ebird_taxon[ebird_taxon['SPECIES_CODE'] == species_code]['SCI_NAME'].values[0]
    print(f'Getting recordings for {species_code}: {scientific_name}')

    xc_ids = {type: get_xc_ids(scientific_name, n_recordings[type], type) for type in types}

    existing_recordings = set(
        file.split('_')[0] for root, dirs, files in os.walk(target_path, topdown=False) for file in files if file.endswith('.wav') and file.startswith('xc'))

    for type in types:  # Iterate through each type of vocalization
        for id in xc_ids[type]:  # For each type, go through each xc recording
            if id in existing_recordings:
                print(f'xc recording {id} already exists, skipping')
                continue
            try:
                audio = audio_utils.load_xc_audio(id, sample_rate=sample_rate)
                peaks = audio_utils.slice_peaked_audio(audio, sample_rate_hz=sample_rate, interval_length_s=window_s)
                for i, peak in enumerate(peaks):
                    if i == 0:
                        audio_slice = audio[peak[0]:peak[1]]
                        label_path = f'{species_code}_{type}'
                        output_path = epath.Path(target_path) / label_path
                        output_path.mkdir(parents=True, exist_ok=True)
                        filename = f"{id}_{i}.wav"
                        output_filepath = output_path / filename
                        with output_filepath.open('wb') as f:
                            wavfile.write(f, sample_rate, np.float32(audio_slice))
            except Exception as e:
                print(f'Error processing xc id {id}: {e}')

def get_target_recordings(
    species_code_list: List[str],
    types: List[str], 
    n: int, target_path: epath.Path, 
    sample_rate: int, window_s: int):
    
    for species_code in species_code_list:
        get_target_recordings_species(species_code, types, n, target_path, sample_rate, window_s)


def search_single_recording(
    recording_path: epath.Path|str, 
    labeled_path: epath.Path|str,
    species_code: str, 
    types: List[str],
    target_score: float|None, 
    sample_rate, 
    project_state, 
    bootstrap_config):
    
    audio = audio_utils.load_audio_file(recording_path, sample_rate)
    outputs = project_state.embedding_model.embed(audio)
    query = outputs.pooled_embeddings('first', 'first')
    
    
    top_k = 20
    metric = 'mip'
    random_sample = False
    ds = project_state.create_embeddings_dataset(shuffle_files=True)
    results, all_scores = search.search_embeddings_parallel(
        ds, query,
        hop_size_s=bootstrap_config.embedding_hop_size_s,
        top_k=top_k, target_score=target_score, score_fn=metric,
        random_sample=random_sample)

    samples_per_page = 8
    page_state = display.PageState(
        np.ceil(len(results.search_results) / samples_per_page))

    # get labels
    labels = ['unknown']
    for type in types:
        labels.append(f'{species_code}_{type}')

    display.display_paged_results(
        results, page_state, samples_per_page,
        project_state=project_state,
        embedding_sample_rate=project_state.embedding_model.sample_rate,
        exclusive_labels=False,
        checkbox_labels=labels,
        max_workers=5,
    )

    # write to file to say that we have looked at this recording_path already
    with (labeled_path / epath.Path('finished_targets.csv')).open('a') as f:
        f.write(f'{recording_path}\n')
    
    return results

def search_recordings(
    target_path: epath.Path, 
    labeled_path: epath.Path,
    working_dir: str,
    target_score: float|None,
    sample_rate, 
    project_state,
    bootstrap_config):
    
    if not labeled_path.exists():
        labeled_path.mkdir(parents=True, exist_ok=True)

    # get list of species and types
    dirs = [f.path for f in os.scandir(target_path) if f.is_dir()]
    dirs = [d for d in dirs if not d.split('/')[-1].startswith('.')]

    types = []
    for dir in dirs:
        _, type = dir.split('/')[-1].split('_')
        if type not in types:
            types.append(type)

    # get list of target_recordings already searched on
    finished_targets_path = labeled_path / epath.Path('finished_targets.csv')
    if not finished_targets_path.exists():
        with finished_targets_path.open('a') as f:
            f.write('finished\n')
    already_labeled = set(pd.read_csv(
        labeled_path / epath.Path('finished_targets.csv'), 
        header=None).iloc[:,0].to_list())


    for dir in dirs:
        species = dir.split('/')[-1].split('_')[-2]
        for recording in os.listdir(dir):
            recording_path = epath.Path(working_dir) / dir / epath.Path(recording)
            if recording.startswith('.') or str(recording_path) in already_labeled:
                continue
            clear_output(wait=True)
            results = search_single_recording(recording_path=recording_path,
                                    labeled_path=labeled_path,
                                    species_code=species,
                                    types=types,
                                    target_score=target_score,
                                    sample_rate=sample_rate,
                                    project_state=project_state, 
                                    bootstrap_config=bootstrap_config)
            return results


def get_missing_species(
    labeled_path: epath.Path,
    bird_list: List[str],
    types: List[str],
    n_recordings: int):

    if bird_list is None:
        bird_list_types = []
    else:
        bird_list_types = [f'{bird}_{type}' for bird in bird_list for type in types]

    dirs = [f.path for f in os.scandir(labeled_path) if f.is_dir()]
    species_type = [dir.split('/')[-1] for dir in dirs]
    labeled = {}

    for dir in dirs:
        recordings = len(os.listdir(dir))
        s_t = species_type[dirs.index(dir)]
        labeled[s_t] = recordings

    for bird_list_type in bird_list_types:
        if bird_list_type in labeled:
            continue
        labeled[bird_list_type] = 0

    missing = {}
    for label in labeled:
        if labeled[label] < n_recordings:
            missing[label] = labeled[label]
    return missing




    
