from typing import List
from perch_hoplite.taxonomy import namespace_db


def get_all_species_codes() -> List[str]:
    name_db = namespace_db.load_db()
    mapping = name_db.mappings.get("xenocanto_11_2_to_ebird2022_species", None)
    if mapping is None:
        raise ValueError("Mapping not found. This error should never happen:/")

    reversed_mapping = {v: k for k, v in mapping.mapped_pairs.items()}

    return list(reversed_mapping.keys())
