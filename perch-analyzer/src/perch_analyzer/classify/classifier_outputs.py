"""Sample windows out of a classifier output's parquet file for review."""

import logging

import polars as pl

from perch_analyzer.db import db

logger = logging.getLogger(__name__)


def gather_classifier_output_windows(
    analyzer_db: db.AnalyzerDB,
    classifier_output_id: int,
    min_logit: float,
    max_logit: float,
    label: str,
    num_windows: int,
    filename: str | None = None,
    min_offset: float | None = None,
    max_offset: float | None = None,
) -> int:
    """Store up to `num_windows` windows scoring in (min_logit, max_logit).

    Optionally restrict to windows from the recording `filename` and whose
    start offset (in seconds) lies in [min_offset, max_offset].

    Returns the number of newly stored windows.
    """
    classifier_output = analyzer_db.get_classifier_output(classifier_output_id)

    filters = [
        pl.col("label") == label,
        pl.col("logit") > min_logit,
        pl.col("logit") < max_logit,
    ]
    if filename is not None:
        filters.append(pl.col("filename") == filename)
    if min_offset is not None:
        filters.append(pl.col("timestamp_s") >= min_offset)
    if max_offset is not None:
        filters.append(pl.col("timestamp_s") <= max_offset)

    windows = (
        pl.scan_parquet(classifier_output.parquet_path)
        .filter(*filters)
        .limit(num_windows)
        .collect()
    )

    # One query for the whole dedupe rather than one per candidate window.
    existing = analyzer_db.get_existing_output_window_keys(classifier_output_id)

    to_insert: list[tuple[int, float, str]] = []
    for row in windows.iter_rows(named=True):
        key = (row["window_id"], row["label"])
        if key in existing:
            continue
        existing.add(key)
        to_insert.append((row["window_id"], row["logit"], row["label"]))

    inserted = analyzer_db.insert_classifier_output_windows(
        classifier_output_id, to_insert
    )
    logger.info(
        "gathered %d window(s) for label %r (%d already present)",
        inserted,
        label,
        len(windows) - inserted,
    )
    return inserted
