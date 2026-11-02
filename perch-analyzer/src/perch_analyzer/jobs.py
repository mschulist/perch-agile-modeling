"""Running CLI commands as background jobs for the GUI.

Each job is the real CLI, `python -m perch_analyzer <command> ...`, in its own
process. That keeps JAX, TensorFlow and the embedding model out of the GUI
process, lets a job be cancelled, and leaves the event loop free while a
classifier churns through millions of windows.

Jobs are recorded as files rather than database rows, so the schema stays
as it was:

    <data_dir>/jobs/<id>.json   metadata, rewritten on every status change
    <data_dir>/jobs/<id>.log    the command's output

Nothing here imports NiceGUI; the GUI polls `JobManager` from a timer.
"""

import asyncio
import codecs
import contextlib
import json
import logging
import os
import shlex
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime as dt
from enum import StrEnum
from pathlib import Path
from typing import Any

from perch_analyzer import cli

logger = logging.getLogger(__name__)

JOBS_DIRNAME = "jobs"
# Lines of output kept in memory per job; the log file has all of them.
TAIL_LINES = 1000
# How long a cancelled job gets to exit before it is killed.
TERMINATE_GRACE_S = 10.0
_READ_CHUNK = 4096


class JobStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    # Still marked running when the GUI started, so the server stopped under it.
    INTERRUPTED = "interrupted"


class JobConflictError(RuntimeError):
    """Raised when the same command is already running."""


def _now() -> str:
    return dt.now().isoformat(timespec="seconds")


