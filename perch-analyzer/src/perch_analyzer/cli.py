"""Command line interface for Perch Analyzer.

Each subcommand is a `Command` entry in `COMMANDS`. Handlers import their
implementation module lazily so that, for example, `perch-analyzer init` never
pays for JAX, polars or TensorFlow.

Commands marked `gui=True` can also be launched from the GUI's Jobs page. The
GUI builds its forms from the same argparse definitions (`command_arguments`)
and turns the filled-in form back into a command line (`to_argv`), which runs
as a subprocess. There is one definition of every flag, here.
"""

import argparse
import getpass
import logging
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import NoReturn, override

from perch_analyzer.app_context import AppContext, ProjectNotInitializedError
from perch_analyzer.logging_config import setup_logging

logger = logging.getLogger(__name__)

ArgumentAdder = Callable[[argparse.ArgumentParser], None]
Handler = Callable[[AppContext, argparse.Namespace], None]


@dataclass(frozen=True)
class Command:
    name: str
    help: str
    handler: Handler
    add_arguments: ArgumentAdder = field(default=lambda parser: None)
    # `init` is the only command that may run against an empty directory.
    requires_project: bool = True
    # Whether the GUI's Jobs page offers this command. Commands that need a
    # GPU or careful tuning (`embed`, `create_classifier`) stay CLI-only.
    gui: bool = False


def report(message: str) -> None:
    """Tell the user something, and record it in the project log."""
    logger.info(message)


# --- Handlers --------------------------------------------------------------


