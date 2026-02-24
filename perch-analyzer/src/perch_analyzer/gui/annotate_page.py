import reflex as rx
from typing import Optional
from pathlib import Path
import os
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.examine import examine_annotations, audio_windows
from perch_hoplite.db import interface
from ml_collections import config_dict


# Import WindowWithMetadata from examine_page to share the same dataclass
from perch_analyzer.gui.examine_page import WindowWithMetadata


class AnnotateState(ConfigState):
    """State management for the annotate page."""

    # Current window to annotate
    current_window: Optional[WindowWithMetadata] = None
    current_target_label: str = ""
    has_more_windows: bool = True

    # Label selection state
    all_labels: list[str] = []
    selected_labels: list[str] = []
    label_search: str = ""
    filtered_label_suggestions: list[str] = []

    @rx.event
    def on_mount_handler(self):
        """Initialize state when component mounts."""
        self.load_next_window()

    @rx.event
    def load_next_window(self):
        """Load the next window to annotate."""
        hoplite_db = self.get_hoplite_db().thread_split()

        # Get all POSSIBLE annotations
        annotations = hoplite_db.get_all_annotations(
            config_dict.create(eq=dict(label_type=interface.LabelType.UNCERTAIN))
        )

        # Check if there are no more windows
        if len(annotations) == 0:
            self.has_more_windows = False
            self.current_window = None
            return

        # Get the first annotation
        annotation = annotations[0]
        recording = hoplite_db.get_recording(annotation.recording_id)
        windows = hoplite_db.get_all_windows(
            filter=config_dict.create(
                eq=dict(recording_id=recording.id),
                approx=dict(offsets=annotation.offsets),
            )
        )

        if len(windows) != 1:
            raise ValueError(
                f"Expected 1 window, got {len(windows)} with same offsets and recording id"
            )

        window = windows[0]

        # Get audio and spec files
        recording_file, spec_file = audio_windows.get_audio_window_path(
            config=self.config, hoplite_db=hoplite_db, window_id=window.id
        )

        # Convert to backend URLs
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

        # Load all labels
        self.all_labels = list(hoplite_db.get_all_labels())

        # Set current window
        self.current_window = WindowWithMetadata(
            window_id=window.id,
            filename=recording.filename,
            offsets=window.offsets,
            labels=[annotation.label],
            spec_file=spec_url,
            audio_file=audio_url,
        )
        self.current_target_label = annotation.label
        self.selected_labels = []
        self.label_search = ""
        self.filtered_label_suggestions = []

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
                if search_lower in label.lower() and label not in self.selected_labels
            ][:10]  # Limit to 10 suggestions

    @rx.event
    def add_label(self, label: str):
        """Add a label to the selection list."""
        if label and label not in self.selected_labels:
            self.selected_labels = self.selected_labels + [label]
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
    def remove_selected_label(self, label: str):
        """Remove a label from the selection list."""
        self.selected_labels = [lbl for lbl in self.selected_labels if lbl != label]

    @rx.event
    def submit_annotations(self):
        """Submit the annotations and load next window."""
        if not self.current_window:
            return

        hoplite_db = self.get_hoplite_db().thread_split()

        # Get the POSSIBLE annotation to remove
        annotations = hoplite_db.get_all_annotations(
            config_dict.create(eq=dict(label_type=interface.LabelType.UNCERTAIN))
        )

        if annotations:
            # Remove the first POSSIBLE annotation
            first_annotation = annotations[0]
            if hoplite_db.get_annotation(first_annotation.id):
                hoplite_db.remove_annotation(first_annotation.id)

        # Add new annotations with selected labels
        if self.selected_labels:
            examine_annotations.update_labels(
                config=self.config,
                hoplite_db=hoplite_db,
                window_id=self.current_window.window_id,
                new_labels=self.selected_labels,
            )

        hoplite_db.commit()

        # Load next window
        self.load_next_window()


# Reusable Components