@dataclass
class Job:
    id: int
    command: str
    values: dict[str, Any]
    argv: list[str]
    user: str
    status: JobStatus = JobStatus.RUNNING
    started_at: str = field(default_factory=_now)
    finished_at: str | None = None
    return_code: int | None = None

    @property
    def finished(self) -> bool:
        return self.status is not JobStatus.RUNNING

    @property
    def display_command(self) -> str:
        """The command as someone would type it, minus the interpreter."""
        # argv is [python, -m, perch_analyzer, command, ...].
        return shlex.join(["perch-analyzer", *self.argv[3:]])

    def to_json(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "Job":
        return cls(
            id=int(data["id"]),
            command=str(data["command"]),
            values=dict(data["values"]),
            argv=[str(arg) for arg in data["argv"]],
            user=str(data["user"]),
            status=JobStatus(data["status"]),
            started_at=str(data["started_at"]),
            finished_at=data.get("finished_at"),
            return_code=data.get("return_code"),
        )


class _OutputSplitter:
    """Split a byte stream into lines, treating `\\r` as a progress update.

    tqdm redraws its bar with `\\r`; keeping each redraw as a line would bury
    the real output, so a `\\r`-terminated fragment only replaces `progress`.
    The final bar, which tqdm ends with `\\n`, is kept as a normal line.
    """

    def __init__(self) -> None:
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._partial = ""
        self.progress = ""

    def feed(self, data: bytes, final: bool = False) -> list[str]:
        lines: list[str] = []
        for char in self._decoder.decode(data, final=final):
            if char == "\n":
                lines.append(self._partial)
                self._partial = ""
                self.progress = ""
            elif char == "\r":
                if self._partial:
                    self.progress = self._partial
                self._partial = ""
            else:
                self._partial += char
        if final and self._partial:
            lines.append(self._partial)
            self._partial = ""
        return lines


class JobManager:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)
        self.jobs_dir = self.data_dir / JOBS_DIRNAME
        self._jobs: dict[int, Job] = {}
        self._tails: dict[int, deque[str]] = {}
        # Lines ever written per job, so a viewer can ask for only the new ones
        # even after the in-memory tail has rolled over.
        self._line_counts: dict[int, int] = {}
        self._progress: dict[int, str] = {}
        self._processes: dict[int, asyncio.subprocess.Process] = {}
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._cancel_requested: set[int] = set()
        self._load_history()

    # --- Paths and persistence -----------------------------------------

    def _meta_path(self, job_id: int) -> Path:
        return self.jobs_dir / f"{job_id}.json"

    def log_path(self, job_id: int) -> Path:
        return self.jobs_dir / f"{job_id}.log"

    def _write(self, job: Job) -> None:
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._meta_path(job.id).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(job.to_json(), indent=2))
        tmp.replace(self._meta_path(job.id))

    def _load_history(self) -> None:
        """Read earlier jobs, marking any left `running` as interrupted."""
        if not self.jobs_dir.is_dir():
            return
        for path in self.jobs_dir.glob("*.json"):
            try:
                job = Job.from_json(json.loads(path.read_text()))
            except (ValueError, TypeError, KeyError):
                logger.warning("ignoring unreadable job file %s", path)
                continue
            if job.status is JobStatus.RUNNING:
                job.status = JobStatus.INTERRUPTED
                job.finished_at = job.finished_at or _now()
                self._write(job)
            self._jobs[job.id] = job

    # --- Queries ---------------------------------------------------------

    def get(self, job_id: int) -> Job:
        return self._jobs[job_id]

    def recent(self, limit: int = 50) -> list[Job]:
        """Most recent first."""
        return [self._jobs[i] for i in sorted(self._jobs, reverse=True)[:limit]]

    def running(self, command: str | None = None) -> list[Job]:
        return [
            job
            for job in self._jobs.values()
            if job.status is JobStatus.RUNNING
            and (command is None or job.command == command)
        ]

    def lines(self, job_id: int) -> list[str]:
        """The tail of a job's output."""
        tail = self._tails.get(job_id)
        if tail is not None:
            return list(tail)
        path = self.log_path(job_id)
        if not path.exists():
            return []
        with path.open(errors="replace") as f:
            return list(deque((line.rstrip("\n") for line in f), maxlen=TAIL_LINES))

    def lines_after(self, job_id: int, seen: int) -> tuple[int, list[str]]:
        """Lines written since a viewer had seen `seen` of them.

        Returns the new total and the unseen lines (at most a tail's worth).
        """
        if job_id not in self._tails:
            lines = self.lines(job_id)
            return len(lines), lines[seen:]
        total = self._line_counts.get(job_id, 0)
        unseen = total - seen
        if unseen <= 0:
            return total, []
        tail = list(self._tails[job_id])
        return total, tail[-unseen:]

    def progress(self, job_id: int) -> str:
        """The latest progress-bar redraw, if the job is showing one."""
        return self._progress.get(job_id, "")

    # --- Running -----------------------------------------------------------

    async def start(self, command: str, values: dict[str, Any], user: str) -> Job:
        """Launch `command`. Must be called from the event loop.

        Raises `cli.ArgumentError` for bad values and `JobConflictError` if the
        same command is already running: two searches at once would both
        insert annotations for the same target recordings.
        """
        if not cli.get_command(command).gui:
            raise ValueError(f"{command} cannot be run from the GUI")
        argv = cli.subprocess_argv(command, self.data_dir, values)
        if self.running(command):
            raise JobConflictError(f"{command} is already running")

        job = Job(
            id=max(self._jobs, default=0) + 1,
            command=command,
            values=dict(values),
            argv=argv,
            user=user,
        )
        self._jobs[job.id] = job
        self._tails[job.id] = deque(maxlen=TAIL_LINES)
        self._write(job)

        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                stdin=asyncio.subprocess.DEVNULL,
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
            )
        except OSError as exc:
            self._finish(job, JobStatus.FAILED, None)
            self._append(job, f"could not start: {exc}")
            raise

        self._processes[job.id] = process
        self._tasks[job.id] = asyncio.create_task(self._watch(job, process))
        logger.info("job %d started by %s: %s", job.id, user, job.display_command)
        return job

    async def wait(self, job_id: int) -> Job:
        task = self._tasks.get(job_id)
        if task is not None:
            await asyncio.shield(task)
        return self._jobs[job_id]

    def cancel(self, job_id: int) -> None:
        process = self._processes.get(job_id)
        if process is None or process.returncode is not None:
            return
        self._cancel_requested.add(job_id)
        process.terminate()
        asyncio.get_running_loop().call_later(
            TERMINATE_GRACE_S, self._kill_if_alive, job_id
        )

    def _kill_if_alive(self, job_id: int) -> None:
        process = self._processes.get(job_id)
        if process is not None and process.returncode is None:
            logger.warning("job %d ignored SIGTERM; killing it", job_id)
            process.kill()

    async def shutdown(self) -> None:
        """Stop every running job, for when the GUI exits."""
        for job in self.running():
            self.cancel(job.id)
        tasks = list(self._tasks.values())
        if tasks:
            await asyncio.wait(tasks, timeout=TERMINATE_GRACE_S)

    def _append(self, job: Job, line: str) -> None:
        self._tails.setdefault(job.id, deque(maxlen=TAIL_LINES)).append(line)
        self._line_counts[job.id] = self._line_counts.get(job.id, 0) + 1
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        with self.log_path(job.id).open("a") as f:
            f.write(line + "\n")

    async def _watch(self, job: Job, process: asyncio.subprocess.Process) -> None:
        assert process.stdout is not None
        splitter = _OutputSplitter()
        self._append(job, f"$ {job.display_command}")
        try:
            while chunk := await process.stdout.read(_READ_CHUNK):
                for line in splitter.feed(chunk):
                    self._append(job, line)
                self._progress[job.id] = splitter.progress
            for line in splitter.feed(b"", final=True):
                self._append(job, line)
            return_code = await process.wait()
        finally:
            self._progress.pop(job.id, None)
            self._processes.pop(job.id, None)

        if job.id in self._cancel_requested:
            status = JobStatus.CANCELLED
        elif return_code == 0:
            status = JobStatus.SUCCEEDED
        else:
            status = JobStatus.FAILED
        self._finish(job, status, return_code)
        self._append(job, f"[{status.value}, exit code {return_code}]")
        logger.info("job %d %s (exit code %s)", job.id, status.value, return_code)

    def _finish(self, job: Job, status: JobStatus, return_code: int | None) -> None:
        job.status = status
        job.return_code = return_code
        job.finished_at = _now()
        self._cancel_requested.discard(job.id)
        with contextlib.suppress(OSError):
            self._write(job)
