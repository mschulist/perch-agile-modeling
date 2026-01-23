import gradio as gr
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_analyzer.examine import examine_annotations, audio_windows
from perch_hoplite.db import sqlite_usearch_impl, interface
from ml_collections import config_dict


def get_next_example_to_annotate(
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
) -> examine_annotations.WindowWithAnnotations | None:
    annotations = hoplite_db.get_all_annotations(
        config_dict.create(eq=dict(label_type=interface.LabelType.POSSIBLE))
    )

    # there are no examples to annotate
    if len(annotations) == 0:
        return None

    annotation = annotations[0]

    recording = hoplite_db.get_recording(annotation.recording_id)
    windows = hoplite_db.get_all_windows(
        filter=config_dict.create(
            eq=dict(recording_id=recording.id), approx=dict(offsets=annotation.offsets)
        )
    )

    if len(windows) != 1:
        raise ValueError(
            f"ut oh, there are multiple (or zero) windows with the same offsets and recording id, {len(windows)}"
        )

    return examine_annotations.WindowWithAnnotations(
        recording=recording, window=windows[0], annotations=[annotation]
    )


def annotate(
    config: config.Config,
    analyzer_db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
):
    next_window = get_next_example_to_annotate(hoplite_db=hoplite_db)

    with gr.Blocks() as annotate_blocks:
        if next_window is None:
            gr.Markdown("no more windows to annotate!")
            return annotate_blocks

        

        recording_file, spec_file = audio_windows.get_audio_window_path(
            config=config, hoplite_db=hoplite_db, window_id=next_window.window.id
        )

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown(f"## Filename: {next_window.recording.filename}")
                gr.Markdown(f"## Target recording label: {next_window.annotations[0].label}")
                gr.Markdown(f"### Offsets: {next_window.window.offsets}")
            with gr.Column(scale=2):
                gr.Image(str(spec_file), height=400, container=False)
                gr.Audio(
                    str(recording_file),
                    label="Audio",
                    container=False,
                    show_label=False,
                )

    return annotate_blocks
