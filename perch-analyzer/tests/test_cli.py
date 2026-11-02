"""The CLI's user commands, and the bridge the GUI uses to build commands."""

import argparse
import sys
from pathlib import Path

import pytest

from perch_analyzer import cli
from perch_analyzer.app_context import AppContext

from .conftest import TEST_USERNAME


def run(project_dir: Path, *argv: str) -> int:
    return cli.main([argv[0], f"--data_dir={project_dir}", *argv[1:]])


def test_add_list_and_remove_user(
    project_dir: Path, capsys: pytest.CaptureFixture[str]
):
    assert run(project_dir, "add_user", "--username=ana", "--password=pw") == 0
    assert AppContext(project_dir).analyzer_db.verify_user("ana", "pw")

    run(project_dir, "list_users")
    out = capsys.readouterr().out
    assert "ana" in out and TEST_USERNAME in out

    assert run(project_dir, "set_password", "--username=ana", "--password=new") == 0
    assert AppContext(project_dir).analyzer_db.verify_user("ana", "new")

    assert run(project_dir, "remove_user", "--username=ana") == 0
    assert not AppContext(project_dir).analyzer_db.user_exists("ana")


def test_add_user_twice_fails(project_dir: Path):
    with pytest.raises(SystemExit, match="already exists"):
        run(project_dir, "add_user", f"--username={TEST_USERNAME}", "--password=x")


def test_gui_commands_are_the_cpu_friendly_ones():
    assert [c.name for c in cli.gui_commands()] == [
        "target_recordings",
        "search",
        "run_classifier",
        "gather_classifier_outputs",
    ]


SAMPLE_VALUES: dict[str, dict[str, object]] = {
    "target_recordings": {
        "ebird_code": "stejay",
        "call_type": "song",
        "num_recordings": 2.0,
    },
    "search": {"num_per_target_recording": 7},
    "run_classifier": {"classifier_id": 1},
    "gather_classifier_outputs": {
        "classifier_output_id": 1,
        "min_logit": -2.5,
        "max_logit": 3,
        "label": "-odd-label",
        "num_windows": 5.0,
        "filename": "",
        "min_offset": None,
    },
}


@pytest.mark.parametrize("command", [c.name for c in cli.gui_commands()])
def test_to_argv_round_trips_through_the_real_parser(command: str):
    argv = cli.to_argv(command, SAMPLE_VALUES[command])
    args = cli.build_parser().parse_args([command, "--data_dir=/x", *argv])
    for dest, value in SAMPLE_VALUES[command].items():
        if value in (None, ""):
            continue
        parsed = getattr(args, dest)
        assert parsed == value, (dest, parsed, value)
        if isinstance(parsed, int) and not isinstance(parsed, bool):
            # Integer flags must arrive as ints even from `ui.number` floats.
            action = next(a for a in cli.command_arguments(command) if a.dest == dest)
            assert action.type is not int or type(parsed) is int


def test_to_argv_rejects_bad_values():
    with pytest.raises(cli.ArgumentError, match="required"):
        cli.to_argv("run_classifier", {})
    with pytest.raises(cli.ArgumentError, match="invalid choice"):
        cli.to_argv(
            "target_recordings", {"ebird_code": "stejay", "call_type": "squawk"}
        )


def test_subprocess_argv_runs_this_interpreter(tmp_path: Path):
    argv = cli.subprocess_argv("search", tmp_path, {})
    assert argv[:4] == [sys.executable, "-m", "perch_analyzer", "search"]
    assert f"--data_dir={tmp_path}" in argv


def test_building_the_parser_does_not_import_nicegui():
    import subprocess

    code = (
        "import sys; from perch_analyzer import cli; cli.build_parser(); "
        "sys.exit('nicegui' in sys.modules)"
    )
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_command_arguments_excludes_shared_options():
    dests = {a.dest for a in cli.command_arguments("search")}
    assert dests == {"num_per_target_recording"}
    assert all(isinstance(a, argparse.Action) for a in cli.command_arguments("search"))
