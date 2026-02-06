import reflex as rx
from typing import Optional
from pathlib import Path
import os
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.examine import examine_annotations, audio_windows
from perch_hoplite.db import interface


class ExamineState(ConfigState):
    """State management for the examine page."""

    # Search and filter state
    search_query: str = ""
    all_labels: list[str] = []
    filtered_labels: list[str] = []
    selected_label: Optional[str] = None

    # Recording display state
    recordings: list[dict] = []

    # Edit state for each recording (using window_id as key)
    editing_window_id: Optional[int] = None
    edit_labels: list[str] = []
    edit_window_offsets: str = ""

    @rx.event
    def on_mount_handler(self):
        """Initialize state when component mounts."""
        self.load_labels()

    def load_labels(self):
        """Load all labels from the database."""
        hoplite_db = self.get_hoplite_db().thread_split()
        self.all_labels = list(
            hoplite_db.get_all_labels(label_type=interface.LabelType.POSITIVE)
        )
        self.filtered_labels = self.all_labels.copy()

    def update_search_query(self, query: str):
        """Update search query and filter labels."""
        self.search_query = query
        if not query:
            self.filtered_labels = self.all_labels.copy()
        else:
            search_lower = query.lower()
            self.filtered_labels = [
                label for label in self.all_labels if search_lower in label.lower()
            ]

    def select_label_by_index(self, index: int):
        """Select a label by its index in the filtered list."""
        if 0 <= index < len(self.filtered_labels):
            label = self.filtered_labels[index]
            self.selected_label = label
            self.editing_window_id = None
            self.load_recordings_for_label(label)

    def load_recordings_for_label(self, label: str):
        """Load all recordings with the selected label."""
        hoplite_db = self.get_hoplite_db().thread_split()
        windows = examine_annotations.get_windows_by_label(hoplite_db, label)

        recordings = []
        for window_with_annotations in windows:
            recording_file, spec_file = audio_windows.get_audio_window_path(
                config=self.config,
                hoplite_db=hoplite_db,
                window_id=window_with_annotations.window.id,
            )

            labels_list = [ann.label for ann in window_with_annotations.annotations]

            # Convert absolute paths to backend URLs
            # Get backend URL from environment variables (set by Reflex)
            backend_host = os.getenv("BACKEND_HOST", "localhost")
            backend_port = os.getenv("BACKEND_PORT", "8000")
            backend_url = f"http://{backend_host}:{backend_port}"

            spec_relative = "/" + str(spec_file.relative_to(Path.cwd()))
            audio_relative = "/" + str(recording_file.relative_to(Path.cwd()))

            spec_url = f"{backend_url}{spec_relative}"
            audio_url = f"{backend_url}{audio_relative}"

            recordings.append(
                {
                    "window_id": window_with_annotations.window.id,
                    "filename": window_with_annotations.recording.filename,
                    "offsets": f"{window_with_annotations.window.offsets[0]:.2f}s - {window_with_annotations.window.offsets[1]:.2f}s",
                    "labels": labels_list,
                    "labels_str": ", ".join(labels_list),
                    "spec_file": spec_url,
                    "recording_file": audio_url,
                }
            )

        self.recordings = recordings

    def start_editing_by_index(self, index: int):
        """Start editing labels for a recording by its index."""
        if 0 <= index < len(self.recordings):
            rec = self.recordings[index]
            self.editing_window_id = rec["window_id"]
            self.edit_labels = rec["labels"].copy()
            self.edit_window_offsets = rec["offsets"]

    def cancel_editing(self):
        """Cancel editing labels."""
        self.editing_window_id = None
        self.edit_labels = []
        self.edit_window_offsets = ""

    def toggle_edit_label_by_index(self, index: int):
        """Toggle a label in the edit list by its index."""
        if 0 <= index < len(self.all_labels):
            label = self.all_labels[index]
            if label in self.edit_labels:
                self.edit_labels = [lbl for lbl in self.edit_labels if lbl != label]
            else:
                self.edit_labels = self.edit_labels + [label]

    def save_current_labels(self):
        """Save edited labels to database."""
        if not self.edit_labels or self.editing_window_id is None:
            return

        hoplite_db = self.get_hoplite_db().thread_split()

        # Update labels in database
        examine_annotations.update_labels(
            config=self.config,
            hoplite_db=hoplite_db,
            window_id=self.editing_window_id,
            new_labels=self.edit_labels,
        )
        hoplite_db.commit()

        # Check if the current selected label was removed
        if self.selected_label and self.selected_label not in self.edit_labels:
            # Remove this recording from the display
            self.recordings = [
                rec
                for rec in self.recordings
                if rec["window_id"] != self.editing_window_id
            ]
        else:
            # Update the recording in the list
            for rec in self.recordings:
                if rec["window_id"] == self.editing_window_id:
                    rec["labels"] = self.edit_labels.copy()
                    rec["labels_str"] = ", ".join(self.edit_labels)
                    break

        # Clear editing state
        self.editing_window_id = None
        self.edit_labels = []
        self.edit_window_offsets = ""


