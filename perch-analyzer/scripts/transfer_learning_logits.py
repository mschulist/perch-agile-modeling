from pathlib import Path

import polars as pl

WORK_DIR = Path("data/baseline_test")

with open(WORK_DIR / "annotated_window_ids.txt") as f:
    ann_window_ids = []
    for line in f.readlines():
        ann_window_ids.append(int(line))

ann_window_ids = set(ann_window_ids)

outputs = (
    pl.scan_parquet(
        "/home/mschulist/perch-agile-modeling/perch-analyzer/data/classifier_outputs/9.parquet"
    )
    .filter(pl.col("window_id").is_in(ann_window_ids))
    .with_columns(pl.col("label").str.split("_").list.get(0).alias("label"))
    .group_by(["window_id", "label"])
    .max()
)

outputs.sink_csv(WORK_DIR / "transfer_outputs.csv")
