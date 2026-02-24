import reflex as rx
from perch_hoplite.db import interface
from ml_collections import config_dict
from .state import ConfigState


def render_metadata(
    metadata: config_dict.ConfigDict | dict | list | str, level: int = 0
):
    """Recursively render metadata in a nicely formatted way."""

    # Handle ConfigDict or regular dict
    if isinstance(metadata, (config_dict.ConfigDict, dict)):
        # Skip internal fields that start with underscore
        items_to_render = {k: v for k, v in metadata.items() if not k.startswith("_")}

        if not items_to_render:
            return rx.text("(empty)", color="gray")

        items = []
        for key, value in items_to_render.items():
            # Format the key nicely (replace underscores, capitalize)
            display_key = key.replace("_", " ").title()

            items.append(
                rx.box(
                    rx.hstack(
                        rx.text(
                            f"{display_key}:",
                            weight="bold",
                            color="var(--accent-11)",
                        ),
                        render_metadata(value, level + 1)
                        if not isinstance(value, (dict, config_dict.ConfigDict, list))
                        else rx.text(""),
                        spacing="2",
                    ),
                    rx.box(
                        render_metadata(value, level + 1)
                        if isinstance(value, (dict, config_dict.ConfigDict, list))
                        else rx.text(""),
                        padding_left="4"
                        if isinstance(value, (dict, config_dict.ConfigDict, list))
                        else "0",
                    ),
                    padding_bottom="2",
                )
            )
        return rx.vstack(*items, spacing="1", align_items="start")

    # Handle lists
    elif isinstance(metadata, list):
        if not metadata:
            return rx.text("(empty)", color="gray")

        items = []
        for i, item in enumerate(metadata):
            items.append(
                rx.hstack(
                    rx.text("•", color="var(--accent-9)"),
                    render_metadata(item, level + 1),
                    spacing="2",
                )
            )
        return rx.vstack(*items, spacing="1", align_items="start")

    # Handle primitive values
    else:
        return rx.text(
            str(metadata),
            color="var(--gray-12)",
            size="2",
        )


def summary():
    hoplite_db = ConfigState.get_hoplite_db()
    analyzer_db = ConfigState.get_analyzer_db()

    class_counts = hoplite_db.count_each_label()
    embedding_count = hoplite_db.count_embeddings()
    annotation_count = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.POSITIVE))
        )
    )
    recording_count = len(hoplite_db.get_all_recordings())

    target_recordings_count = analyzer_db.count_target_recordings(True)
    unfinished_target_recordings_count = analyzer_db.count_target_recordings(False)
    annotations_to_be_labeled = len(
        hoplite_db.get_all_annotations(
            filter=config_dict.create(eq=dict(label_type=interface.LabelType.UNCERTAIN))
        )
    )

    hoplite_metadata = hoplite_db.get_metadata(None)

    return rx.center(
        rx.grid(
            rx.vstack(
                rx.heading("Audio Summary", size="9"),
                rx.heading(f"Classes: {len(class_counts)}", size="6"),
                rx.heading(f"Windows: {embedding_count}", size="6"),
                rx.heading(f"Annotations: {annotation_count}", size="6"),
                rx.heading(f"Recordings: {recording_count}", size="6"),
                rx.heading(
                    f"Target recordings: {target_recordings_count} ({unfinished_target_recordings_count} unfinished)",
                    size="6",
                ),
                rx.heading(
                    f"Annotations to be labeled: {annotations_to_be_labeled}", size="6"
                ),
                spacing="4",
                align="center",
            ),
            rx.divider(orientation="vertical"),
            rx.vstack(
                rx.heading("Hoplite DB Metadata", size="9"),
                render_metadata(hoplite_metadata),
                spacing="4",
                align="start",
                width="100%",
                padding_left="1em",
                padding_bottom="4em",
            ),
            columns="3",
            spacing="4",
            width="90%",
            grid_template_columns="1fr auto 1fr",
        )
    )
