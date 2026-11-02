"""Background jobs, run for real as subprocesses against the test project."""

import json
from pathlib import Path

import pytest

from perch_analyzer import cli
from perch_analyzer.app_context import AppContext
from perch_analyzer.jobs import (
    Job,
    JobConflictError,
    JobManager,
    JobStatus,
    _OutputSplitter,
)

GATHER = {
    "classifier_output_id": 1,
    "min_logit": -100,
    "max_logit": 100,
    "label": "mouchi",
    "num_windows": 3,
}


async def test_gather_job_succeeds(project_dir: Path):
    manager = JobManager(project_dir)
    job = await manager.start("gather_classifier_outputs", GATHER, user="ana")
    assert job.status is JobStatus.RUNNING

    job = await manager.wait(job.id)

    log = "\n".join(manager.lines(job.id))
    assert job.status is JobStatus.SUCCEEDED, log
    assert job.return_code == 0
    assert "successfully gathered 3 window(s)" in log
    assert AppContext(project_dir).analyzer_db.get_classifier_output_labels(1) == [
        "mouchi",
        "stejay",
    ]

    meta = json.loads((project_dir / "jobs" / f"{job.id}.json").read_text())
    assert meta["status"] == "succeeded"
    assert meta["user"] == "ana"
    assert (
        (project_dir / "jobs" / f"{job.id}.log")
        .read_text()
        .startswith("$ perch-analyzer gather_classifier_outputs")
    )


async def test_failing_job_records_the_traceback(project_dir: Path):
    manager = JobManager(project_dir)
    job = await manager.start(
        "gather_classifier_outputs", {**GATHER, "classifier_output_id": 999}, "ana"
    )
    job = await manager.wait(job.id)

    assert job.status is JobStatus.FAILED
    assert job.return_code not in (0, None)
    assert any("Traceback" in line for line in manager.lines(job.id))


async def test_same_command_cannot_run_twice(project_dir: Path):
    manager = JobManager(project_dir)
    first = await manager.start("gather_classifier_outputs", GATHER, "ana")
    with pytest.raises(JobConflictError):
        await manager.start("gather_classifier_outputs", GATHER, "bo")
    await manager.wait(first.id)

    # Once it is done, the command is free again.
    second = await manager.start("gather_classifier_outputs", GATHER, "bo")
    assert (await manager.wait(second.id)).status is JobStatus.SUCCEEDED
    assert [j.id for j in manager.recent()] == [second.id, first.id]


async def test_cancel(project_dir: Path):
    manager = JobManager(project_dir)
    job = await manager.start("gather_classifier_outputs", GATHER, "ana")
    manager.cancel(job.id)
    job = await manager.wait(job.id)
    assert job.status is JobStatus.CANCELLED


async def test_bad_arguments_never_start_a_process(project_dir: Path):
    manager = JobManager(project_dir)
    with pytest.raises(cli.ArgumentError):
        await manager.start("gather_classifier_outputs", {"label": "x"}, "ana")
    for cli_only in ("embed", "create_classifier", "run_classifier"):
        with pytest.raises(ValueError, match="cannot be run from the GUI"):
            await manager.start(cli_only, {}, "ana")
    assert manager.recent() == []


def test_jobs_left_running_are_marked_interrupted(project_dir: Path):
    jobs_dir = project_dir / "jobs"
    jobs_dir.mkdir()
    stale = Job(id=4, command="search", values={}, argv=[], user="ana")
    (jobs_dir / "4.json").write_text(json.dumps(stale.to_json()))
    (jobs_dir / "5.json").write_text("not json")

    manager = JobManager(project_dir)

    job = manager.get(4)
    assert job.status is JobStatus.INTERRUPTED
    assert job.finished_at is not None
    assert json.loads((jobs_dir / "4.json").read_text())["status"] == "interrupted"
    # The unreadable file is skipped rather than breaking the history.
    assert [j.id for j in manager.recent()] == [4]


def test_output_splitter_keeps_progress_bars_out_of_the_log():
    splitter = _OutputSplitter()
    assert splitter.feed(b"starting\n 10%|#") == ["starting"]
    assert splitter.feed(b"   |\r 50%|##  |\r") == []
    assert splitter.progress == " 50%|##  |"
    # tqdm finishes with its last bar and a newline: that one is kept.
    assert splitter.feed(b"100%|####|\ndone") == ["100%|####|"]
    assert splitter.progress == ""
    assert splitter.feed(b"", final=True) == ["done"]


def test_output_splitter_handles_split_utf8():
    splitter = _OutputSplitter()
    data = "café\n".encode()
    assert splitter.feed(data[:4]) == []
    assert splitter.feed(data[4:]) == ["café"]


async def test_lines_after_only_returns_new_lines(project_dir: Path):
    manager = JobManager(project_dir)
    job = await manager.start("gather_classifier_outputs", GATHER, "ana")
    await manager.wait(job.id)
    total, lines = manager.lines_after(job.id, 0)
    assert total == len(lines) > 0
    assert manager.lines_after(job.id, total) == (total, [])
    # A fresh manager reads the same lines back from the log file.
    assert JobManager(project_dir).lines_after(job.id, 0) == (total, lines)
