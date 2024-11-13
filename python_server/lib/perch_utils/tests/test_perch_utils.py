from ..target_recordings import GatherTargetRecordings
from ...db import AccountsDB
import tempfile

# create a fake db
tmp_db = tempfile.NamedTemporaryFile(suffix=".db")
db = AccountsDB(tmp_db.name)

tmp_target_path = tempfile.TemporaryDirectory()
targets = GatherTargetRecordings(db, tmp_target_path.name)

db.setup()


def test_process_req_for_targets():
    species_codes = ["amerob", "westan"]
    call_types = ["song", "call"]

    targets.process_req_for_targets(species_codes, call_types, 1, project_id=None)

    # check that the target recordings were added to the db

    existing_targets = db.get_target_recordings(species_code=None, call_type=None, project_id=None)

    # there should be 4 target recordings in the db, 1 for each of the 4 species/call type combinations
    assert len(existing_targets) == 4

    for target in existing_targets:
        assert target.species in species_codes
        assert target.call_type in call_types
        assert target.timestamp_s is not None
        assert target.xc_id is not None
        assert target.id is not None
        assert target.id > 0

        assert target.species in species_codes
        assert target.call_type in call_types

    # try again and make sure that no new target recordings are added
    targets.process_req_for_targets(species_codes, call_types, 1, project_id=None)

    existing_targets = db.get_target_recordings(species_code=None, call_type=None, project_id=1)

    assert len(existing_targets) == 4