# Reusable Components


def search_box() -> rx.Component:
    """Search box component for filtering labels."""
    return rx.input(
        placeholder="Search labels...",
        value=ExamineState.search_query,
        on_change=ExamineState.update_search_query,
        width="100%",
    )


def labels_panel() -> rx.Component:
    """Left panel showing searchable list of labels."""
    return rx.vstack(
        rx.heading("Labels", size="6"),
        search_box(),
        rx.box(
            rx.cond(
                ExamineState.filtered_labels.length() > 0,
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ExamineState.filtered_labels.length()),
                        lambda i: rx.box(
                            rx.text(ExamineState.filtered_labels[i], size="3"),
                            padding="0.75em",
                            border_radius="0.5em",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=ExamineState.select_label_by_index(i),
                        ),
                    ),
                    spacing="1",
                    width="100%",
                ),
                rx.text("No labels found", size="2", color="gray"),
            ),
            max_height="600px",
            overflow_y="auto",
            width="100%",
            border=f"1px solid {rx.color('gray', 6)}",
            border_radius="0.5em",
            padding="0.5em",
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def recording_card(recording: dict, index: int) -> rx.Component:
    """Card component for displaying a single recording."""

    return rx.card(
        rx.vstack(
            # Header with filename
            rx.heading(recording["filename"], size="5"),
            # Offsets and labels display
            rx.vstack(
                rx.text(
                    f"Offsets: {recording['offsets']}",
                    size="2",
                    weight="bold",
                ),
                rx.text(
                    f"Labels: {recording['labels_str']}",
                    size="2",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            # Edit button (only show when not editing this recording)
            rx.cond(
                ExamineState.editing_window_id != recording["window_id"],
                rx.button(
                    "Edit Labels",
                    on_click=ExamineState.start_editing_by_index(index),
                    variant="outline",
                    size="2",
                ),
                # Edit section (show when editing this recording)
                rx.cond(
                    ExamineState.editing_window_id == recording["window_id"],
                    rx.vstack(
                        rx.text("Select labels:", size="2", weight="bold"),
                        rx.box(
                            rx.vstack(
                                rx.foreach(
                                    rx.Var.range(ExamineState.all_labels.length()),
                                    lambda label_idx: rx.checkbox(
                                        rx.text(
                                            ExamineState.all_labels[label_idx], size="2"
                                        ),
                                        checked=ExamineState.edit_labels.contains(
                                            ExamineState.all_labels[label_idx]
                                        ),
                                        on_change=ExamineState.toggle_edit_label_by_index(
                                            label_idx
                                        ),
                                    ),
                                ),
                                spacing="1",
                                width="100%",
                            ),
                            max_height="200px",
                            overflow_y="auto",
                            width="100%",
                        ),
                        rx.hstack(
                            rx.button(
                                "Save",
                                on_click=ExamineState.save_current_labels,
                                variant="solid",
                                size="2",
                                disabled=ExamineState.edit_labels.length() == 0,
                            ),
                            rx.button(
                                "Cancel",
                                on_click=ExamineState.cancel_editing,
                                variant="outline",
                                size="2",
                            ),
                            spacing="2",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
            ),
            # Spectrogram image
            rx.image(
                src=recording["spec_file"],
                alt="Spectrogram",
                width="100%",
                height="auto",
                max_height="350px",
                object_fit="contain",
            ),
            # Audio player
            rx.audio(
                src=recording["recording_file"],
                controls=True,
                width="100%",
                preload=None,
            ),
            spacing="4",
            width="100%",
            align="start",
        ),
        width="100%",
    )


def recordings_panel() -> rx.Component:
    """Right panel showing recordings for selected label."""
    return rx.vstack(
        rx.heading("Recordings", size="6"),
        rx.cond(
            ExamineState.selected_label,
            rx.cond(
                ExamineState.recordings.length() > 0,
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ExamineState.recordings.length()),
                        lambda i: recording_card(ExamineState.recordings[i], i),
                    ),
                    spacing="4",
                    width="100%",
                    overflow_y="auto",
                ),
                rx.text("No recordings found for this label.", size="3"),
            ),
            rx.text("Select a label to view recordings.", size="3"),
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def examine() -> rx.Component:
    """Main examine page component."""
    return rx.container(
        rx.hstack(
            # Left column: Labels (1/3 width)
            rx.box(
                labels_panel(),
                flex="1",
                min_width="250px",
                height="fit-content",
            ),
            # Right column: Recordings (2/3 width)
            rx.box(
                recordings_panel(),
                flex="2",
                min_width="400px",
                height="fit-content",
            ),
            spacing="6",
            width="100%",
            align_items="start",
        ),
        on_mount=ExamineState.on_mount_handler,
        size="4",
        padding="2em",
    )
