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
) -> int:
    """Store up to `num_windows` windows scoring in (min_logit, max_logit).

    Returns the number of newly stored windows.
    """
    classifier_output = analyzer_db.get_classifier_output(classifier_output_id)

    windows = (
        pl.scan_parquet(classifier_output.parquet_path)
        .filter(
            pl.col("label") == label,
            pl.col("logit") > min_logit,
            pl.col("logit") < max_logit,
        )
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
