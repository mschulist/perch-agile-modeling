from python_server.lib.perch_utils import GatherTargetRecordings
from python_server.lib.db import AccountsDB
from python_server.lib.perch_utils import GatherPossibleExamples


import tempfile
from chirp.projects.agile2 import embed, source_info, colab_utils
from chirp.projects.agile2.tests import test_utils
from etils import epath

from python_server.lib.perch_utils.annotate import AnnotatePossibleExamples

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

    # finish a target recording and make sure that it gets removed from the list of target recordings
    existing_id = existing_targets[0].id
    assert existing_id is not None
    db.finish_target_recording(existing_id, 1)

    existing_targets = db.get_target_recordings(species_code=None, call_type=None, project_id=1)

    finished = db.get_finished_targets(1)
    assert len(finished) == 1

    assert len(existing_targets) == 3


# create a fake hoplite db and insert some embeddings
hoplite_db_path = tempfile.TemporaryDirectory()

classes = ["amerob", "westan"]

filenames = ["1.wav", "2.wav", "3.wav", "4.wav"]

test_utils.make_wav_files(
    hoplite_db_path.name, classes, filenames, file_len_s=20, sample_rate_hz=32000
)

audio_sources = source_info.AudioSources(
    audio_globs=(
        source_info.AudioSourceConfig(
            dataset_name="test",
            base_path=hoplite_db_path.name,
            file_glob="*/*.wav",
            min_audio_len_s=0.0,
            target_sample_rate_hz=32000,
        ),
    )
)

configs = colab_utils.load_configs(
    audio_sources,
    model_config_key="perch_8",
    db_key="sqlite_usearch",
)

hoplite_db = configs.db_config.load_db()
db.setup()

worker = embed.EmbedWorker(
    audio_sources=configs.audio_sources_config,
    db=hoplite_db,
    model_config=configs.model_config,
)


worker.process_all(target_dataset_name="test")

print("DONE EMBEDDING")

precompute_dir = tempfile.TemporaryDirectory()


def test_search_hoplite_db():
    species_codes = ["amerob", "westan"]
    call_types = ["song", "call"]

    gatherer = GatherPossibleExamples(
        db=db,
        hoplite_db=hoplite_db,
        target_path=tmp_target_path.name,
        precompute_search_dir=precompute_dir.name,
        project_id=1,
    )

    gatherer.get_possible_examples(species_codes, call_types, 1, num_target_recordings=1)

    possible_examples = db.get_possible_examples(project_id=1)

    assert len(possible_examples) == 4

    for example in possible_examples:
        assert example.filename is not None
        assert example.id is not None
        assert example.score is not None
        assert example.timestamp_s is not None
        assert example.embedding_id is not None

    print(possible_examples)


# this path is just so that we can see the images and audio files that were created
tmp_annotation_path = epath.Path("test_annotations/")
tmp_annotation_path.mkdir(exist_ok=True, parents=True)


def test_annotate():
    annotate = AnnotatePossibleExamples(
        db=db,
        hoplite_db=hoplite_db,
        precompute_search_dir=precompute_dir.name,
        project_id=1,
    )

    error = None
    num_examples = 0
    while error is None:
        ex = annotate.get_next_possible_example()
        if ex is None:
            break
        annotate.annotate_possible_example(ex, "westan", "test_user")
        num_examples += 1
        image_path = annotate.get_possible_example_image_path(ex)
        audio_path = annotate.get_possible_example_audio_path(ex)
        assert image_path.exists()
        assert audio_path.exists()
        image_path.copy(tmp_annotation_path / image_path.name)
        audio_path.copy(tmp_annotation_path / audio_path.name)

    assert num_examples == 4
