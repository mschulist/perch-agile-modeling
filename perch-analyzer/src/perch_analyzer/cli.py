import argparse
from perch_analyzer.gui import home_page
from perch_analyzer.config import initialize_directory, config
from pathlib import Path
from perch_analyzer.embed import embed
from perch_analyzer.target_recordings import target_recordings
from perch_analyzer.db import db
from perch_analyzer.search import search
from perch_hoplite.db import sqlite_usearch_impl


def main():
    parser = argparse.ArgumentParser(
        description="Perch Analyzer - Bird call analysis toolkit"
    )

    # Create subparsers for different modules
    subparsers = parser.add_subparsers(
        dest="module", help="Modules of the program to run", required=True
    )

    # Initialize command
    initialize_parser = subparsers.add_parser("init", help="Initialize a project")
    initialize_parser.add_argument("--data_dir", type=Path, required=True)
    initialize_parser.add_argument("--project_name", type=str, required=True)
    initialize_parser.add_argument("--user_name", type=str, required=True)
    initialize_parser.add_argument("--embedding_model", type=str, required=True)

    # GUI subcommand
    gui_parser = subparsers.add_parser("gui", help="Launch the GUI interface")
    gui_parser.add_argument("--data_dir", type=Path, required=True)
    gui_parser.add_argument(
        "--share", action="store_true", help="Create a public share link"
    )
    gui_parser.add_argument(
        "--server-name",
        type=str,
        default="127.0.0.1",
        help="Server name (default: 127.0.0.1)",
    )
    gui_parser.add_argument(
        "--server-port", type=int, default=7860, help="Server port (default: 7860)"
    )

    # Embed subcommand
    embed_parser = subparsers.add_parser("embed", help="Generate embeddings from audio")
    embed_parser.add_argument("--data_dir", type=Path, required=True)
    embed_parser.add_argument("--ARU_base_path", type=str, required=True)
    embed_parser.add_argument("--ARU_file_glob", type=str, required=True)

    # Target recordings subcommand
    target_recordings_parser = subparsers.add_parser(
        "target_recordings", help="Gather target recordings"
    )
    target_recordings_parser.add_argument("--data_dir", type=Path, required=True)
    target_recordings_parser.add_argument("--ebird_code", type=str, required=True)
    target_recordings_parser.add_argument(
        "--call_type",
        type=str,
        required=True,
        help="call type to search for, one of (song, call)",
    )
    target_recordings_parser.add_argument("--num_recordings", type=int, default=1)

    # Search subcommand
    search_parser = subparsers.add_parser("search", help="Search recordings")
    search_parser.add_argument("--data_dir", type=Path, required=True)
    search_parser.add_argument("--num_per_target_recording", type=int, default=5)

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate section
    if args.module == "gui":
        demo = home_page.home(args.data_dir)
        demo.launch(
            share=args.share, server_name=args.server_name, server_port=args.server_port
        )
    elif args.module == "embed":
        if not initialize_directory.check_initialized(args.data_dir):
            raise ValueError(
                f"data directory {args.data_dir} is not initialized yet, run perch-analyzer init --data_dir={args.data_dir}"
            )
        # update the config with the ARU path
        conf = config.Config.load(args.data_dir)

        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )

        print("embedding audio...this may take a while")
        embed.embed_audio(
            config=conf,
            hoplite_db=hoplite_db,
            ARU_base_path=args.ARU_base_path,
            ARU_file_glob=args.ARU_file_glob,
        )
        print("done embedding audio!")
    elif args.module == "init":
        initialize_directory.initialize_directory(
            data_path=args.data_dir,
            project_name=args.project_name,
            user_name=args.user_name,
            embedding_model=args.embedding_model,
        )
        print(f"Successfully initialized directory {args.data_dir}!")
    elif args.module == "target_recordings":
        if not initialize_directory.check_initialized(args.data_dir):
            raise ValueError(
                f"data directory {args.data_dir} is not initialized yet, run perch-analyzer init --data_dir={args.data_dir}"
            )
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)

        print("adding recordings from xenocanto")

        target_recordings.add_target_recording_from_xc(
            config=conf,
            db=analyzer_db,
            ebird_6_code=args.ebird_code,
            call_type=args.call_type,
            num_recordings=args.num_recordings,
        )

        print("finished adding recordings!")
    if args.module == "search":
        if not initialize_directory.check_initialized(args.data_dir):
            raise ValueError(
                f"data directory {args.data_dir} is not initialized yet, run perch-analyzer init --data_dir={args.data_dir}"
            )
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )

        print("searching recordings")

        search.search_using_target_recordings(
            config=conf,
            db=analyzer_db,
            hoplite_db=hoplite_db,
            num_per_target_recording=args.num_per_target_recording,
        )

        print("finished searching recordings!")


if __name__ == "__main__":
    main()
