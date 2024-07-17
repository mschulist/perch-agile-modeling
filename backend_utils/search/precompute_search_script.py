from etils import epath
from chirp.inference.search import bootstrap
import argparse
import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from precompute_search import PrecomputeSearchTargets
import logging


"""
Script to precompute mel spectrograms and wav files for all target recordings
"""


def main(
    embeddings_path: epath.Path,
    precompute_dir: epath.Path,
    target_recordings_path: epath.Path,
    labeled_outputs_path: epath.Path,
    max_workers: int = None,
):
    """
    Precomputes search targets for a given set of target recordings.

    Args:
        embeddings_path (epath.Path): The path to the embeddings file.
        precompute_dir (epath.Path): The directory to store the precomputed search targets.
        target_recordings_path (epath.Path): The path to the target recordings.
        labeled_outputs_path (epath.Path): The path to the labeled outputs.
        max_workers (int): The number of workers to use. Defaults to None.
    """

    precompute_dir.mkdir(exist_ok=True, parents=True)
    labeled_outputs_path.mkdir(exist_ok=True, parents=True)

    bootstrap_config = bootstrap.BootstrapConfig.load_from_embedding_path(
        embeddings_path=embeddings_path, annotated_path=labeled_outputs_path
    )

    pst = PrecomputeSearchTargets(
        bootstrap_config=bootstrap_config, precompute_dir=precompute_dir
    )

    target_recordings_globs = list(target_recordings_path.glob("*/*.wav"))

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(pst.process_target_recording, target_recording_path)
            for target_recording_path in target_recordings_globs
        ]

        for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
            try:
                future.result()
            except Exception as e:
                logging.warning(f"Error processing target recording: {e}")


if __name__ == "__main__":
    """
    Example usage:
    python precompute_search_targets_script.py \
        -ep /path/to/embeddings/ \
        -pd /path/to/precompute_dir/ \
        -trp /path/to/target_recordings/ \
        -lop /path/to/labeled_outputs/ 
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("-ep", "--embeddings_path", type=epath.Path, required=True)
    parser.add_argument("-pd", "--precompute_dir", type=epath.Path, required=True)
    parser.add_argument(
        "-trp", "--target_recordings_path", type=epath.Path, required=True
    )
    parser.add_argument(
        "-lop", "--labeled_outputs_path", type=epath.Path, required=True
    )
    parser.add_argument("-mw", "--max_workers", type=int, default=None)
    args = parser.parse_args()

    main(
        embeddings_path=args.embeddings_path,
        precompute_dir=args.precompute_dir,
        target_recordings_path=args.target_recordings_path,
        labeled_outputs_path=args.labeled_outputs_path,
        max_workers=args.max_workers,
    )
