"""Launch CLI commands and follow their progress.

`embed` and `create_classifier` are deliberately absent: they want a GPU and
careful tuning, and stay on the command line. Everything with `gui=True` in
`cli.COMMANDS` gets a form here.
"""

import logging
from dataclasses import dataclass, field

from nicegui import ui

from perch_analyzer import cli
from perch_analyzer.db.db import AnalyzerDB
from perch_analyzer.gui.background import load
from perch_analyzer.gui.components import loading, page_layout, wait_for_client
from perch_analyzer.gui.job_forms import JobForm
from perch_analyzer.gui.services import ProjectServices, project
from perch_analyzer.jobs import Job, JobStatus

logger = logging.getLogger(__name__)

REFRESH_INTERVAL_S = 1.0
RECENT_JOBS = 50

STATUS_COLORS = {
    JobStatus.RUNNING: "text-blue-700",
    JobStatus.SUCCEEDED: "text-green-700",
    JobStatus.FAILED: "text-red-600",
    JobStatus.CANCELLED: "text-orange-600",
    JobStatus.INTERRUPTED: "text-orange-600",
}

COLUMNS = [
    {"name": "id", "label": "#", "field": "id", "align": "left"},
    {"name": "command", "label": "Command", "field": "command", "align": "left"},
    {"name": "user", "label": "User", "field": "user", "align": "left"},
    {"name": "status", "label": "Status", "field": "status", "align": "left"},
    {"name": "started", "label": "Started", "field": "started", "align": "left"},
    {"name": "finished", "label": "Finished", "field": "finished", "align": "left"},
]


@dataclass
class FormChoices:
    """Existing ids and labels to offer in the forms, read once per page load."""

    classifier_ids: list[int] = field(default_factory=list)
    classifier_output_ids: list[int] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    unfinished_target_recordings: int = 0


def _load_choices(analyzer_db: AnalyzerDB) -> FormChoices:
    classifiers = analyzer_db.get_all_classifiers()
    output_ids = [
        output.id
        for classifier in classifiers
        for output in analyzer_db.get_all_classifier_outputs(classifier.id)
    ]
    return FormChoices(
        classifier_ids=[classifier.id for classifier in classifiers],
        classifier_output_ids=sorted(output_ids),
        labels=sorted({label for c in classifiers for label in c.labels}),
        unfinished_target_recordings=analyzer_db.count_target_recordings(False),
    )


def _row(job: Job) -> dict[str, object]:
    return {
        "id": job.id,
        "command": job.command,
        "user": job.user,
        "status": job.status.value,
        "started": job.started_at.replace("T", " "),
        "finished": (job.finished_at or "").replace("T", " "),
    }


class JobsView:
    def __init__(self, services: ProjectServices, selected: int | None):
        self.services = services
        self.selected = selected
        self._seen_lines = 0

    async def build(self) -> None:
        with page_layout("Jobs"):
            ui.label(
                "Run project commands in the background. Embedding and training "
                "classifiers stay on the command line."
            ).classes("text-sm text-gray-500")
            with ui.row().classes("w-full gap-6 items-start no-wrap"):
                with ui.column().classes("w-[560px] shrink-0 gap-3"):
                    ui.label("Start a job").classes("text-2xl font-bold")
                    self.forms_slot = ui.column().classes("w-full gap-3")
                with ui.column().classes("grow gap-3 min-w-0"):
                    ui.label("Recent jobs").classes("text-2xl font-bold")
                    self.table = ui.table(
                        rows=[], columns=COLUMNS, row_key="id", pagination=10
                    ).classes("w-full cursor-pointer")
                    self.table.on("rowClick", self._on_row_click)
                    with ui.row().classes("w-full items-center gap-3"):
                        self.log_title = ui.label("Select a job to see its log.")
                        self.log_title.classes("text-lg font-semibold")
                        self.cancel_button = ui.button(
                            "Cancel job", on_click=self._cancel
                        ).props("outline dense no-caps color=negative")
                        self.cancel_button.visible = False
                    self.command_label = ui.label().classes(
                        "font-mono text-xs text-gray-600 break-all"
                    )
                    self.log = ui.log(max_lines=2000).classes("w-full h-[420px]")
                    self.progress = ui.label().classes("font-mono text-xs")
            self.timer = ui.timer(REFRESH_INTERVAL_S, self._refresh, active=False)

        await wait_for_client()

        with self.forms_slot:
            spinner = loading("Loading...")
        choices = await load(_load_choices, self.services.analyzer_db)
        spinner.delete()
        with self.forms_slot:
            self._build_forms(choices)

        self._refresh_table()
        if self.selected is not None:
            self._select(self.selected)
        self.timer.activate()

    def _build_forms(self, choices: FormChoices) -> None:
        options: dict[str, dict[str, list[object]]] = {
            "run_classifier": {"classifier_id": list(choices.classifier_ids)},
            "gather_classifier_outputs": {
                "classifier_output_id": list(choices.classifier_output_ids),
                "label": list(choices.labels),
            },
        }
        for command in cli.gui_commands():
            with (
                ui.expansion(command.help, caption=command.name)
                .classes("w-full border rounded")
                .mark(f"form_{command.name}"),
                ui.column().classes("w-full gap-2 p-2"),
            ):
                if command.name == "search":
                    ui.label(
                        f"{choices.unfinished_target_recordings} unfinished target "
                        "recording(s) will be searched."
                    ).classes("text-sm text-gray-500")
                JobForm(
                    command.name,
                    options=options.get(command.name),
                    on_finished=self._on_job_finished,
                )

    # --- Live updates ----------------------------------------------------

    def _refresh_table(self) -> None:
        self.table.rows = [_row(job) for job in self.services.jobs.recent(RECENT_JOBS)]
        self.table.update()

    async def _refresh(self) -> None:
        self._refresh_table()
        if self.selected is not None:
            self._update_log()

    def _on_job_finished(self, job: Job) -> None:
        self._refresh_table()

    def _on_row_click(self, event: object) -> None:
        args = getattr(event, "args", None)
        # Quasar's rowClick emits (event, row, index).
        if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], dict):
            job_id = args[1].get("id")
            if isinstance(job_id, int):
                self._select(job_id)

    def _select(self, job_id: int) -> None:
        try:
            self.services.jobs.get(job_id)
        except KeyError:
            self.log_title.text = f"No job #{job_id}."
            return
        self.selected = job_id
        self._seen_lines = 0
        self.log.clear()
        self._update_log()

    def _update_log(self) -> None:
        assert self.selected is not None
        jobs = self.services.jobs
        job = jobs.get(self.selected)
        self.log_title.text = f"Job #{job.id}: {job.command} ({job.status.value})"
        self.log_title.classes(
            replace=f"text-lg font-semibold {STATUS_COLORS[job.status]}"
        )
        self.command_label.text = f"{job.display_command}  (started by {job.user})"
        self.cancel_button.visible = not job.finished
        self._seen_lines, new_lines = jobs.lines_after(job.id, self._seen_lines)
        for line in new_lines:
            self.log.push(line)
        self.progress.text = jobs.progress(job.id)

    def _cancel(self) -> None:
        if self.selected is not None:
            self.services.jobs.cancel(self.selected)
            ui.notify(f"Cancelling job #{self.selected}")


async def jobs_page(job: int | None = None) -> None:
    await JobsView(project(), job).build()
