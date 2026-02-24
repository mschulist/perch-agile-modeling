from dataclasses import dataclass
import reflex as rx
from typing import Optional
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.db import db
from perch_analyzer.examine import audio_windows, examine_annotations
from perch_hoplite.db import interface
from pathlib import Path
import os
from ml_collections import config_dict
import logging

logger = logging.getLogger(__name__)


@dataclass
class WindowWithClassifierOutput:
    window_id: int
    filename: str
    offsets: list[float]
    ann_labels: list[str]
    label: str
    logit: float
    spec_file: str
    audio_file: str


class ClassifierOutputState(ConfigState):
    """State management for the classifier output page."""

    # Search and filter state
    search_query: str = ""
    all_labels: list[str] = []
    filtered_labels: list[str] = []
    selected_label: Optional[str] = None

    # Windows display state
    windows: list[WindowWithClassifierOutput] = []
    all_windows: list[WindowWithClassifierOutput] = []

    # Edit state for each recording (using window_id as key)
    editing_window_id: Optional[int] = None
    edit_labels: list[str] = []
    label_search: str = ""
    filtered_label_suggestions: list[str] = []

    @rx.var
    def classifier_output_id(self) -> str:
        """Get the classifier output ID from the URL route parameter."""
        return self.router.page.params.get("id", "")

    def _get_classifier_output(self) -> db.ClassifierOutput | None:
        """Helper method to get the classifier output object from the database."""
        if not self.classifier_output_id:
            return None

        analyzer_db = self.get_analyzer_db()
        try:
            return analyzer_db.get_classifier_output(int(self.classifier_output_id))
        except Exception as e:
            logger.error(f"Error loading classifier output: {e}")
            return None

    def _get_classifier(self) -> db.Classifier | None:
        classifier_output = self._get_classifier_output()
        if not classifier_output:
            return None

        analyzer_db = self.get_analyzer_db()
        return analyzer_db.get_classifier(classifier_output.classifier_id)

    @rx.var
    def classifier_name(self) -> str:
        """Get a display name for the classifier."""
        classifier = self._get_classifier()
        if not classifier:
            return "Unknown"
        return f"Classifier {classifier.id} ({classifier.datetime.strftime('%Y-%m-%d %H:%M')})"

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
        self.load_classifier_output_windows()
        self.load_labels()

    @rx.event
    def load_labels(self):
        """Load all labels from both classifier outputs and hoplite database."""
        hoplite_db = self.get_hoplite_db().thread_split()
        analyzer_db = self.get_analyzer_db()

        # Get annotated labels from hoplite
        hoplite_labels = set(
            hoplite_db.get_all_labels(label_type=interface.LabelType.POSITIVE)
        )

        # Get classifier output labels from analyzer db
        classifier_labels = set()
        if self.classifier_output_id:
            try:
                classifier_output_windows = (
                    analyzer_db.get_all_classifier_output_windows(
                        classifier_output_id=int(self.classifier_output_id)
                    )
                )
                classifier_labels = {cow.label for cow in classifier_output_windows}
            except Exception as e:
                logger.error(f"Error loading classifier labels: {e}")

        # Combine both label sets
        all_labels_set = hoplite_labels | classifier_labels
        self.all_labels = sorted(list(all_labels_set))
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
            self.filter_windows_by_label(label)

    @rx.event
    def filter_windows_by_label(self, label: str):
        """Filter windows to show only those with the selected label (just classifier label)"""
        self.windows = [window for window in self.all_windows if label == window.label]

    @rx.event
    def load_classifier_output_windows(self):
        """Load all classifier output windows for the selected classifier output."""
        if not self.classifier_output_id:
            return

        analyzer_db = self.get_analyzer_db()
        hoplite_db = self.get_hoplite_db().thread_split()

        try:
            # Get all classifier output windows for this classifier output
            classifier_output_windows = analyzer_db.get_all_classifier_output_windows(
                classifier_output_id=int(self.classifier_output_id)
            )

            windows_with_metadata: list[WindowWithClassifierOutput] = []
            for cow in classifier_output_windows:
                # Get window and recording information from hoplite
                window = hoplite_db.get_window(cow.window_id)
                recording = hoplite_db.get_recording(window.recording_id)

                # Get window labels from hoplite (same as examine page)
                annotations = hoplite_db.get_all_annotations(
                    config_dict.create(
                        eq=dict(recording_id=window.recording_id),
                        approx=dict(offsets=window.offsets),
                    )
                )
                labels_list = [ann.label for ann in annotations]

                # Get audio and spectrogram paths
                recording_file, spec_file = audio_windows.get_audio_window_path(
                    config=self.config,
                    hoplite_db=hoplite_db,
                    window_id=cow.window_id,
                )

                # Convert absolute paths to backend URLs
                backend_host = os.getenv("BACKEND_HOST", "localhost")
                backend_port = os.getenv("BACKEND_PORT", "8000")
                backend_url = f"http://{backend_host}:{backend_port}"

                # Compute paths using /data prefix
                data_path = Path(self.config.data_path)
                spec_relative = "/data/" + str(spec_file.relative_to(data_path))
                audio_relative = "/data/" + str(recording_file.relative_to(data_path))

                spec_url = f"{backend_url}{spec_relative}"
                audio_url = f"{backend_url}{audio_relative}"

                windows_with_metadata.append(
                    WindowWithClassifierOutput(
                        window_id=cow.window_id,
                        filename=recording.filename,
                        offsets=window.offsets,
                        ann_labels=labels_list,
                        label=cow.label,
                        logit=cow.logit,
                        spec_file=spec_url,
                        audio_file=audio_url,
                    )
                )

            self.all_windows = windows_with_metadata
            self.windows = []  # Start with no windows displayed until label is selected
        except Exception as e:
            logger.error(f"Error loading classifier output windows: {e}")
            self.all_windows = []
            self.windows = []

    @rx.event
    def start_editing_by_index(self, index: int):
        """Start editing labels for a recording by its index."""
        if 0 <= index < len(self.windows):
            window = self.windows[index]
            self.editing_window_id = window.window_id
            self.edit_labels = window.ann_labels.copy()

    @rx.event
    def cancel_editing(self):
        """Cancel editing labels."""
        self.editing_window_id = None
        self.edit_labels = []

    @rx.event
    def save_current_labels(self):
        """Save edited labels to database."""
        if self.editing_window_id is None:
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

        # Update the window in both lists
        for window in self.all_windows:
            if window.window_id == self.editing_window_id:
                window.ann_labels = self.edit_labels.copy()
                break

        for window in self.windows:
            if window.window_id == self.editing_window_id:
                window.ann_labels = self.edit_labels.copy()
                break

        # Check if the current selected label was removed
        # (only if it was an annotated label, not the classifier label)
        if self.selected_label and self.selected_label not in self.edit_labels:
            # Need to check if it's still the classifier label
            should_remove = True
            for window in self.windows:
                if window.window_id == self.editing_window_id:
                    if window.label == self.selected_label:
                        should_remove = False
                    break

            if should_remove:
                # Remove this window from the filtered display
                self.windows = [
                    window
                    for window in self.windows
                    if window.window_id != self.editing_window_id
                ]

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
                value=ClassifierOutputState.label_search,
                on_change=ClassifierOutputState.update_label_search,
                width="100%",
                size="2",
            ),
            rx.button(
                "Add",
                on_click=ClassifierOutputState.add_current_search_as_label,
                disabled=ClassifierOutputState.label_search == "",
                size="2",
                variant="solid",
            ),
            spacing="2",
            width="100%",
        ),
        # Dropdown suggestions
        rx.cond(
            ClassifierOutputState.filtered_label_suggestions.length() > 0,
            rx.box(
                rx.vstack(
                    rx.foreach(
                        ClassifierOutputState.filtered_label_suggestions,
                        lambda label: rx.box(
                            rx.text(label, size="2"),
                            padding="0.5em",
                            border_radius="0.25em",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=lambda: ClassifierOutputState.add_label(label),
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
            ClassifierOutputState.edit_labels.length() > 0,
            rx.box(
                rx.foreach(
                    ClassifierOutputState.edit_labels,
                    lambda label: rx.badge(
                        rx.hstack(
                            rx.text(label, size="2"),
                            rx.icon(
                                "x",
                                size=14,
                                cursor="pointer",
                                on_click=lambda: (
                                    ClassifierOutputState.remove_edit_label(label)
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


def search_box() -> rx.Component:
    """Search box component for filtering labels."""
    return rx.input(
        placeholder="Search labels...",
        value=ClassifierOutputState.search_query,
        on_change=ClassifierOutputState.update_search_query,
        width="100%",
    )


def labels_panel() -> rx.Component:
    """Left panel showing searchable list of labels."""
    return rx.vstack(
        rx.heading("Labels", size="6"),
        search_box(),
        rx.box(
            rx.cond(
                ClassifierOutputState.filtered_labels,
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ClassifierOutputState.filtered_labels.length()),  # type: ignore
                        lambda i: rx.box(
                            rx.text(ClassifierOutputState.filtered_labels[i], size="3"),
                            padding="0.75em",
                            border_radius="0.5em",
                            width="100%",
                            _hover={
                                "background_color": rx.color("accent", 3),
                                "cursor": "pointer",
                            },
                            on_click=ClassifierOutputState.select_label_by_index(i),  # type: ignore
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


def window_card(window: WindowWithClassifierOutput, index: int) -> rx.Component:
    """Card component for displaying a single classifier output window."""
    return rx.card(
        rx.vstack(
            # Header with filename
            rx.heading(window.filename, size="5"),
            # Window information
            rx.vstack(
                rx.text(
                    f"Offset: {window.offsets[0]:.2f}s",
                    size="2",
                    weight="bold",
                ),
                rx.text(
                    f"Classifier Label: {window.label}",
                    size="2",
                    weight="bold",
                ),
                rx.text(
                    f"Logit: {window.logit:.4f}",
                    size="2",
                    weight="bold",
                ),
                rx.text(
                    f"Annotated Labels: {window.ann_labels}",
                    size="2",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            # Edit button (only show when not editing this recording)
            rx.cond(
                ClassifierOutputState.editing_window_id != window.window_id,
                rx.button(
                    "Edit Labels",
                    on_click=ClassifierOutputState.start_editing_by_index(index),
                    variant="outline",
                    size="2",
                    cursor="pointer",
                ),
                # Edit section (show when editing this recording)
                rx.cond(
                    ClassifierOutputState.editing_window_id == window.window_id,
                    rx.vstack(
                        label_multiselect(),
                        rx.hstack(
                            rx.button(
                                "Save",
                                on_click=ClassifierOutputState.save_current_labels,
                                variant="solid",
                                size="2",
                                cursor="pointer",
                            ),
                            rx.button(
                                "Cancel",
                                on_click=ClassifierOutputState.cancel_editing,
                                variant="outline",
                                size="2",
                                cursor="pointer",
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
    """Right panel showing windows for selected label."""
    return rx.vstack(
        rx.heading(
            rx.cond(
                ClassifierOutputState.selected_label,
                f"Windows: ({ClassifierOutputState.selected_label})",
                "Windows",
            ),
            size="6",
        ),
        rx.cond(
            ClassifierOutputState.selected_label,
            rx.cond(
                ClassifierOutputState.windows.length() > 0,  # type: ignore
                rx.vstack(
                    rx.foreach(
                        rx.Var.range(ClassifierOutputState.windows.length()),  # type: ignore
                        lambda i: window_card(ClassifierOutputState.windows[i], i),
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


def classifier_output_page() -> rx.Component:
    """Main classifier output page component."""
    return rx.container(
        rx.vstack(
            rx.heading(
                f"Classifier Output ID: {ClassifierOutputState.classifier_output_id}",
                size="8",
            ),
            rx.text(
                f"Classifier: {ClassifierOutputState.classifier_name}",
                size="4",
                weight="medium",
            ),
            rx.hstack(
                # Left column: Labels (1/4 width)
                rx.box(
                    labels_panel(),
                    flex="1",
                    min_width="250px",
                    height="fit-content",
                ),
                # Right column: Windows (3/4 width)
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
            spacing="4",
            width="100%",
        ),
        on_mount=ClassifierOutputState.on_mount_handler,
        size="4",
        padding="2em",
        width="100%",
    )
