import argparse
from perch_analyzer.gui.home_page import homepage
from perch_analyzer.config import initialize_directory, config
from pathlib import Path
from perch_analyzer.embed import embed
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

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate section
    if args.module == "gui":
        homepage.launch(
            share=args.share, server_name=args.server_name, server_port=args.server_port
        )
    elif args.module == "embed":
        # update the config with the ARU path
        conf = config.Config.load(args.data_dir)
        conf.ARU_base_path = args.ARU_base_path
        conf.ARU_file_glob = args.ARU_file_glob

        conf.to_file()

        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )

        print("embedding audio...this may take a while")
        embed.embed_audio(config=conf, hoplite_db=hoplite_db)
        print("done embedding audio!")

    elif args.module == "init":
        initialize_directory.initialize_directory(
            data_path=args.data_dir,
            project_name=args.project_name,
            user_name=args.user_name,
            embedding_model=args.embedding_model,
        )
        print(f"Successfully initialized directory {args.data_dir}!")


if __name__ == "__main__":
    main()
