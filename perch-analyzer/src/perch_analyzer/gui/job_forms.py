"""A form that launches a CLI command as a background job.

The fields come straight from the command's argparse definition
(`cli.command_arguments`), so a flag added to the CLI shows up here without
touching the GUI.
"""

import argparse
import inspect
import logging
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from nicegui import ui
from nicegui.elements.mixins.value_element import ValueElement

from perch_analyzer import cli
from perch_analyzer.gui.services import project
from perch_analyzer.gui.session import require_user
from perch_analyzer.jobs import Job, JobConflictError, JobStatus

logger = logging.getLogger(__name__)

POLL_INTERVAL_S = 1.0

FinishedHandler = Callable[[Job], object]


def _title(action: argparse.Action) -> str:
    title = action.dest.replace("_", " ")
    return f"{title} *" if action.required else title


def _field(
    command: str, action: argparse.Action, options: Sequence[object] | None
) -> ValueElement[Any]:
    """The widget for one argparse option."""
    title = _title(action)
    default = action.default
    element: ValueElement[Any]
    if action.nargs == 0:  # store_true
        element = ui.checkbox(title, value=bool(default))
    elif action.nargs in ("*", "+"):
        element = (
            ui.select(
                options=list(options or []),
                value=list(default or []),
                label=title,
                multiple=True,
                with_input=True,
                new_value_mode="add-unique",
            )
            .props("use-chips dense outlined")
            .classes("w-full")
        )
    elif options is not None or action.choices is not None:
        choices = list(options if options is not None else action.choices or [])
        element = (
            ui.select(
                options=choices,
                value=default if default in choices else None,
                label=title,
                with_input=True,
                clearable=not action.required,
            )
            .props("dense outlined")
            .classes("w-full")
        )
    elif action.type in (int, float):
        element = (
            ui.number(
                title,
                value=default,
                precision=0 if action.type is int else None,
            )
            .props("dense outlined")
            .classes("w-full")
        )
    else:
        element = (
            ui.input(title, value=default or "")
            .props("dense outlined")
            .classes("w-full")
        )
    if action.help:
        element.tooltip(action.help)
    # Marked by bare name and by command, so tests can find a field on a page
    # that holds several forms.
    return element.mark(action.dest, f"{command}.{action.dest}")


class JobForm:
    """Fields for one command, a start button, and the job's status.

    Args:
      command: a `cli.Command` name with `gui=True`.
      fixed: values to pass without showing a field, e.g. the classifier id on
        that classifier's own page.
      options: choices to offer for a field, e.g. existing labels.
      on_finished: called once the job this form started has finished.
    """

    def __init__(
        self,
        command: str,
        *,
        fixed: Mapping[str, object] | None = None,
        options: Mapping[str, Sequence[object]] | None = None,
        submit_label: str = "Start",
        on_finished: FinishedHandler | None = None,
    ):
        self.command = command
        self.fixed = dict(fixed or {})
        self.on_finished = on_finished
        self.job: Job | None = None
        self.fields: dict[str, ValueElement[Any]] = {}

        with ui.column().classes("w-full gap-2") as self.container:
            with ui.grid(columns=2).classes("w-full gap-3"):
                for action in cli.command_arguments(command):
                    if action.dest in self.fixed:
                        continue
                    self.fields[action.dest] = _field(
                        command, action, (options or {}).get(action.dest)
                    )
            with ui.row().classes("items-center gap-3"):
                self.button = (
                    ui.button(submit_label, on_click=self._start)
                    .props("no-caps")
                    .mark(f"start_{command}")
                )
                self.status = ui.label().classes("text-sm")
                self.link = ui.link("View log", "/jobs").classes("text-sm")
                self.link.visible = False
            # Created once and toggled, never recreated from its own tick.
            self.timer = ui.timer(POLL_INTERVAL_S, self._poll, active=False)

    def values(self) -> dict[str, object]:
        values: dict[str, object] = {
            dest: field.value for dest, field in self.fields.items()
        }
        values.update(self.fixed)
        return values

    async def _start(self) -> None:
        user = require_user()
        try:
            job = await project().jobs.start(self.command, self.values(), user)
        except cli.ArgumentError as exc:
            self._show(f"Check the form: {exc}", "text-red-600")
            return
        except JobConflictError as exc:
            self._show(f"{exc}; wait for it to finish first.", "text-orange-600")
            return
        self.job = job
        self.button.disable()
        self._show(f"Job #{job.id} running...", "text-gray-600")
        self.link.props(f"href=/jobs?job={job.id}")
        self.link.visible = True
        self.timer.activate()

    async def _poll(self) -> None:
        job = self.job
        if job is None or not job.finished:
            return
        self.timer.deactivate()
        self.button.enable()
        if job.status is JobStatus.SUCCEEDED:
            self._show(f"Job #{job.id} finished.", "text-green-700")
        else:
            self._show(f"Job #{job.id} {job.status.value}.", "text-red-600")
        if self.on_finished is not None:
            result = self.on_finished(job)
            if inspect.isawaitable(result):
                await result

    def _show(self, message: str, color: str) -> None:
        self.status.text = message
        self.status.classes(
            replace=f"text-sm {color}",
        )
