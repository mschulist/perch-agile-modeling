from gather_target_recordings import GatherTargetRecordings
import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed
from etils import epath
import argparse

"""
Script to gather target recordings for a given set of species codes.
"""


def main(
    species_codes: list[str],
    n: int,
    target_path: epath.Path,
    types: list[str] = ["song", "call"],
    species_codes_file: epath.Path = None,
    sample_rate: int = 32000,
    window_s: int = 5,
    max_len: int = 60,
    max_workers: int | None = None,
):
    """
    Gathers target recordings for a given set of species codes.

    Args:
        species_codes (list[str]): List of species codes.
        n (int): Number of target recordings to gather for each species.
        target_path (epath.Path): Path to the target directory.
        types (list[str], optional): List of recording types to consider. Defaults to ["song", "call"].
        species_codes_file (epath.Path, optional): Path to the species codes file. Defaults to None.
        sample_rate (int, optional): Sample rate of the recordings. Defaults to 32000.
        window_s (int, optional): Window size in samples. Defaults to 5.
        max_len (int, optional): Maximum length of the recordings in seconds. Defaults to 60.
        max_workers (int): The number of workers to use. Defaults to None.
    """

    if species_codes_file:
        with species_codes_file.open("r") as f:
            species_codes_from_file = f.read().splitlines()
        species_codes += species_codes_from_file

    target_path.mkdir(exist_ok=True, parents=True)

    gtr = GatherTargetRecordings(
        n=n,
        target_path=target_path,
        types=types,
        sample_rate=sample_rate,
        window_s=window_s,
        max_len=max_len,
    )

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(gtr.process_targets, species_code)
            for species_code in species_codes
        ]

        for future in tqdm.tqdm(as_completed(futures), total=len(futures)):
            try:
                future.result()
            except Exception as e:
                print(f"Error gathering target recordings: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--species_codes", nargs="+", help="List of species codes.", default=[]
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
        "--species_codes_file",
        type=epath.Path,
        help="Path to the species codes",
        default=None,
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
    parser.add_argument(
        "--max_workers",
        type=int,
        help="The number of workers to use.",
        default=None,
    )
    args = parser.parse_args()
    main(
        species_codes=args.species_codes,
        n=args.n,
        target_path=args.target_path,
        types=args.types,
        species_codes_file=args.species_codes_file,
        sample_rate=args.sample_rate,
        window_s=args.window_s,
        max_len=args.max_len,
        max_workers=args.max_workers,
    )
