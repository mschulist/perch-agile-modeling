"""Browse and re-label the windows annotated with a given label."""

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


class ExamineView:
    """Label list on the left, a page of windows on the right.

    Window ids for a label are fetched once (a single query returning ints);
    only the ids on the current page get their metadata and assets loaded.

    The right-hand panel is split into containers that are created once and
    then refilled. Clearing a container that holds the widget whose handler is
    running would delete that widget mid-event.
    """

    def __init__(self, services: ProjectServices):
        self.services = services
        self.all_labels: list[str] = []
        self.selected_label: str | None = None
        self.window_ids: list[int] = []
        self.cards: list[WindowCard] = []
        self.page = 1
        self._updating_pager = False

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
                    1, 1, value=1, direction_links=True, on_change=self._on_page_change
                ).classes("self-center")
                self.pager.visible = False

        # Let the browser have the shell before doing anything slow: this both
        # shows the spinner and takes the work out of the page's
        # response_timeout budget.
        await wait_for_client()

        with self.labels_slot:
            spinner = loading("Loading labels...")
        self.all_labels = await load(self._load_labels)
        spinner.delete()

        with self.labels_slot:
            self.label_list = SearchableList(self.all_labels, self._on_select_label)

    async def _on_select_label(self, label: str) -> None:
        self.selected_label = label
        self.page = 1
        self.label_list.set_selected(label)
        self.heading.text = f"Windows: ({label})"
        self.status.text = "Loading windows..."

        self.cards_slot.clear()
        with self.cards_slot:
            spinner = loading("Loading windows...")
        self.window_ids = await load(self._load_window_ids, label)
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

        self.status.text = f"Showing {start + 1}-{start + len(page_ids)} of {total}"
        self.cards_slot.clear()
        with self.cards_slot:
            spinner = loading("Loading windows...")
        views = await load(self._load_page, page_ids)
        spinner.delete()

        self.cards = []
        with self.cards_slot:
            for view in views:
                self.cards.append(WindowCard(view, self.all_labels, self._on_save))

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
            if label not in self.all_labels:
                self.all_labels.append(label)
                self.all_labels.sort()
                self.label_list.set_items(self.all_labels)
        # The window may no longer belong under the label being browsed. Hide
        # its card rather than re-rendering the page: this runs inside that
        # card's own save handler.
        if self.selected_label is not None and self.selected_label not in labels:
            self.window_ids = [wid for wid in self.window_ids if wid != window_id]
            for card in self.cards:
                if card.view.window_id == window_id:
                    card.hide()
            self.status.text = (
                f"{len(self.window_ids)} window(s) left under "
                f"{self.selected_label}; reload the label to refresh the page."
            )


async def examine_page() -> None:
    await ExamineView(project()).build()
