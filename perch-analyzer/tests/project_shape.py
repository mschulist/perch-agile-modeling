"""Shape of the project that `conftest.project_dir` builds.

Kept out of `conftest.py` so tests can import the numbers directly.
"""

SAMPLE_RATE = 32000
WINDOW_SIZE_S = 5.0
EMBEDDING_DIM = 128  # matches the "placeholder" preset model
LABELS = ("stejay", "mouchi")

# Enough windows under one label to paginate (PAGE_SIZE is 10).
NUM_MAIN = 12
NUM_OTHER = 2
NUM_UNCERTAIN = 2
NUM_WINDOWS = NUM_MAIN + NUM_OTHER + NUM_UNCERTAIN