def label_multiselect() -> rx.Component:
    """Multiselect component for selecting labels to annotate."""
    return rx.vstack(
        rx.text("Select or create labels:", size="2", weight="bold"),
        # Input field with add button
        rx.hstack(
            rx.input(
                placeholder="Type to search or create...",
                value=AnnotateState.label_search,
                on_change=AnnotateState.update_label_search,
                width="100%",
                size="2",
            ),
            rx.button(
                "Add",
                on_click=AnnotateState.add_current_search_as_label,
                disabled=AnnotateState.label_search == "",
                size="2",
                variant="solid",
            ),
            spacing="2",
            width="100%",
        ),
        # Dropdown suggestions
        rx.cond(
            AnnotateState.filtered_label_suggestions.length() > 0,
            rx.box(
                rx.vstack(
                    rx.foreach(
                        AnnotateState.filtered_label_suggestions,
                        lambda label: rx.box(
                            rx.text(label, size="2"),
                            padding="0.5em",
                            border_radius="0.25em",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=lambda: AnnotateState.add_label(label),
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
            AnnotateState.selected_labels.length() > 0,
            rx.box(
                rx.foreach(
                    AnnotateState.selected_labels,
                    lambda label: rx.badge(
                        rx.hstack(
                            rx.text(label, size="2"),
                            rx.icon(
                                "x",
                                size=14,
                                cursor="pointer",
                                on_click=lambda: AnnotateState.remove_selected_label(
                                    label
                                ),
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


def window_info_panel() -> rx.Component:
    """Left panel showing window information and label selection."""
    return rx.vstack(
        rx.heading("Annotation Info", size="6"),
        rx.vstack(
            rx.text(
                rx.cond(
                    AnnotateState.current_window,
                    f"Filename: {AnnotateState.current_window.filename}",
                    "No window loaded",
                ),
                size="3",
                weight="bold",
            ),
            rx.text(
                rx.cond(
                    AnnotateState.current_window,
                    f"Target Label: {AnnotateState.current_target_label}",
                    "",
                ),
                size="3",
                weight="bold",
            ),
            rx.text(
                rx.cond(
                    AnnotateState.current_window,
                    f"Offsets: {AnnotateState.current_window.offsets[0]:.2f}s - {AnnotateState.current_window.offsets[1]:.2f}s",
                    "",
                ),
                size="2",
            ),
            spacing="2",
            align="start",
            width="100%",
        ),
        rx.divider(),
        label_multiselect(),
        rx.button(
            "Submit Annotations",
            on_click=AnnotateState.submit_annotations,
            variant="solid",
            size="3",
            width="100%",
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def window_display_panel() -> rx.Component:
    """Right panel showing spectrogram and audio player."""
    return rx.vstack(
        rx.heading("Window", size="6"),
        rx.cond(
            AnnotateState.current_window,
            rx.vstack(
                # Spectrogram image
                rx.image(
                    src=AnnotateState.current_window.spec_file,
                    alt="Spectrogram",
                    width="100%",
                    height="auto",
                    max_height="400px",
                    object_fit="contain",
                ),
                # Audio player
                rx.audio(
                    src=AnnotateState.current_window.audio_file,
                    controls=True,
                    width="100%",
                    preload=None,
                ),
                spacing="4",
                width="100%",
            ),
            rx.text("No window to display", size="3", color="gray"),
        ),
        spacing="4",
        width="100%",
        align="start",
    )


def annotate() -> rx.Component:
    """Main annotate page component."""
    return rx.container(
        rx.cond(
            AnnotateState.has_more_windows,
            rx.hstack(
                # Left column: Window info and label selection
                rx.box(
                    window_info_panel(),
                    flex="1",
                    min_width="300px",
                    height="fit-content",
                ),
                # Right column: Spectrogram and audio
                rx.box(
                    window_display_panel(),
                    flex="2",
                    min_width="400px",
                    height="fit-content",
                ),
                spacing="6",
                width="100%",
                align_items="start",
            ),
            rx.vstack(
                rx.heading("No more windows to annotate!", size="7"),
                rx.text(
                    "All search results have been reviewed.",
                    size="4",
                    color="gray",
                ),
                spacing="4",
                align="center",
                width="100%",
                padding="4em",
            ),
        ),
        on_mount=AnnotateState.on_mount_handler,
        size="4",
        padding="2em",
        width="100%",
    )
