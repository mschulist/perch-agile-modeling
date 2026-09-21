"""Browse and re-label the windows annotated with a given label."""

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


class ExamineView:
    """Label list on the left, a page of windows on the right.

    Window ids for a label are fetched once (a single query returning ints);
    only the ids on the current page get their metadata and assets loaded.
    """

    def __init__(self, services: ProjectServices):
        self.services = services
        self.all_labels: list[str] = []
        self.selected_label: str | None = None
        self.window_ids: list[int] = []
        self.page = 1

    # --- Data ----------------------------------------------------------

    def _load_labels(self) -> list[str]:
        return list(
            self.services.hoplite_db.get_all_labels(
                label_type=datatypes.LabelType.POSITIVE
            )
        )

    def _load_window_ids(self, label: str) -> list[int]:
        return examine_annotations.get_window_ids_by_label(
            self.services.hoplite_db, label
        )

    def _load_page(self, window_ids: list[int]) -> list[WindowView]:
        return build_views(self.services, window_ids)

    def _save(self, window_id: int, labels: list[str]) -> None:
        examine_annotations.update_labels(
            config=self.services.config,
            hoplite_db=self.services.hoplite_db,
            window_id=window_id,
            new_labels=labels,
        )

    # --- UI ------------------------------------------------------------

    async def build(self) -> None:
        with (
            page_layout("Examine"),
            ui.row().classes("w-full gap-6 items-start no-wrap"),
        ):
            self.left = ui.column().classes("w-[300px] shrink-0 gap-2")
            self.right = ui.column().classes("grow gap-4 min-w-0")

        with self.left:
            spinner = loading("Loading labels...")
        self.all_labels = await io_bound(self._load_labels)
        spinner.delete()
        self._render_labels()

        with self.right:
            ui.label("Select a label to view windows.").classes("text-gray-500")

    def _render_labels(self) -> None:
        self.left.clear()
        with self.left:
            ui.label("Labels").classes("text-2xl font-bold")
            searchable_list(
                self.all_labels,
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
        self.window_ids = await io_bound(self._load_window_ids, self.selected_label)
        spinner.delete()
        await self._render_page()

    async def _render_page(self) -> None:
        self.right.clear()
        label = self.selected_label
        total = len(self.window_ids)
        pages = max(1, -(-total // PAGE_SIZE))
        self.page = min(self.page, pages)
        start = (self.page - 1) * PAGE_SIZE
        page_ids = self.window_ids[start : start + PAGE_SIZE]

        with self.right:
            ui.label(f"Windows: ({label})").classes("text-2xl font-bold")
            if total == 0:
                ui.label("No windows found for this label.")
                return
            ui.label(f"Showing {start + 1}-{start + len(page_ids)} of {total}").classes(
                "text-sm text-gray-500"
            )
            spinner = loading("Loading windows...")

        views = await io_bound(self._load_page, page_ids)
        spinner.delete()

        with self.right:
            for view in views:
                WindowCard(view, self.all_labels, self._on_save)
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
            if label not in self.all_labels:
                self.all_labels.append(label)
                self.all_labels.sort()
        # The window may no longer belong under the label being browsed.
        if self.selected_label is not None and self.selected_label not in labels:
            self.window_ids = [wid for wid in self.window_ids if wid != window_id]
            await self._render_page()


async def examine_page() -> None:
    await ExamineView(project()).build()
