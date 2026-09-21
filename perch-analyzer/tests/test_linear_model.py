from pathlib import Path
from typing import Any

import numpy as np
import pytest

from perch_analyzer.classify.linear_model import (
    LinearClassifier,
    batched_embedding_iterator,
)


def make_classifier() -> LinearClassifier:
    rng = np.random.default_rng(1)
    return LinearClassifier(
        beta=rng.normal(size=(6, 3)).astype(np.float32),
        beta_bias=rng.normal(size=3).astype(np.float32),
        classes=["a", "b", "c"],
        embedding_model_config={"model_key": "placeholder"},
    )


def test_save_load_round_trip(tmp_path: Path):
    classifier = make_classifier()
    path = str(tmp_path / "clf.json")
    classifier.save(path)
    loaded = LinearClassifier.load(path)

    assert np.array_equal(loaded.beta, classifier.beta)
    assert np.array_equal(loaded.beta_bias, classifier.beta_bias)
    assert list(loaded.classes) == list(classifier.classes)


def test_format_matches_perch_hoplite(tmp_path: Path):
    """The on-disk format must stay readable by perch_hoplite, and vice versa."""
    from perch_hoplite.agile.classifier import LinearClassifier as HopliteClassifier

    classifier = make_classifier()
    path = str(tmp_path / "clf.json")
    classifier.save(path)

    theirs = HopliteClassifier.load(path)
    assert np.array_equal(theirs.beta, classifier.beta)
    assert theirs.to_config_dict().to_json() == classifier.to_config_dict().to_json()

    ours = LinearClassifier.from_hoplite(theirs)
    embeddings = np.random.default_rng(2).normal(size=(4, 6)).astype(np.float32)
    assert np.allclose(ours(embeddings), theirs(embeddings))


def test_inference_is_affine():
    classifier = make_classifier()
    embeddings = np.random.default_rng(3).normal(size=(5, 6)).astype(np.float32)
    expected = embeddings @ classifier.beta + classifier.beta_bias
    assert np.allclose(classifier(embeddings), expected)


def test_batched_embedding_iterator_covers_every_id():
    class FakeDB:
        def get_embeddings_batch(self, window_ids: Any) -> np.ndarray:
            return np.array(window_ids, dtype=np.float32).reshape(-1, 1)

    ids = np.arange(7)
    batches = list(batched_embedding_iterator(FakeDB(), ids, batch_size=3))

    assert [len(batch_ids) for batch_ids, _ in batches] == [3, 3, 1]
    assert np.array_equal(np.concatenate([b for b, _ in batches]), ids)


async def test_run_blocking_tolerates_a_none_result():
    """`load` treats None as cancellation; void work must not go through it."""
    import asyncio

    from perch_analyzer.gui.background import load, run_blocking

    calls = []

    def returns_none() -> None:
        calls.append(1)

    def returns_value() -> int:
        return 7

    await run_blocking(returns_none)
    assert calls == [1]
    assert await load(returns_value) == 7

    with pytest.raises(asyncio.CancelledError):
        await load(returns_none)  # type: ignore[arg-type]
