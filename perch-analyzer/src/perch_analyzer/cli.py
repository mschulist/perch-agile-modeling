"""Command line interface for Perch Analyzer.

Each subcommand is a `Command` entry in `COMMANDS`. Handlers import their
implementation module lazily so that, for example, `perch-analyzer init` never
pays for JAX, polars or TensorFlow.
"""

import argparse
import logging
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

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
    from perch_analyzer.gui.app import launch

    launch(
        ctx,
        host=args.host,
        port=args.port,
        show=not args.no_browser,
        reload=False,
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
    )
    report(f"successfully gathered {gathered} window(s)")


# --- Argument definitions --------------------------------------------------


def init_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--project_name", type=str, required=True)
    parser.add_argument("--user_name", type=str, required=True)
    parser.add_argument("--embedding_model", type=str, required=True)


def gui_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--host", type=str, default="127.0.0.1", help="Address to bind to."
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on.")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open a browser window on startup.",
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
        help="call type to search for, one of (song, call)",
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


def gather_classifier_outputs_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--classifier_output_id", type=int, required=True)
    parser.add_argument("--min_logit", type=float, required=True)
    parser.add_argument("--max_logit", type=float, required=True)
    parser.add_argument("--label", type=str, required=True)
    parser.add_argument("--num_windows", type=int, default=1)


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
    ),
    Command(
        name="search",
        help="Search recordings",
        handler=handle_search,
        add_arguments=search_args,
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
    ),
)


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
