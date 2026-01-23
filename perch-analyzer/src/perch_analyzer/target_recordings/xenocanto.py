import time
from perch_hoplite.taxonomy import namespace_db
import httpx

from perch_analyzer.config import config

SAMPLE_RATE = 32000
MAX_LEN = 60

XENO_CANTO_URL = "https://xeno-canto.org/api/3/recordings"


def get_xc_ids(config: config.Config, ebird_6_code: str, call_type: str) -> list[str]:
    xc_sci_name = convert_ebird_6_code_to_xc_sci_name(ebird_6_code)

    url = f'{XENO_CANTO_URL}?key={config.xenocanto_api_key}&query=sp:"{xc_sci_name}"+type:"{call_type}"+len:"1-{MAX_LEN}"'

    # continue trying if rate limited
    status_code = 0
    response = None
    while status_code != 200:
        response = httpx.get(url)
        status_code = response.status_code
        if status_code == 200:
            break
        if status_code == 401:
            raise ValueError(
                "unauthorized xenocanto request, make sure to set your xenocanto API key"
            )
        time.sleep(0.25)

    if not response:
        raise ValueError(
            f"Failed to get response from xeno-canto API for {xc_sci_name} ({ebird_6_code}): {call_type}. status code: {status_code}"
        )
    response_json = response.json()

    return [rec["id"] for rec in response_json["recordings"]]


def convert_ebird_6_code_to_xc_sci_name(ebird_6_code: str):
    name_db = namespace_db.load_db()

    mapping = name_db.mappings.get("xenocanto_11_2_to_ebird2022_species", None)
    if not mapping:
        raise KeyError("oops!...we do not have a mapping :(")

    reversed_mapping = {v: k for k, v in mapping.mapped_pairs.items()}

    xc_sci_name = reversed_mapping.get(ebird_6_code, None)
    if xc_sci_name is None:
        raise ValueError(f"Mapping not found for {ebird_6_code}.")
    return xc_sci_name


def convert_xc_sci_name_to_ebird_6_code(xc_scientific_name: str) -> str:
    name_db = namespace_db.load_db()

    mapping = name_db.mappings.get("xenocanto_11_2_to_ebird2022_species", None)
    if mapping is None:
        raise ValueError("Mapping not found. This error should never happen:/")

    ebird_6_code = mapping.mapped_pairs.get(xc_scientific_name, None)
    if ebird_6_code is None:
        raise ValueError(f"Mapping not found for {xc_scientific_name}.")
    return ebird_6_code
