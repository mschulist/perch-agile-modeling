"""Fixtures building a small but complete project on disk.

The GUI and database tests all run against a real project directory: a hoplite
database with a handful of windows cut out of `ARU_test_data`, plus a trained
classifier and one classifier output.
"""

import base64
from datetime import datetime as dt
from pathlib import Path

import numpy as np
import pytest
from ml_collections import config_dict
from nicegui.testing import User
from perch_hoplite.db import datatypes
from scipy.io import wavfile

from perch_analyzer.app_context import AppContext
from perch_analyzer.classify.linear_model import LinearClassifier
from perch_analyzer.config.initialize_directory import initialize_directory

from .project_shape import (
    EMBEDDING_DIM,
    LABELS,
    NUM_MAIN,
    NUM_OTHER,
    NUM_WINDOWS,
    SAMPLE_RATE,
    WINDOW_SIZE_S,
)

pytest_plugins = ["nicegui.testing.user_plugin"]

# The account `project_dir` creates, which the `gui` fixture signs in as.
TEST_USERNAME = "tester"
TEST_PASSWORD = "correct horse"

# 1x1 transparent PNG.
_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)

REPO_ROOT = Path(__file__).resolve().parents[1]
ARU_DIR = REPO_ROOT / "ARU_test_data"


def _write_stub_assets(data_dir: Path, window_id: int) -> None:
    """Drop placeholder .wav/.png files for a window.

    Real rendering costs about a second per window; the pages only care that
    the files exist. `test_audio_windows.py` covers the rendering path itself.
    """
    windows_dir = data_dir / "precomputed_windows"
    windows_dir.mkdir(parents=True, exist_ok=True)
    wavfile.write(
        windows_dir / f"{window_id}.wav",
        SAMPLE_RATE,
        np.zeros(SAMPLE_RATE // 10, dtype=np.float32),
    )
    (windows_dir / f"{window_id}.png").write_bytes(_ONE_PIXEL_PNG)


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Create a project with windows, annotations, a classifier and an output."""
    data_dir = tmp_path / "project"
    rng = np.random.default_rng(0)

    analyzer_db, hoplite_db = initialize_directory(
        data_path=data_dir,
        project_name="test",
        user_name="tester",
        embedding_model="placeholder",
    )

    hoplite_db.insert_metadata(
        "model_config",
        config_dict.create(
            model_key="placeholder",
            embedding_dim=EMBEDDING_DIM,
            model_config=config_dict.create(
                sample_rate=SAMPLE_RATE, window_size_s=WINDOW_SIZE_S
            ),
        ),
    )
    hoplite_db.insert_metadata(
        "audio_sources",
        config_dict.create(
            audio_globs=[
                dict(dataset_name="test", base_path=str(ARU_DIR), file_glob="*.wav")
            ]
        ),
    )

    audio_file = sorted(ARU_DIR.glob("*.wav"))[0]
    recording_id = hoplite_db.insert_recording(filename=audio_file.name)

    for index in range(NUM_WINDOWS):
        offsets = [index * WINDOW_SIZE_S, (index + 1) * WINDOW_SIZE_S]
        window_id = hoplite_db.insert_window(
            recording_id=recording_id,
            offsets=offsets,
            embedding=rng.normal(size=EMBEDDING_DIM).astype(np.float16),
        )
        if index < NUM_MAIN:
            label, label_type = LABELS[0], datatypes.LabelType.POSITIVE
        elif index < NUM_MAIN + NUM_OTHER:
            label, label_type = LABELS[1], datatypes.LabelType.POSITIVE
        else:
            label, label_type = LABELS[0], datatypes.LabelType.UNCERTAIN
        hoplite_db.insert_annotation(
            recording_id=recording_id,
            offsets=offsets,
            label=label,
            label_type=label_type,
            provenance="tester"
            if label_type is datatypes.LabelType.POSITIVE
            else "searched_annotator",
        )
        _write_stub_assets(data_dir, window_id)
    hoplite_db.commit()

    classifier_id = analyzer_db.insert_classifier(
        datetime=dt(2026, 1, 2, 3, 4, 5),
        embedding_model="placeholder",
        labels=list(LABELS),
        train_ratio=0.8,
        rng=123,
        learning_rate=1e-3,
        weak_neg_rate=0.05,
        num_train_steps=8,
        metrics={
            "roc_auc": np.float64(0.9),
            "cmap": np.float64(0.8),
            "top1_acc": np.float32(0.75),
        },
        linear_classifier=LinearClassifier(
            beta=rng.normal(size=(EMBEDDING_DIM, len(LABELS))).astype(np.float32),
            beta_bias=np.zeros(len(LABELS), dtype=np.float32),
            classes=list(LABELS),
            embedding_model_config={"model_key": "placeholder"},
        ),
    )

    output_id = analyzer_db.insert_classifier_output(classifier_id)
    analyzer_db.insert_classifier_output_windows(
        output_id, [(1, 2.5, LABELS[0]), (2, 1.25, LABELS[0])]
    )
    _write_classifier_output_parquet(
        data_dir / "classifier_outputs" / f"{output_id}.parquet",
        audio_file.name,
    )

    analyzer_db.create_user(TEST_USERNAME, TEST_PASSWORD)

    return data_dir


def _write_classifier_output_parquet(path: Path, filename: str) -> None:
    """A small output file, so gather_classifier_outputs has rows to sample."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    from perch_analyzer.classify.classify import ARROW_SCHEMA

    rows = [
        # (window_id, label, logit)
        (window_id, label, float(NUM_WINDOWS - window_id))
        for window_id in range(1, NUM_WINDOWS + 1)
        for label in LABELS
    ]
    pq.write_table(
        pa.table(
            {
                "filename": [filename] * len(rows),
                "logit": [logit for _, _, logit in rows],
                "timestamp_s": [(wid - 1) * WINDOW_SIZE_S for wid, _, _ in rows],
                "window_id": [wid for wid, _, _ in rows],
                "label": [label for _, label, _ in rows],
            },
            schema=ARROW_SCHEMA,
        ),
        path,
    )


@pytest.fixture
def ctx(project_dir: Path) -> AppContext:
    return AppContext(project_dir)


@pytest.fixture
async def gui_unauthenticated(user: User, ctx: AppContext) -> User:
    """Register the GUI pages against the test project, signed out."""
    from perch_analyzer.gui.app import register_pages
    from perch_analyzer.gui.services import ProjectServices, set_project

    set_project(ProjectServices(ctx))
    register_pages()
    return user


async def sign_in(user: User, username: str, password: str) -> None:
    await user.open("/login")
    user.find(marker="username").type(username)
    user.find(marker="password").type(password)
    user.find(marker="submit").click()


@pytest.fixture
async def gui(gui_unauthenticated: User) -> User:
    """The GUI pages, signed in as the test user."""
    await sign_in(gui_unauthenticated, TEST_USERNAME, TEST_PASSWORD)
    await gui_unauthenticated.should_see("Welcome to Perch Analyzer!")
    return gui_unauthenticated
