from perch_analyzer.db import db
import polars as pl


def gather_classifier_output_windows(
    analyzer_db: db.AnalyzerDB,
    classifier_output_id: int,
    min_logit: float,
    max_logit: float,
    label: str,
    num_windows: int,
):
    classifier_outputs = analyzer_db.get_classifier_output(classifier_output_id)

    windows = (
        pl.scan_parquet(classifier_outputs.parquet_path)
        .filter(
            pl.col("label") == label,
            pl.col("logit") > min_logit,
            pl.col("logit") < max_logit,
        )
        .limit(num_windows)
        .collect()
    )

    for window in windows.iter_rows(named=True):
        window_id = window["window_id"]
        logit = window["logit"]
        label = window["label"]

        if analyzer_db.get_all_classifier_output_windows(
            classifier_output_id=classifier_output_id, window_id=window_id, label=label
        ):
            # skip adding duplicates
            continue

        analyzer_db.insert_classifier_output_window(
            classifier_output_id=classifier_output_id,
            window_id=window_id,
            logit=logit,
            label=label,
        )
