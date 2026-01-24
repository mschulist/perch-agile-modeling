import gradio as gr
from dataclasses import dataclass
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_analyzer.examine import examine_annotations, audio_windows
from perch_hoplite.db import sqlite_usearch_impl, interface
from ml_collections import config_dict


@dataclass
class RecordingDisplay:
    """Data for displaying a single recording window."""

    filename: str
    offsets: str
    labels: str
    spec_file: str | None
    recording_file: str | None
    window_id: int
    labels_list: list[str]


def examine(
    config: config.Config,
    analyzer_db: db.AnalyzerDB,
    hoplite_db: sqlite_usearch_impl.SQLiteUSearchDB,
) -> gr.Blocks:
    hoplite_db = hoplite_db.thread_split()
    all_labels: list[str] = list(
        hoplite_db.get_all_labels(label_type=interface.LabelType.POSITIVE)
    )

    def filter_labels(search_query: str) -> list[list[str]]:
        """Filter labels based on search query"""
        if not search_query:
            return [[label] for label in all_labels]
        search_lower: str = search_query.lower()
        filtered: list[str] = [
            label for label in all_labels if search_lower in label.lower()
        ]
        return [[label] for label in filtered]

    def get_recordings_for_label(label: str) -> list[RecordingDisplay]:
        """Get all recordings with the selected label."""
        # Create new DB connection for this thread
        thread_hoplite_db = hoplite_db.thread_split()

        windows = examine_annotations.get_windows_by_label(thread_hoplite_db, label)
        recordings: list[RecordingDisplay] = []

        for window_with_annotations in windows:
            recording_file, spec_file = audio_windows.get_audio_window_path(
                config=config,
                hoplite_db=thread_hoplite_db,
                window_id=window_with_annotations.window.id,
            )

            # Get all labels for this window
            labels_list = [ann.label for ann in window_with_annotations.annotations]

            recordings.append(
                RecordingDisplay(
                    filename=window_with_annotations.recording.filename,
                    offsets=f"{window_with_annotations.window.offsets[0]:.2f}s - {window_with_annotations.window.offsets[1]:.2f}s",
                    labels=", ".join(labels_list),
                    spec_file=str(spec_file),
                    recording_file=str(recording_file),
                    window_id=window_with_annotations.window.id,
                    labels_list=labels_list,
                )
            )

        return recordings

    with gr.Blocks() as examine_blocks:
        with gr.Row():
            # Left column: Searchable label list (1/3 width)
            with gr.Column(scale=1):
                gr.Markdown("## Labels")
                search_box = gr.Textbox(
                    placeholder="Search labels...", label="Search", container=False
                )
                label_list = gr.Dataframe(
                    headers=["Label"],
                    datatype=["str"],
                    value=[[label] for label in all_labels],
                    interactive=False,
                    max_height=600,
                    wrap=True,
                )

            # Right column: Recordings display (2/3 width)
            with gr.Column(scale=2):
                gr.Markdown("## Recordings")
                selected_label_state = gr.State(value=None)

                @gr.render(inputs=[selected_label_state])
                def render_recordings(selected_label: str | None):
                    if selected_label is None:
                        gr.Markdown("Select a label to view recordings.")
                        return

                    recordings = get_recordings_for_label(selected_label)

                    if not recordings:
                        gr.Markdown("No recordings found for this label.")
                        return

                    for rec in recordings:
                        with gr.Group() as recording_group:
                            gr.Markdown(f"### {rec.filename}")

                            labels_display = gr.Markdown(
                                f"**Offsets:** {rec.offsets}  \n**Labels:** {rec.labels}",
                                elem_id=f"labels_{rec.window_id}",
                            )

                            # Hidden state to store window info
                            window_id_state = gr.State(value=rec.window_id)
                            offsets_state = gr.State(value=rec.offsets)
                            selected_label_filter = gr.State(value=selected_label)

                            # Edit button and controls in a clean layout
                            edit_btn = gr.Button(
                                "Edit Labels", size="sm", variant="secondary"
                            )

                            with gr.Column(visible=False) as edit_section:
                                edit_dropdown = gr.Dropdown(
                                    choices=all_labels,
                                    value=rec.labels_list,
                                    multiselect=True,
                                    allow_custom_value=True,
                                    label="Labels",
                                    interactive=True,
                                )
                                with gr.Row():
                                    save_btn = gr.Button(
                                        "Save",
                                        variant="primary",
                                        size="sm",
                                        interactive=len(rec.labels_list) > 0,
                                    )
                                    cancel_btn = gr.Button("Cancel", size="sm")

                            gr.Image(
                                value=rec.spec_file,
                                height=350,
                                show_label=False,
                                container=False,
                            )
                            gr.Audio(
                                value=rec.recording_file,
                                show_label=False,
                                container=False,
                            )

                            # Event handlers for this recording
                            def show_edit():
                                return gr.Column(visible=True)

                            def hide_edit():
                                return gr.Column(visible=False)

                            def update_save_button(labels: list[str]) -> gr.Button:
                                """Enable save button only when at least one label is selected."""
                                return gr.Button(
                                    interactive=len(labels) > 0 if labels else False
                                )

                            def save_labels_handler(
                                new_labels: list[str],
                                window_id: int,
                                offsets: str,
                                current_label: str,
                            ) -> tuple:
                                # Create new DB connection for this thread
                                thread_hoplite_db = hoplite_db.thread_split()

                                # Update labels in database
                                examine_annotations.update_labels(
                                    config=config,
                                    hoplite_db=thread_hoplite_db,
                                    window_id=window_id,
                                    new_labels=new_labels,
                                )
                                thread_hoplite_db.commit()

                                # Check if the current label was removed
                                if current_label not in new_labels:
                                    # Hide the entire recording group
                                    return (
                                        "",
                                        gr.Column(visible=False),
                                        gr.Group(visible=False),
                                    )

                                # Return updated markdown string and hide modal
                                labels_str = (
                                    ", ".join(new_labels) if new_labels else "None"
                                )
                                return (
                                    f"**Offsets:** {offsets}  \n**Labels:** {labels_str}",
                                    gr.Column(visible=False),
                                    gr.Group(visible=True),
                                )

                            edit_btn.click(fn=show_edit, outputs=[edit_section])
                            cancel_btn.click(fn=hide_edit, outputs=[edit_section])
                            edit_dropdown.change(
                                fn=update_save_button,
                                inputs=[edit_dropdown],
                                outputs=[save_btn],
                            )
                            save_btn.click(
                                fn=save_labels_handler,
                                inputs=[
                                    edit_dropdown,
                                    window_id_state,
                                    offsets_state,
                                    selected_label_filter,
                                ],
                                outputs=[labels_display, edit_section, recording_group],
                            )

        # Wire up the search functionality
        search_box.change(fn=filter_labels, inputs=[search_box], outputs=[label_list])

        # Wire up label selection to update state
        def update_selected_label(evt: gr.SelectData) -> str:
            return evt.value

        label_list.select(fn=update_selected_label, outputs=[selected_label_state])

    return examine_blocks