def handle_init(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.config import initialize_directory

    initialize_directory.initialize_directory(
        data_path=ctx.data_dir,
        project_name=args.project_name,
        user_name=args.user_name,
        embedding_model=args.embedding_model,
    )
    report(f"Successfully initialized directory {ctx.data_dir}!")


def handle_gui(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.gui import settings

    # NiceGUI reads this when it is first imported, so it must be set before
    # `gui.app` is. Keeps login sessions inside the project, not the cwd.
    os.environ.setdefault(
        "NICEGUI_STORAGE_PATH", str(ctx.data_dir / settings.STORAGE_DIRNAME)
    )
    from perch_analyzer.gui.app import launch

    launch(
        ctx,
        host=args.host,
        port=args.port,
        show=not args.no_browser,
        reload=False,
        response_timeout=args.page_timeout,
        reconnect_timeout=args.reconnect_timeout,
    )


def handle_embed(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.embed import embed

    report("embedding audio...this may take a while")
    embed.embed_audio(
        config=ctx.config,
        hoplite_db=ctx.hoplite_db,
        ARU_base_path=args.ARU_base_path,
        ARU_file_glob=args.ARU_file_glob,
    )
    report("done embedding audio!")


def handle_target_recordings(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.target_recordings import target_recordings

    report("adding recordings from xenocanto")
    added = target_recordings.add_target_recording_from_xc(
        config=ctx.config,
        db=ctx.analyzer_db,
        ebird_6_code=args.ebird_code,
        call_type=args.call_type,
        num_recordings=args.num_recordings,
    )
    report(f"finished adding {added} recording(s)!")


def handle_search(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.search import search

    report("searching recordings")
    search.search_using_target_recordings(
        config=ctx.config,
        db=ctx.analyzer_db,
        hoplite_db=ctx.hoplite_db,
        num_per_target_recording=args.num_per_target_recording,
    )
    report("finished searching recordings!")


def handle_create_classifier(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.classify import classifier

    report("making custom classifier")
    classifier_id = classifier.train_classifier(
        config=ctx.config,
        hoplite_db=ctx.hoplite_db,
        analyzer_db=ctx.analyzer_db,
        throwaway_classes=args.throwaway_classes,
        train_ratio=args.train_ratio,
        learning_rate=args.learning_rate,
        weak_neg_rate=args.weak_neg_rate,
        num_train_steps=args.num_train_steps,
    )
    report(f"done making classifier {classifier_id}!")


def handle_run_classifier(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.classify import classify

    report("running classifier!")
    output_id = classify.classify(
        classifier_id=args.classifier_id,
        hoplite_db=ctx.hoplite_db,
        analyzer_db=ctx.analyzer_db,
    )
    report(f"done running classifier, classifier output id is {output_id}")


def handle_set_xc_api_key(ctx: AppContext, args: argparse.Namespace) -> None:
    config = ctx.config
    config.xenocanto_api_key = args.xc_api_key
    config.to_file()
    report("successfully updated Xeno-canto API key")


def handle_gather_classifier_outputs(ctx: AppContext, args: argparse.Namespace) -> None:
    from perch_analyzer.classify import classifier_outputs

    gathered = classifier_outputs.gather_classifier_output_windows(
        analyzer_db=ctx.analyzer_db,
        classifier_output_id=args.classifier_output_id,
        min_logit=args.min_logit,
        max_logit=args.max_logit,
        label=args.label,
        num_windows=args.num_windows,
        filename=args.filename,
        min_offset=args.min_offset,
        max_offset=args.max_offset,
    )
    report(f"successfully gathered {gathered} window(s)")


def _read_password(args: argparse.Namespace) -> str:
    if args.password is not None:
        return args.password
    password = getpass.getpass("Password: ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("error: passwords do not match")
    return password


def handle_add_user(ctx: AppContext, args: argparse.Namespace) -> None:
    try:
        ctx.analyzer_db.create_user(args.username, _read_password(args))
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc
    report(f"created user {args.username.strip()!r}")


def handle_set_password(ctx: AppContext, args: argparse.Namespace) -> None:
    try:
        ctx.analyzer_db.set_password(args.username, _read_password(args))
    except (KeyError, ValueError) as exc:
        raise SystemExit(f"error: {exc.args[0]}") from exc
    report(f"updated the password for {args.username.strip()!r}")


def handle_remove_user(ctx: AppContext, args: argparse.Namespace) -> None:
    try:
        ctx.analyzer_db.delete_user(args.username)
    except KeyError as exc:
        raise SystemExit(f"error: {exc.args[0]}") from exc
    report(f"removed user {args.username.strip()!r}")


def handle_list_users(ctx: AppContext, args: argparse.Namespace) -> None:
    users = ctx.analyzer_db.list_users()
    if not users:
        print("no users yet; create one with `perch-analyzer add_user`")
    for user in users:
        print(f"{user.username}\t(created {user.created_at:%Y-%m-%d %H:%M})")


# --- Argument definitions --------------------------------------------------


def init_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project_name", type=str, required=True)
    parser.add_argument("--user_name", type=str, required=True)
    parser.add_argument("--embedding_model", type=str, required=True)


def gui_args(parser: argparse.ArgumentParser) -> None:
    # `gui.settings` rather than `gui.app`: importing NiceGUI here would slow
    # down building the parser for every command.
    from perch_analyzer.gui import settings as gui_settings

    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Address to bind to."
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser window on startup.",
    )
    parser.add_argument(
        "--page_timeout",
        type=float,
        default=gui_settings.DEFAULT_RESPONSE_TIMEOUT,
        help=(
            "Seconds a page may take to build before the browser gives up. "
            "Raise it if rendering spectrograms for a large project times out."
        ),
    )
    parser.add_argument(
        "--reconnect_timeout",
        type=float,
        default=gui_settings.DEFAULT_RECONNECT_TIMEOUT,
        help="Seconds the server keeps a disconnected browser's state alive.",
    )


def embed_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ARU_base_path", type=str, required=True)
    parser.add_argument("--ARU_file_glob", type=str, required=True)


def target_recordings_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ebird_code", type=str, required=True)
    parser.add_argument(
        "--call_type",
        type=str,
        required=True,
        choices=("song", "call"),
        help="call type to search for",
    )
    parser.add_argument("--num_recordings", type=int, default=1)


def search_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--num_per_target_recording", type=int, default=5)


def create_classifier_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--throwaway_classes", nargs="*", type=str, default=[])
    parser.add_argument("--train_ratio", type=float, default=0.8)
    parser.add_argument("--learning_rate", type=float, default=1e-3)
    parser.add_argument("--weak_neg_rate", type=float, default=0.05)
    parser.add_argument("--num_train_steps", type=int, default=128)


def run_classifier_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--classifier_id", type=int, required=True)


def set_xc_api_key_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--xc_api_key", type=str, required=True)


def username_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--username", type=str, required=True)


def username_password_args(parser: argparse.ArgumentParser) -> None:
    username_args(parser)
    parser.add_argument(
        "--password",
        type=str,
        default=None,
        help="prompted for if omitted, which keeps it out of your shell history",
    )


def gather_classifier_outputs_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--classifier_output_id", type=int, required=True)
    parser.add_argument("--min_logit", type=float, required=True)
    parser.add_argument("--max_logit", type=float, required=True)
    parser.add_argument("--label", type=str, required=True)
    parser.add_argument("--num_windows", type=int, default=1)
    parser.add_argument(
        "--filename",
        type=str,
        default=None,
        help="only gather windows from this recording (exact match)",
    )
    parser.add_argument(
        "--min_offset",
        type=float,
        default=None,
        help="only gather windows starting at or after this many seconds",
    )
    parser.add_argument(
        "--max_offset",
        type=float,
        default=None,
        help="only gather windows starting at or before this many seconds",
    )


COMMANDS: tuple[Command, ...] = (
    Command(
        name="init",
        help="Initialize a project",
        handler=handle_init,
        add_arguments=init_args,
        requires_project=False,
    ),
    Command(
        name="gui",
        help="Launch the GUI interface",
        handler=handle_gui,
        add_arguments=gui_args,
    ),
    Command(
        name="embed",
        help="Generate embeddings from audio",
        handler=handle_embed,
        add_arguments=embed_args,
    ),
    Command(
        name="target_recordings",
        help="Gather target recordings",
        handler=handle_target_recordings,
        add_arguments=target_recordings_args,
        gui=True,
    ),
    Command(
        name="search",
        help="Search recordings",
        handler=handle_search,
        add_arguments=search_args,
        gui=True,
    ),
    Command(
        name="create_classifier",
        help="Create a custom classifier",
        handler=handle_create_classifier,
        add_arguments=create_classifier_args,
    ),
    Command(
        name="run_classifier",
        help="Run a custom classifier on the data",
        handler=handle_run_classifier,
        add_arguments=run_classifier_args,
        gui=True,
    ),
    Command(
        name="set_xc_api_key",
        help="Set the Xeno-canto API key for the given project",
        handler=handle_set_xc_api_key,
        add_arguments=set_xc_api_key_args,
    ),
    Command(
        name="gather_classifier_outputs",
        help=(
            "Gather outputs from classifier outputs for a particular label and "
            "logit range"
        ),
        handler=handle_gather_classifier_outputs,
        add_arguments=gather_classifier_outputs_args,
        gui=True,
    ),
    Command(
        name="add_user",
        help="Create a GUI login",
        handler=handle_add_user,
        add_arguments=username_password_args,
    ),
    Command(
        name="set_password",
        help="Change a GUI login's password",
        handler=handle_set_password,
        add_arguments=username_password_args,
    ),
    Command(
        name="remove_user",
        help="Delete a GUI login (their annotations are kept)",
        handler=handle_remove_user,
        add_arguments=username_args,
    ),
    Command(
        name="list_users",
        help="List GUI logins",
        handler=handle_list_users,
    ),
)


# --- Running commands from the GUI -----------------------------------------


def get_command(name: str) -> Command:
    for command in COMMANDS:
        if command.name == name:
            return command
    raise KeyError(f"unknown command {name!r}")


def gui_commands() -> tuple[Command, ...]:
    """The commands the GUI may launch."""
    return tuple(command for command in COMMANDS if command.gui)


class ArgumentError(ValueError):
    """A command's arguments did not parse."""


class _RaisingParser(argparse.ArgumentParser):
    """A parser that raises instead of printing usage and exiting."""

    @override
    def error(self, message: str) -> NoReturn:
        raise ArgumentError(message)


def _command_parser(name: str) -> argparse.ArgumentParser:
    parser = _RaisingParser(prog=f"perch-analyzer {name}", add_help=False)
    get_command(name).add_arguments(parser)
    return parser


def command_arguments(name: str) -> list[argparse.Action]:
    """The options a command takes, excluding the shared ones like --data_dir."""
    return list(_command_parser(name)._actions)


def _flag(action: argparse.Action) -> str:
    return max(action.option_strings, key=len)


def to_argv(name: str, values: Mapping[str, object]) -> list[str]:
    """Turn {dest: value} into command line options for `name`.

    `None`, empty strings and empty lists are left out, so the option falls
    back to its default. The result is parsed before being returned, so a bad
    value raises `ArgumentError` here rather than inside a subprocess.
    """
    argv: list[str] = []
    for action in command_arguments(name):
        value = values.get(action.dest)
        if value is None or value == "" or value == []:
            continue
        flag = _flag(action)
        if action.nargs == 0:  # store_true and friends
            if value:
                argv.append(flag)
        elif action.nargs in ("*", "+"):
            items: list[object] = (
                list(value) if isinstance(value, (list, tuple)) else [value]
            )
            argv.append(flag)
            argv.extend(str(item) for item in items)
        else:
            if action.type is int and isinstance(value, float) and value.is_integer():
                # `ui.number` hands back floats even for integer fields.
                value = int(value)
            # `--flag=value` keeps a value that starts with "-" from being
            # mistaken for an option.
            argv.append(f"{flag}={value}")
    _command_parser(name).parse_args(argv)
    return argv


def subprocess_argv(
    name: str, data_dir: Path, values: Mapping[str, object]
) -> list[str]:
    """The full command line that runs `name` in a fresh Python process."""
    return [
        sys.executable,
        "-m",
        "perch_analyzer",
        name,
        f"--data_dir={data_dir}",
        *to_argv(name, values),
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perch-analyzer",
        description="Perch Analyzer - Bird call analysis toolkit",
    )
    parser.add_argument("--version", action="version", version=_version())

    # Options every subcommand shares. Declared on a parent parser so they stay
    # in one place and appear in each subcommand's --help.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--data_dir",
        type=Path,
        required=True,
        help="Project directory created by `perch-analyzer init`.",
    )
    common.add_argument(
        "-v", "--verbose", action="store_true", help="Show debug logging."
    )
    common.add_argument("-q", "--quiet", action="store_true", help="Only show errors.")

    subparsers = parser.add_subparsers(
        dest="module", help="Modules of the program to run", required=True
    )
    for command in COMMANDS:
        subparser = subparsers.add_parser(
            command.name, help=command.help, parents=[common]
        )
        command.add_arguments(subparser)
        subparser.set_defaults(command=command)

    return parser


def _version() -> str:
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("perch-analyzer")
    except PackageNotFoundError:
        return "unknown"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command: Command = args.command

    ctx = AppContext(args.data_dir)
    verbosity = 1 if args.verbose else (-1 if args.quiet else 0)
    # `init` may be creating the directory, so only log to a file once it is
    # plausible that one exists.
    setup_logging(ctx.data_dir if ctx.data_dir.is_dir() else None, verbosity)

    try:
        if command.requires_project:
            ctx.require_initialized()
        command.handler(ctx, args)
    except ProjectNotInitializedError as exc:
        parser.exit(2, f"error: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "\ninterrupted\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
