from dataclasses import dataclass
import reflex as rx
from typing import Optional
from pathlib import Path
import os
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.examine import examine_annotations, audio_windows
from perch_hoplite.db import interface


@dataclass
class WindowWithMetadata:
    window_id: int
    filename: str
    offsets: list[float]
    labels: list[str]
    spec_file: str
    audio_file: str


class ExamineState(ConfigState):
    """State management for the examine page."""

    # Search and filter state
    search_query: str = ""
    all_labels: list[str] = []
    filtered_labels: list[str] = []
    selected_label: Optional[str] = None

    # Windows display state
    windows: list[WindowWithMetadata] = []

    # Edit state for each recording (using window_id as key)
    editing_window_id: Optional[int] = None
    edit_labels: list[str] = []
    label_search: str = ""
    filtered_label_suggestions: list[str] = []

    @rx.event
    def update_label_search(self, query: str):
        """Update label search and filter suggestions."""
        self.label_search = query
        if not query:
            self.filtered_label_suggestions = []
        else:
            search_lower = query.lower()
            # Filter labels not already selected
            self.filtered_label_suggestions = [
                label
                for label in self.all_labels
                if search_lower in label.lower() and label not in self.edit_labels
            ][:10]  # Limit to 10 suggestions

    @rx.event
    def add_label(self, label: str):
        """Add a label to the edit list."""
        if label and label not in self.edit_labels:
            self.edit_labels = self.edit_labels + [label]
            # Add to all_labels if it's a new label
            if label not in self.all_labels:
                self.all_labels = self.all_labels + [label]
        self.label_search = ""
        self.filtered_label_suggestions = []

    @rx.event
    def add_current_search_as_label(self):
        """Add the current search text as a new label."""
        if self.label_search.strip():
            self.add_label(self.label_search.strip())

    @rx.event
    def remove_edit_label(self, label: str):
        """Remove a label from the edit list."""
        self.edit_labels = [lbl for lbl in self.edit_labels if lbl != label]

    @rx.event
    def on_mount_handler(self):
        """Initialize state when component mounts."""
        self.load_labels()

    @rx.event
    def load_labels(self):
        """Load all labels from the database."""
        hoplite_db = self.get_hoplite_db().thread_split()
        self.all_labels = list(
            hoplite_db.get_all_labels(label_type=interface.LabelType.POSITIVE)
        )
        self.filtered_labels = self.all_labels.copy()

    @rx.event
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

    @rx.event
    def select_label_by_index(self, index: int):
        """Select a label by its index in the filtered list."""
        if 0 <= index < len(self.filtered_labels):
            label = self.filtered_labels[index]
            self.selected_label = label
            self.editing_window_id = None
            self.load_recordings_for_label(label)

    @rx.event
    def load_recordings_for_label(self, label: str):
        """Load all recordings with the selected label."""
        hoplite_db = self.get_hoplite_db().thread_split()
        windows = examine_annotations.get_windows_by_label(hoplite_db, label)

        windows_with_metadata: list[WindowWithMetadata] = []
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

            # Compute paths using /data prefix, which is what the backend uses to fetch 
            # data from the data_dir (for spectrograms and audio)
            data_path = Path(self.config.data_path)
            spec_relative = "/data/" + str(spec_file.relative_to(data_path))
            audio_relative = "/data/" + str(recording_file.relative_to(data_path))

            spec_url = f"{backend_url}{spec_relative}"
            audio_url = f"{backend_url}{audio_relative}"

            windows_with_metadata.append(
                WindowWithMetadata(
                    window_id=window_with_annotations.window.id,
                    filename=window_with_annotations.recording.filename,
                    offsets=window_with_annotations.window.offsets,
                    labels=labels_list,
                    spec_file=spec_url,
                    audio_file=audio_url,
                )
            )

        self.windows = windows_with_metadata

    @rx.event
    def start_editing_by_index(self, index: int):
        """Start editing labels for a recording by its index."""
        if 0 <= index < len(self.windows):
            window = self.windows[index]
            self.editing_window_id = window.window_id
            self.edit_labels = window.labels.copy()

    @rx.event
    def cancel_editing(self):
        """Cancel editing labels."""
        self.editing_window_id = None
        self.edit_labels = []

    @rx.event
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
            self.windows = [
                window
                for window in self.windows
                if window.window_id != self.editing_window_id
            ]
        else:
            # Update the recording in the list
            for window in self.windows:
                if window.window_id == self.editing_window_id:
                    window.labels = self.edit_labels.copy()
                    break

        # Clear editing state
        self.editing_window_id = None
        self.edit_labels = []
        self.label_search = ""
        self.filtered_label_suggestions = []


# Reusable Components


