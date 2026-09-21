"""Review the windows a classifier run picked out, label by label."""

import logging

from nicegui import run, ui
from nicegui.events import ValueChangeEventArguments
from perch_hoplite.db import datatypes

from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.background import io_bound
from perch_analyzer.gui.components import (
    WindowCard,
    loading,
    page_layout,
    searchable_list,
)
from perch_analyzer.gui.services import ProjectServices, project
from perch_analyzer.gui.views import WindowView, build_views

logger = logging.getLogger(__name__)

PAGE_SIZE = 10


class ClassifierOutputView:
    """Only the selected label's windows are loaded.

    The Reflex version loaded and rendered every window in the output on
    mount, including its spectrogram and audio, before a label was picked.
    """

    def __init__(self, services: ProjectServices, output_id: int):
        self.services = services
        self.output_id = output_id
        self.output_labels: list[str] = []
        self.editor_labels: list[str] = []
        self.selected_label: str | None = None
        self.window_ids: list[int] = []
        self.logits: dict[int, tuple[str, float]] = {}
        self.page = 1
        self.header = ""

    # --- Data ----------------------------------------------------------

    def _load_header(self) -> tuple[str, list[str], list[str]]:
        analyzer_db = self.services.analyzer_db
        try:
            output = analyzer_db.get_classifier_output(self.output_id)
            classifier = analyzer_db.get_classifier_info(output.classifier_id)
            header = (
                f"Classifier {classifier.id} "
                f"({classifier.datetime.strftime('%Y-%m-%d %H:%M')})"
            )
        except Exception:
            logger.exception("could not load classifier output %s", self.output_id)
            header = "Unknown"

        output_labels = analyzer_db.get_classifier_output_labels(self.output_id)
        hoplite_labels = self.services.hoplite_db.get_all_labels(
            label_type=datatypes.LabelType.POSITIVE
        )
        editor_labels = sorted({*hoplite_labels, *output_labels})
        return header, output_labels, editor_labels

    def _load_windows_for_label(
        self, label: str
    ) -> tuple[list[int], dict[int, tuple[str, float]]]:
        rows = self.services.analyzer_db.get_all_classifier_output_windows(
            classifier_output_id=self.output_id, label=label
        )
        rows.sort(key=lambda row: row.logit, reverse=True)
        window_ids = [row.window_id for row in rows]
        logits = {row.window_id: (row.label, row.logit) for row in rows}
        return window_ids, logits

    def _load_page(self, window_ids: list[int]) -> list[WindowView]:
        return build_views(self.services, window_ids, classifier_labels=self.logits)

    def _save(self, window_id: int, labels: list[str]) -> None:
        examine_annotations.update_labels(
            config=self.services.config,
            hoplite_db=self.services.hoplite_db,
            window_id=window_id,
            new_labels=labels,
        )

    # --- UI ------------------------------------------------------------

    async def build(self) -> None:
        with page_layout(f"Classifier Output ID: {self.output_id}"):
            self.subtitle = ui.label().classes("text-lg")
            with ui.row().classes("w-full gap-6 items-start no-wrap"):
                self.left = ui.column().classes("w-[300px] shrink-0 gap-2")
                self.right = ui.column().classes("grow gap-4 min-w-0")

        with self.left:
            spinner = loading("Loading labels...")
        (
            self.header,
            self.output_labels,
            self.editor_labels,
        ) = await io_bound(self._load_header)
        spinner.delete()

        self.subtitle.text = f"Classifier: {self.header}"
        self._render_labels()
        with self.right:
            if self.output_labels:
                ui.label("Select a label to view windows.").classes("text-gray-500")
            else:
                ui.label(
                    "No gathered windows yet. Use "
                    "`perch-analyzer gather_classifier_outputs` to sample some."
                ).classes("text-gray-500")

    def _render_labels(self) -> None:
        self.left.clear()
        with self.left:
            ui.label("Labels").classes("text-2xl font-bold")
            searchable_list(
                self.output_labels,
                self._on_select_label,
                selected=self.selected_label,
            )

    def _on_select_label(self, label: str) -> None:
        self.selected_label = label
        self.page = 1
        self._render_labels()
        ui.timer(0, self._load_and_render, once=True)

    async def _load_and_render(self) -> None:
        assert self.selected_label is not None
        self.right.clear()
        with self.right:
            spinner = loading("Loading windows...")
        self.window_ids, self.logits = await io_bound(
            self._load_windows_for_label, self.selected_label
        )
        spinner.delete()
        await self._render_page()

    async def _render_page(self) -> None:
        self.right.clear()
        total = len(self.window_ids)
        pages = max(1, -(-total // PAGE_SIZE))
        self.page = min(self.page, pages)
        start = (self.page - 1) * PAGE_SIZE
        page_ids = self.window_ids[start : start + PAGE_SIZE]

        with self.right:
            ui.label(f"Windows: ({self.selected_label})").classes("text-2xl font-bold")
            if total == 0:
                ui.label("No windows found for this label.")
                return
            ui.label(
                f"Showing {start + 1}-{start + len(page_ids)} of {total}, "
                "highest logit first"
            ).classes("text-sm text-gray-500")
            spinner = loading("Loading windows...")

        views = await io_bound(self._load_page, page_ids)
        spinner.delete()

        with self.right:
            for view in views:
                WindowCard(view, self.editor_labels, self._on_save)
            if pages > 1:
                ui.pagination(
                    1,
                    pages,
                    value=self.page,
                    direction_links=True,
                    on_change=self._on_page_change,
                ).classes("self-center")

    def _on_page_change(self, event: ValueChangeEventArguments[int | None]) -> None:
        if event.value and event.value != self.page:
            self.page = event.value
            ui.timer(0, self._render_page, once=True)

    async def _on_save(self, window_id: int, labels: list[str]) -> None:
        await run.io_bound(self._save, window_id, labels)
        ui.notify("Saved labels", type="positive")
        for label in labels:
            if label not in self.editor_labels:
                self.editor_labels.append(label)
                self.editor_labels.sort()


async def classifier_output_page(output_id: int) -> None:
    await ClassifierOutputView(project(), output_id).build()
