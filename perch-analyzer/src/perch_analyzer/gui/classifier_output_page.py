"""Review the windows a classifier run picked out, label by label."""

import logging

from nicegui import ui
from nicegui.events import ValueChangeEventArguments
from perch_hoplite.db import datatypes

from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.background import load, run_blocking
from perch_analyzer.gui.components import (
    SearchableList,
    WindowCard,
    loading,
    page_layout,
    wait_for_client,
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
        self._updating_pager = False

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
                with ui.column().classes("w-[300px] shrink-0 gap-2"):
                    ui.label("Labels").classes("text-2xl font-bold")
                    self.labels_slot = ui.column().classes("w-full")
                with ui.column().classes("grow gap-4 min-w-0"):
                    self.heading = ui.label("Windows").classes("text-2xl font-bold")
                    self.status = ui.label("Select a label to view windows.").classes(
                        "text-sm text-gray-500"
                    )
                    self.cards_slot = ui.column().classes("w-full gap-4")
                    self.pager = ui.pagination(
                        1,
                        1,
                        value=1,
                        direction_links=True,
                        on_change=self._on_page_change,
                    ).classes("self-center")
                    self.pager.visible = False

        # Hand the shell to the browser before the databases get touched.
        await wait_for_client()

        with self.labels_slot:
            spinner = loading("Loading labels...")
        header, self.output_labels, self.editor_labels = await load(self._load_header)
        spinner.delete()

        self.subtitle.text = f"Classifier: {header}"
        with self.labels_slot:
            self.label_list = SearchableList(self.output_labels, self._on_select_label)
        if not self.output_labels:
            self.status.text = (
                "No gathered windows yet. Use "
                "`perch-analyzer gather_classifier_outputs` to sample some."
            )

    async def _on_select_label(self, label: str) -> None:
        self.selected_label = label
        self.page = 1
        self.label_list.set_selected(label)
        self.heading.text = f"Windows: ({label})"
        self.status.text = "Loading windows..."

        self.cards_slot.clear()
        with self.cards_slot:
            spinner = loading("Loading windows...")
        self.window_ids, self.logits = await load(self._load_windows_for_label, label)
        spinner.delete()
        await self._render_page()

    async def _render_page(self) -> None:
        total = len(self.window_ids)
        pages = max(1, -(-total // PAGE_SIZE))
        self.page = min(self.page, pages)
        start = (self.page - 1) * PAGE_SIZE
        page_ids = self.window_ids[start : start + PAGE_SIZE]

        self._set_pager(pages)

        if total == 0:
            self.status.text = "No windows found for this label."
            self.cards_slot.clear()
            return

        self.status.text = (
            f"Showing {start + 1}-{start + len(page_ids)} of {total}, "
            "highest logit first"
        )
        self.cards_slot.clear()
        with self.cards_slot:
            spinner = loading("Loading windows...")
        views = await load(self._load_page, page_ids)
        spinner.delete()

        with self.cards_slot:
            for view in views:
                WindowCard(view, self.editor_labels, self._on_save)

    def _set_pager(self, pages: int) -> None:
        """Resize the pager in place; recreating it would delete the widget
        whose change handler is running."""
        self.pager.props(f"max={pages}")
        self.pager.visible = pages > 1
        if self.pager.value != self.page:
            self._updating_pager = True
            try:
                self.pager.value = self.page
            finally:
                self._updating_pager = False

    async def _on_page_change(
        self, event: ValueChangeEventArguments[int | None]
    ) -> None:
        if self._updating_pager or not event.value or event.value == self.page:
            return
        self.page = event.value
        await self._render_page()

    async def _on_save(self, window_id: int, labels: list[str]) -> None:
        await run_blocking(self._save, window_id, labels)
        ui.notify("Saved labels", type="positive")
        for label in labels:
            if label not in self.editor_labels:
                self.editor_labels.append(label)
                self.editor_labels.sort()


async def classifier_output_page(output_id: int) -> None:
    await ClassifierOutputView(project(), output_id).build()
