"""List of trained classifiers."""

from collections.abc import Mapping
from typing import Any

from nicegui import ui

from perch_analyzer.db import db
from perch_analyzer.gui.background import io_bound
from perch_analyzer.gui.components import loading, page_layout
from perch_analyzer.gui.format import format_metric
from perch_analyzer.gui.services import ProjectServices, project

METRIC_LABELS = (
    ("roc_auc", "AUC-ROC"),
    ("cmap", "CMAP"),
    ("top1_acc", "Top-1 Accuracy"),
)


def _load(services: ProjectServices) -> list[db.ClassifierInfo]:
    return services.analyzer_db.get_all_classifiers()


async def classifiers_page() -> None:
    services = project()
    with page_layout("Trained Classifiers"):
        spinner = loading()
        body = ui.column().classes("w-full gap-3")

        classifiers = await io_bound(_load, services)
        spinner.delete()

        with body:
            if not classifiers:
                ui.label(
                    "No classifiers found. Train a classifier to see it here."
                ).classes("italic text-gray-500")
                return
            for classifier in classifiers:
                classifier_card(classifier)


def classifier_card(classifier: db.ClassifierInfo) -> None:
    with (
        ui.card()
        .classes("w-full cursor-pointer hover:bg-gray-100")
        .on(
            "click",
            lambda cid=classifier.id: ui.navigate.to(f"/single_classifier/{cid}"),
        ),
        ui.row().classes("w-full gap-12 items-start"),
    ):
        with ui.column().classes("gap-1"):
            ui.label(f"Classifier id: {classifier.id}").classes("text-xl font-semibold")
            ui.label(classifier.datetime.strftime("%B %d, %Y at %I:%M %p")).classes(
                "italic text-gray-600"
            )
        metrics_row(classifier.metrics)


def metrics_row(metrics: Mapping[str, Any]) -> None:
    with ui.row().classes("gap-10"):
        for key, title in METRIC_LABELS:
            with ui.column().classes("items-center gap-0"):
                ui.label(title).classes("font-bold text-sm")
                ui.label(format_metric(metrics, key)).classes("text-3xl")
