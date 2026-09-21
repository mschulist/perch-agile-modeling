"""Fixtures building a small but complete project on disk.

The GUI and database tests all run against a real project directory: a hoplite
database with a handful of windows cut out of `ARU_test_data`, plus a trained
classifier and one classifier output.
"""

from datetime import datetime as dt
from pathlib import Path

import numpy as np
import pytest
from ml_collections import config_dict
from nicegui.testing import User
from perch_hoplite.db import datatypes

from perch_analyzer.app_context import AppContext
from perch_analyzer.classify.linear_model import LinearClassifier
from perch_analyzer.config.initialize_directory import initialize_directory

pytest_plugins = ["nicegui.testing.user_plugin"]

REPO_ROOT = Path(__file__).resolve().parents[1]
ARU_DIR = REPO_ROOT / "ARU_test_data"

SAMPLE_RATE = 32000
WINDOW_SIZE_S = 5.0
EMBEDDING_DIM = 128  # matches the "placeholder" preset model
NUM_WINDOWS = 6
LABELS = ("stejay", "mouchi")


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
        hoplite_db.insert_window(
            recording_id=recording_id,
            offsets=offsets,
            embedding=rng.normal(size=EMBEDDING_DIM).astype(np.float16),
        )
        # First few windows are annotated, the rest are pending review.
        if index < 4:
            hoplite_db.insert_annotation(
                recording_id=recording_id,
                offsets=offsets,
                label=LABELS[index % len(LABELS)],
                label_type=datatypes.LabelType.POSITIVE,
                provenance="tester",
            )
        else:
            hoplite_db.insert_annotation(
                recording_id=recording_id,
                offsets=offsets,
                label=LABELS[0],
                label_type=datatypes.LabelType.UNCERTAIN,
                provenance="searched_annotator",
            )
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

    return data_dir


@pytest.fixture
def ctx(project_dir: Path) -> AppContext:
    return AppContext(project_dir)


@pytest.fixture
async def gui(user: User, ctx: AppContext) -> User:
    """Register the GUI pages against the test project for the simulated user."""
    from nicegui import app as nicegui_app

    from perch_analyzer.gui.app import register_pages
    from perch_analyzer.gui.services import ProjectServices, set_project

    set_project(ProjectServices(ctx))
    register_pages()
    nicegui_app.add_static_files("/data", ctx.data_dir)
    return user
