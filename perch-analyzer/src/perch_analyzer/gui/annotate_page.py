"""Work through the windows that a search marked as possible examples."""

import logging
from dataclasses import dataclass

from ml_collections import config_dict
from nicegui import run, ui
from perch_hoplite.db import datatypes

from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.background import io_bound
from perch_analyzer.gui.components import (
    label_editor,
    loading,
    page_layout,
    window_media,
)
from perch_analyzer.gui.services import ProjectServices, project
from perch_analyzer.gui.views import WindowView, build_views

logger = logging.getLogger(__name__)


@dataclass
class NextWindow:
    """The next uncertain annotation to review, if there is one."""

    annotation_id: int | None = None
    target_label: str = ""
    remaining: int = 0
    view: WindowView | None = None
    error: str | None = None


class AnnotateView:
    def __init__(self, services: ProjectServices):
        self.services = services
        self.all_labels: list[str] = []
        self.current = NextWindow()

    # --- Data ----------------------------------------------------------

    def _uncertain_annotations(self):
        return self.services.hoplite_db.get_all_annotations(
            config_dict.create(eq=dict(label_type=datatypes.LabelType.UNCERTAIN))
        )

    def _load_next(self) -> NextWindow:
        hoplite_db = self.services.hoplite_db
        annotations = self._uncertain_annotations()
        if not annotations:
            return NextWindow(remaining=0)

        annotation = annotations[0]
        windows = hoplite_db.get_all_windows(
            filter=config_dict.create(
                eq=dict(recording_id=annotation.recording_id),
                approx=dict(offsets=annotation.offsets),
            )
        )
        if not windows:
            return NextWindow(
                annotation_id=annotation.id,
                target_label=annotation.label,
                remaining=len(annotations),
                error=(
                    f"Annotation {annotation.id} ({annotation.label}) has no "
                    "matching window in the database."
                ),
            )
        if len(windows) > 1:
            logger.warning(
                "expected 1 window for annotation %s, got %d; using the first",
                annotation.id,
                len(windows),
            )

        self.all_labels = list(hoplite_db.get_all_labels())
        views = build_views(self.services, [windows[0].id])
        return NextWindow(
            annotation_id=annotation.id,
            target_label=annotation.label,
            remaining=len(annotations),
            view=views[0] if views else None,
        )

    def _submit(self, annotation_id: int, window_id: int, labels: list[str]) -> None:
        hoplite_db = self.services.hoplite_db
        # Clear the "possible example" marker whether or not it is confirmed.
        if hoplite_db.get_annotation(annotation_id):
            hoplite_db.remove_annotation(annotation_id)
        if labels:
            examine_annotations.update_labels(
                config=self.services.config,
                hoplite_db=hoplite_db,
                window_id=window_id,
                new_labels=labels,
            )
        hoplite_db.commit()

    # --- UI ------------------------------------------------------------

    async def build(self) -> None:
        with page_layout("Annotate"):
            self.body = ui.column().classes("w-full gap-4")
        await self._load_and_render()

    async def _load_and_render(self) -> None:
        self.body.clear()
        with self.body:
            spinner = loading("Finding the next window...")
        self.current = await io_bound(self._load_next)
        spinner.delete()
        self._render()

    def _render(self) -> None:
        current = self.current
        self.body.clear()
        with self.body:
            if current.error:
                ui.label(current.error).classes("text-red-600")
                return
            if current.view is None:
                ui.label("No more windows to annotate!").classes("text-3xl font-bold")
                ui.label("All search results have been reviewed.").classes(
                    "text-gray-500"
                )
                return

            ui.label(f"{current.remaining} possible example(s) left").classes(
                "text-sm text-gray-500"
            )

            with ui.row().classes("w-full gap-8 items-start no-wrap"):
                with ui.column().classes("w-[360px] shrink-0 gap-3"):
                    ui.label("Annotation Info").classes("text-2xl font-bold")
                    ui.label(f"Filename: {current.view.filename}").classes(
                        "font-medium"
                    )
                    ui.label(f"Target Label: {current.target_label}").classes(
                        "font-medium"
                    )
                    ui.label(f"Offsets: {current.view.offsets_label}")
                    ui.separator()
                    ui.label("Add every species vocalizing in this window.").classes(
                        "text-sm text-gray-500"
                    )
                    self.select = label_editor(self.all_labels, [])
                    ui.button("Submit annotations", on_click=self._on_submit).props(
                        "no-caps"
                    )

                with ui.column().classes("grow gap-3 min-w-0 items-center"):
                    ui.label("Window").classes("text-2xl font-bold self-start")
                    window_media(current.view.spec_url, current.view.audio_url)

    async def _on_submit(self) -> None:
        current = self.current
        if current.view is None or current.annotation_id is None:
            return
        labels = sorted(self.select.value or [])
        await run.io_bound(
            self._submit, current.annotation_id, current.view.window_id, labels
        )
        await self._load_and_render()


async def annotate_page() -> None:
    await AnnotateView(project()).build()
