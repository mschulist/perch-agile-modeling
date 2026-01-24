import gradio as gr
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl, interface
from ml_collections import config_dict


def summary(
    config: config.Config,
    analyzer_db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
):
    class_counts = hoplite_db.count_each_label()
    embedding_count = hoplite_db.count_embeddings()
    annotation_count = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.POSITIVE))
        )
    )
    recording_count = len(hoplite_db.get_all_recordings())

    target_recordings_count = analyzer_db.count_target_recordings(True)
    annotations_to_be_labeled = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.POSSIBLE))
        )
    )

    with gr.Blocks() as summary_block:
        gr.Markdown(f"""
                    <div style="text-align: center;">
                    <h1>Summary<h1>
                    <h2>Classes: {len(class_counts)}</h2>
                    <h2>Windows: {embedding_count}</h2>
                    <h2>Annotations: {annotation_count}</h2>
                    <h2>Recordings: {recording_count}</h2>
                    <h2>Target recordings: {target_recordings_count}</h2>
                    <h2>Annotations to be labeled: {annotations_to_be_labeled}</h2>
                    </div>
                    """)

    return summary_block
