"""Pure-numpy linear classifier, wire-compatible with perch_hoplite.

`perch_hoplite.agile.classifier` imports TensorFlow at module scope, but
TensorFlow is only needed to *train* a classifier.  Loading one and running
inference with it is a dot product.  Keeping that path here means the only
command that pays the ~4.5s TensorFlow import is `create_classifier`.

The on-disk JSON format is byte-identical to
`perch_hoplite.agile.classifier.LinearClassifier`, so classifiers written by
either implementation are readable by the other.
"""

import base64
import dataclasses
import json
from collections.abc import Iterator, Sequence
from typing import Any, Protocol

import numpy as np
from ml_collections import config_dict


class _HopliteLinearClassifier(Protocol):
    """Structural type for perch_hoplite's TensorFlow-trained classifier.

    Declared read-only so that a `tuple[str, ...]` of classes satisfies
    `Sequence[str]`; read-write protocol members would be invariant.
    """

    @property
    def beta(self) -> np.ndarray: ...

    @property
    def beta_bias(self) -> np.ndarray: ...

    @property
    def classes(self) -> Sequence[str]: ...

    @property
    def embedding_model_config(self) -> Any: ...


@dataclasses.dataclass
class LinearClassifier:
    """Linear classifier params and metadata."""

    beta: np.ndarray
    beta_bias: np.ndarray
    classes: Sequence[str]
    embedding_model_config: Any

    def __call__(self, embeddings: np.ndarray) -> np.ndarray:
        return np.dot(embeddings, self.beta) + self.beta_bias

    @classmethod
    def from_hoplite(cls, other: _HopliteLinearClassifier) -> "LinearClassifier":
        """Adopt a classifier produced by perch_hoplite's TensorFlow trainer."""
        return cls(
            beta=other.beta,
            beta_bias=other.beta_bias,
            classes=other.classes,
            embedding_model_config=other.embedding_model_config,
        )

    def to_config_dict(self) -> config_dict.ConfigDict:
        cfg = config_dict.ConfigDict()
        cfg.model_config = self.embedding_model_config
        cfg.classes = self.classes
        # Numpy arrays are stored as base64 encoded blobs.
        cfg.beta = base64.b64encode(np.float32(self.beta).tobytes()).decode("ascii")
        cfg.beta_bias = base64.b64encode(np.float32(self.beta_bias).tobytes()).decode(
            "ascii"
        )
        return cfg

    @classmethod
    def from_config_dict(cls, cfg: config_dict.ConfigDict) -> "LinearClassifier":
        classes = cfg.classes
        beta = np.frombuffer(base64.b64decode(cfg.beta), dtype=np.float32)
        beta = np.reshape(beta, (-1, len(classes)))
        beta_bias = np.frombuffer(base64.b64decode(cfg.beta_bias), dtype=np.float32)
        return cls(beta, beta_bias, classes, cfg.model_config)

    def save(self, path: str):
        with open(path, "w") as f:
            f.write(self.to_config_dict().to_json())

    @classmethod
    def load(cls, path: str) -> "LinearClassifier":
        with open(path) as f:
            cfg = config_dict.ConfigDict(json.loads(f.read()))
        return cls.from_config_dict(cfg)


class _EmbeddingSource(Protocol):
    """Anything that can hand back embeddings for a batch of window ids.

    `window_ids` is untyped on purpose: hoplite declares `Sequence[int]` but is
    called with (and is fastest given) a numpy array, so pinning it down here
    would only reject the one implementation this is meant to describe.
    """

    def get_embeddings_batch(self, window_ids: Any) -> np.ndarray: ...


def batched_embedding_iterator(
    hoplite_db: _EmbeddingSource,
    window_ids: np.ndarray,
    batch_size: int = 1024,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Iterate over embeddings in batches."""
    for start in range(0, len(window_ids), batch_size):
        batch_ids = window_ids[start : start + batch_size]
        yield batch_ids, hoplite_db.get_embeddings_batch(batch_ids)