def label_multiselect() -> rx.Component:
    """Multiselect component for editing labels with search and create functionality."""
    return rx.vstack(
        rx.text("Select or create labels:", size="2", weight="bold"),
        # Input field with add button
        rx.hstack(
            rx.input(
                placeholder="Type to search or create...",
                value=ExamineState.label_search,
                on_change=ExamineState.update_label_search,
                width="100%",
                size="2",
            ),
            rx.button(
                "Add",
                on_click=ExamineState.add_current_search_as_label,
                disabled=ExamineState.label_search == "",
                size="2",
                variant="solid",
            ),
            spacing="2",
            width="100%",
        ),
        # Dropdown suggestions
        rx.cond(
            ExamineState.filtered_label_suggestions.length() > 0,
            rx.box(
                rx.vstack(
                    rx.foreach(
                        ExamineState.filtered_label_suggestions,
                        lambda label: rx.box(
                            rx.text(label, size="2"),
                            padding="0.5em",
                            border_radius="0.25em",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=lambda: ExamineState.add_label(label),
                            width="100%",
                        ),
                    ),
                    spacing="1",
                    width="100%",
                ),
                width="100%",
                padding="0.5em",
                border=f"1px solid {rx.color('gray', 6)}",
                border_radius="0.5em",
                max_height="150px",
                overflow_y="auto",
                background_color=rx.color("gray", 1),
            ),
            rx.fragment(),
        ),
        # Show selected labels as removable badges
        rx.cond(
            ExamineState.edit_labels.length() > 0,
            rx.box(
                rx.foreach(
                    ExamineState.edit_labels,
                    lambda label: rx.badge(
                        rx.hstack(
                            rx.text(label, size="2"),
                            rx.icon(
                                "x",
                                size=14,
                                cursor="pointer",
                                on_click=lambda: ExamineState.remove_edit_label(label),
                            ),
                            spacing="1",
                            align="center",
                        ),
                        variant="solid",
                        size="2",
                        margin="0.25em",
                    ),
                ),
                width="100%",
                padding="0.5em",
                border=f"1px solid {rx.color('gray', 6)}",
                border_radius="0.5em",
                min_height="3em",
            ),
            rx.box(
                rx.text("No labels selected", size="2", color="gray"),
                width="100%",
                padding="0.5em",
                border=f"1px solid {rx.color('gray', 6)}",
                border_radius="0.5em",
            ),
        ),
        spacing="2",
        width="100%",
    )


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
                ExamineState.filtered_labels,
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ExamineState.filtered_labels.length()),  # type: ignore
                        lambda i: rx.box(
                            rx.text(ExamineState.filtered_labels[i], size="3"),
                            padding="0.75em",
                            border_radius="0.5em",
                            width="100%",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=ExamineState.select_label_by_index(i),  # type: ignore
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


def window_card(window: WindowWithMetadata, index: int) -> rx.Component:
    """Card component for displaying a single window."""

    return rx.card(
        rx.vstack(
            # Header with filename
            rx.heading(window.filename, size="5"),
            # Offsets and labels display
            rx.vstack(
                rx.text(
                    f"Offsets: {window.offsets[0]}",
                    size="2",
                    weight="bold",
                ),
                rx.text(
                    f"Labels: {window.labels}",
                    size="2",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            # Edit button (only show when not editing this recording)
            rx.cond(
                ExamineState.editing_window_id != window.window_id,
                rx.button(
                    "Edit Labels",
                    on_click=ExamineState.start_editing_by_index(index),
                    variant="outline",
                    size="2",
                    cursor="pointer",
                ),
                # Edit section (show when editing this recording)
                rx.cond(
                    ExamineState.editing_window_id == window.window_id,
                    rx.vstack(
                        label_multiselect(),
                        rx.hstack(
                            rx.button(
                                "Save",
                                on_click=ExamineState.save_current_labels,
                                variant="solid",
                                size="2",
                                disabled=ExamineState.edit_labels.length() == 0,
                                cursor="pointer"
                            ),
                            rx.button(
                                "Cancel",
                                on_click=ExamineState.cancel_editing,
                                variant="outline",
                                size="2",
                                cursor="pointer"
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
                src=window.spec_file,
                alt="Spectrogram",
                width="100%",
                height="auto",
                max_height="350px",
                object_fit="contain",
            ),
            # Audio player
            rx.audio(
                src=window.audio_file,
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


def windows_panel() -> rx.Component:
    """Right panel showing recordings for selected label."""
    return rx.vstack(
        rx.heading(
            rx.cond(
                ExamineState.selected_label,
                f"Recordings: ({ExamineState.selected_label})",
                "Recordings",
            ),
            size="6",
        ),
        rx.cond(
            ExamineState.selected_label,
            rx.cond(
                ExamineState.windows.length() > 0,  # type: ignore
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ExamineState.windows.length()),  # type: ignore
                        lambda i: window_card(ExamineState.windows[i], i),
                    ),
                    spacing="4",
                    width="100%",
                    overflow_y="auto",
                ),
                rx.text("No windows found for this label.", size="3"),
            ),
            rx.text("Select a label to view windows.", size="3"),
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def examine() -> rx.Component:
    """Main examine page component."""
    return rx.container(
        rx.hstack(
            # Left column: Labels (1/4 width)
            rx.box(
                labels_panel(),
                flex="1",
                min_width="250px",
                height="fit-content",
            ),
            # Right column: Recordings (3/4 width)
            rx.box(
                windows_panel(),
                flex="3",
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
        width="100%",
    )
