import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from perch_analyzer.app_context import AppContext
from perch_analyzer.classify.classifier_outputs import gather_classifier_output_windows
from perch_analyzer.classify.classify import ARROW_SCHEMA

# (window_id, filename, timestamp_s); window ids 1 and 2 are already gathered
# by conftest, so these start at 10.
ROWS = [
    (10, "a.wav", 0.0),
    (11, "a.wav", 0.1),
    (12, "a.wav", 5.0),
    (13, "b.wav", 0.1),
    (14, "b.wav", 10.0),
]


@pytest.fixture
def output_id(ctx: AppContext) -> int:
    output = ctx.analyzer_db.get_classifier_output(1)
    pq.write_table(
        pa.table(
            {
                "filename": [filename for _, filename, _ in ROWS],
                "logit": [1.0] * len(ROWS),
                "timestamp_s": [offset for _, _, offset in ROWS],
                "window_id": [window_id for window_id, _, _ in ROWS],
                "label": ["mouchi"] * len(ROWS),
            },
            schema=ARROW_SCHEMA,
        ),
        output.parquet_path,
    )
    return output.id


def gathered_ids(ctx: AppContext, output_id: int) -> set[int]:
    windows = ctx.analyzer_db.get_all_classifier_output_windows(
        output_id, label="mouchi"
    )
    return {w.window_id for w in windows}


def gather(
    ctx: AppContext,
    output_id: int,
    filename: str | None = None,
    min_offset: float | None = None,
    max_offset: float | None = None,
) -> int:
    return gather_classifier_output_windows(
        analyzer_db=ctx.analyzer_db,
        classifier_output_id=output_id,
        min_logit=0.0,
        max_logit=2.0,
        label="mouchi",
        num_windows=100,
        filename=filename,
        min_offset=min_offset,
        max_offset=max_offset,
    )


def test_gather_without_filters_takes_everything(ctx: AppContext, output_id: int):
    assert gather(ctx, output_id) == len(ROWS)


def test_gather_by_filename(ctx: AppContext, output_id: int):
    assert gather(ctx, output_id, filename="b.wav") == 2
    assert gathered_ids(ctx, output_id) == {13, 14}


def test_gather_by_offset_range(ctx: AppContext, output_id: int):
    gather(ctx, output_id, min_offset=0.1, max_offset=5.0)
    assert gathered_ids(ctx, output_id) == {11, 12, 13}


def test_gather_by_exact_float32_offset(ctx: AppContext, output_id: int):
    """0.1 is stored as float32 and must still match a float64 bound."""
    gather(ctx, output_id, filename="a.wav", min_offset=0.1, max_offset=0.1)
    assert gathered_ids(ctx, output_id) == {11}
