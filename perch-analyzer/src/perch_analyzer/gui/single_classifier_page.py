"""Detail view for one classifier: hyperparameters, metrics and its runs."""

from nicegui import ui

from perch_analyzer.db import db
from perch_analyzer.gui.background import load
from perch_analyzer.gui.classifiers_page import metrics_row
from perch_analyzer.gui.components import loading, page_layout, wait_for_client
from perch_analyzer.gui.services import ProjectServices, project


def _load(
    services: ProjectServices, classifier_id: int
) -> tuple[db.ClassifierInfo | None, list[db.ClassifierOutput]]:
    """Read the classifier and its outputs in one trip.

    The Reflex version reloaded the classifier from disk once per displayed
    field; this reads it once, and never loads its weights at all.
    """
    analyzer_db = services.analyzer_db
    try:
        classifier = analyzer_db.get_classifier_info(classifier_id)
    except Exception:
        return None, []
    return classifier, analyzer_db.get_all_classifier_outputs(classifier_id)


async def single_classifier_page(classifier_id: int) -> None:
    services = project()
    with page_layout():
        spinner = loading()
        body = ui.column().classes("w-full gap-4")

    await wait_for_client()
    classifier, outputs = await load(_load, services, classifier_id)
    spinner.delete()

    with body:
        if classifier is None:
            ui.label(f"No classifier found with id: {classifier_id}").classes(
                "text-2xl font-bold"
            )
            return

        with ui.row().classes("items-baseline gap-3"):
            ui.label(f"Classifier id: {classifier.id}").classes("text-3xl font-bold")
            ui.label(
                f"({classifier.datetime.strftime('%B %d, %Y at %I:%M %p')})"
            ).classes("text-lg text-gray-600")

        with ui.card().classes("w-full"):
            with ui.row().classes("w-full gap-12 items-start"):
                with ui.column().classes("gap-1"):
                    ui.label("Hyper Parameters").classes("text-xl font-semibold")
                    ui.label(f"Training Ratio: {classifier.train_ratio}")
                    ui.label(f"Number of Training Steps: {classifier.num_train_steps}")
                    ui.label(f"Weak Negative Rate: {classifier.weak_neg_rate}")
                    ui.label(f"Learning Rate: {classifier.learning_rate}")
                with ui.column().classes("gap-1"):
                    ui.label("Performance Metrics").classes("text-xl font-semibold")
                    metrics_row(classifier.metrics)

            ui.label(f"Labels ({len(classifier.labels)})").classes("font-bold")
            with ui.row().classes("gap-1 max-h-[14rem] overflow-y-auto"):
                for label in classifier.labels:
                    ui.chip(label).props("outline dense")

        ui.separator()
        ui.label("Classifier Outputs").classes("text-2xl font-bold")
        if not outputs:
            ui.label(
                "No runs yet. Use `perch-analyzer run_classifier` to make one."
            ).classes("italic text-gray-500")
        for output in outputs:
            with (
                ui.card()
                .classes("w-full cursor-pointer hover:bg-gray-100")
                .on(
                    "click",
                    lambda oid=output.id: ui.navigate.to(f"/classifier_output/{oid}"),
                )
            ):
                ui.label(f"Classifier Output Id: {output.id}").classes(
                    "text-lg font-semibold"
                )
