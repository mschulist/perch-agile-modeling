import reflex as rx
from perch_analyzer.db import db
from .state import ConfigState


def classifier_card(classifier: db.Classifier) -> rx.Component:
    """Create a card component for a single classifier."""
    formatted_date = classifier.datetime.strftime("%B %d, %Y at %I:%M %p")

    # Extract metrics
    auc_roc = classifier.metrics.get("roc_auc", "N/A")
    cmap = classifier.metrics.get("cmap", "N/A")
    top1_acc = classifier.metrics.get("top1_acc", "N/A")

    # Format metrics with 4 decimal places if they're numeric
    if isinstance(auc_roc, (int, float)):
        auc_roc = f"{auc_roc:.4f}"
    if isinstance(cmap, (int, float)):
        cmap = f"{cmap:.4f}"
    if isinstance(top1_acc, (int, float)):
        top1_acc = f"{top1_acc:.4f}"

    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading(f"Classifier id: {classifier.id}", size="5"),
                rx.text(formatted_date, style={"fontStyle": "italic"}),
                align="start",
                spacing="2",
            ),
            rx.vstack(
                rx.heading("Performance Metrics", size="5"),
                rx.hstack(
                    rx.vstack(
                        rx.text("AUC-ROC", weight="bold"),
                        rx.heading(str(auc_roc), size="7"),
                        align="center",
                    ),
                    rx.vstack(
                        rx.text("CMAP", weight="bold"),
                        rx.heading(str(cmap), size="7"),
                        align="center",
                    ),
                    rx.vstack(
                        rx.text("Top-1 Accuracy", weight="bold"),
                        rx.heading(str(top1_acc), size="7"),
                        align="center",
                    ),
                    spacing="6",
                ),
                align="start",
                spacing="2",
            ),
            spacing="8",
            align="start",
        ),
        padding="1.5em",
        border="1px solid #e0e0e0",
        border_radius="8px",
        margin_bottom="1em",
        width="100%",
        on_click=rx.redirect(f"/single_classifier/{classifier.id}"),
        cursor="pointer",
        transition="background-color 0.3s ease",
        _hover={
            "background_color": "#444444",
        },
    )


def classifiers():
    """Display all trained classifiers with their metrics."""
    analyzer_db = ConfigState.get_analyzer_db()
    all_classifiers = analyzer_db.get_all_classifiers()

    if not all_classifiers:
        content = rx.vstack(
            rx.heading("Trained Classifiers", size="9"),
            rx.text(
                "No classifiers found. Train a classifier to see it here.",
                style={"fontStyle": "italic"},
            ),
            spacing="4",
            align="center",
        )
    else:
        classifier_cards = [
            classifier_card(classifier) for classifier in all_classifiers
        ]
        content = rx.vstack(
            rx.heading("Trained Classifiers", size="9"),
            rx.vstack(
                *classifier_cards,
                spacing="3",
                width="100%",
            ),
            spacing="4",
            align="center",
            width="100%",
        )

    return rx.center(content)
