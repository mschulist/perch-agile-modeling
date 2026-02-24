import argparse
from perch_analyzer.config import initialize_directory, config
from pathlib import Path
from perch_analyzer.embed import embed
from perch_analyzer.target_recordings import target_recordings
from perch_analyzer.db import db
from perch_analyzer.search import search
from perch_analyzer.classify import classifier, classify, classifier_outputs
from perch_analyzer.gui import gui_loader
from perch_hoplite.db import sqlite_usearch_impl
import logging


def setup_logging(data_dir: Path):
    log_path = data_dir / "perch_analyzer.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.FileHandler(log_path)],
    )


def check_init_and_raise_error(data_dir: Path):
    if not initialize_directory.check_initialized(data_dir):
        raise ValueError(
            f"data directory {data_dir} is not initialized yet, run perch-analyzer init --data_dir={data_dir}"
        )
    setup_logging(data_dir)


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

    # Create classifier subcommand
    create_classifier_parser = subparsers.add_parser(
        "create_classifier", help="Create a custom classifier"
    )
    create_classifier_parser.add_argument("--data_dir", type=Path, required=True)
    create_classifier_parser.add_argument(
        "--throwaway_classes", nargs="*", type=str, default=[]
    )
    create_classifier_parser.add_argument("--train_ratio", type=float, default=0.8)
    create_classifier_parser.add_argument(
        "--max_train_examples_per_label", type=int, default=100
    )
    create_classifier_parser.add_argument("--learning_rate", type=float, default=1e-3)
    create_classifier_parser.add_argument("--weak_neg_rate", type=float, default=0.05)
    create_classifier_parser.add_argument("--num_train_steps", type=int, default=128)

    # Run classifier subcommand
    run_classifier_parser = subparsers.add_parser(
        "run_classifier", help="Run a custom classifier on the data"
    )
    run_classifier_parser.add_argument("--data_dir", type=Path, required=True)
    run_classifier_parser.add_argument("--classifier_id", type=int, required=True)

    # Set Xeno-canto API key subcommand
    set_xc_api_key_parser = subparsers.add_parser(
        "set_xc_api_key", help="Set the Xeno-canto API key for the given project"
    )
    set_xc_api_key_parser.add_argument("--data_dir", type=Path, required=True)
    set_xc_api_key_parser.add_argument("--xc_api_key", type=str, required=True)

    # Gather classifier outputs subcommand
    gather_classifier_outputs_parser = subparsers.add_parser(
        "gather_classifier_outputs",
        help="Gather outputs from classifier outputs for a particular label and logit range",
    )
    gather_classifier_outputs_parser.add_argument(
        "--data_dir", type=Path, required=True
    )
    gather_classifier_outputs_parser.add_argument(
        "--classifier_output_id", type=int, required=True
    )
    gather_classifier_outputs_parser.add_argument(
        "--min_logit", type=float, required=True
    )
    gather_classifier_outputs_parser.add_argument(
        "--max_logit", type=float, required=True
    )
    gather_classifier_outputs_parser.add_argument("--label", type=str, required=True)
    gather_classifier_outputs_parser.add_argument("--num_windows", type=int, default=1)

    # Parse arguments
    args = parser.parse_args()

    # Route to appropriate section
    if args.module == "gui":
        check_init_and_raise_error(args.data_dir)
        gui_loader.start_gui(str(args.data_dir))
    elif args.module == "embed":
        check_init_and_raise_error(args.data_dir)
        # update the config with the ARU path
        conf = config.Config.load(args.data_dir)

        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )

        logger = logging.getLogger(__name__)

        logger.info("embedding audio...this may take a while")
        print("embedding audio...this may take a while")
        embed.embed_audio(
            config=conf,
            hoplite_db=hoplite_db,
            ARU_base_path=args.ARU_base_path,
            ARU_file_glob=args.ARU_file_glob,
        )
        logger.info("done embedding audio!")
        print("done embedding audio!")
    elif args.module == "init":
        initialize_directory.initialize_directory(
            data_path=args.data_dir,
            project_name=args.project_name,
            user_name=args.user_name,
            embedding_model=args.embedding_model,
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Successfully initialized directory {args.data_dir}!")
        print(f"Successfully initialized directory {args.data_dir}!")
    elif args.module == "target_recordings":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        logger = logging.getLogger(__name__)

        logger.info("adding recordings from xenocanto")
        print("adding recordings from xenocanto")

        target_recordings.add_target_recording_from_xc(
            config=conf,
            db=analyzer_db,
            ebird_6_code=args.ebird_code,
            call_type=args.call_type,
            num_recordings=args.num_recordings,
        )

        logger.info("finished adding recordings!")
        print("finished adding recordings!")
    if args.module == "search":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )
        logger = logging.getLogger(__name__)
        logger.info("searching recordings")
        print("searching recordings")

        search.search_using_target_recordings(
            config=conf,
            db=analyzer_db,
            hoplite_db=hoplite_db,
            num_per_target_recording=args.num_per_target_recording,
        )

        logger.info("finished searching recordings!")
        print("finished searching recordings!")

    if args.module == "create_classifier":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )
        logger = logging.getLogger(__name__)
        logger.info("making custom classifier")
        print("making custom classifier")
        classifier.train_classifier(
            config=conf,
            hoplite_db=hoplite_db,
            analyzer_db=analyzer_db,
            throwaway_classes=args.throwaway_classes,
            train_ratio=args.train_ratio,
            max_train_examples_per_label=args.max_train_examples_per_label,
            learning_rate=args.learning_rate,
            weak_neg_rate=args.weak_neg_rate,
            num_train_steps=args.num_train_steps,
        )

        logger.info("done making classifier!")
        print("done making classifier!")
    if args.module == "run_classifier":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
            str(Path(conf.data_path) / conf.hoplite_db_path)
        )
        logger = logging.getLogger(__name__)

        logger.info("running classifier!")
        print("running classifier!")
        classify.classify(
            classifier_id=args.classifier_id,
            hoplite_db=hoplite_db,
            analyzer_db=analyzer_db,
        )
        logger.info("done running classifier")
        print("done running classifier")
    if args.module == "set_xc_api_key":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)

        conf.xenocanto_api_key = args.xc_api_key
        conf.to_file()
        logger = logging.getLogger(__name__)

        logger.info("successfully updated Xeno-canto API key")
        print("successfully updated Xeno-canto API key")
    if args.module == "gather_classifier_outputs":
        check_init_and_raise_error(args.data_dir)
        conf = config.Config.load(args.data_dir)
        analyzer_db = db.AnalyzerDB(conf)
        classifier_outputs.gather_classifier_output_windows(
            analyzer_db=analyzer_db,
            classifier_output_id=args.classifier_output_id,
            min_logit=args.min_logit,
            max_logit=args.max_logit,
            label=args.label,
            num_windows=args.num_windows,
        )
        logger = logging.getLogger(__name__)

        logger.info("successfully gathered target recordings")
        print("successfully gathered target recordings")


if __name__ == "__main__":
    main()
