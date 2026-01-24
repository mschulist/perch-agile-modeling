import gradio as gr
from perch_analyzer.gui import annotate_page, examine_page, summary_page
from pathlib import Path
from perch_analyzer.config import config
from perch_analyzer.db import db
from perch_hoplite.db import sqlite_usearch_impl


def home(data_dir: Path):
    conf = config.Config.load(data_path=str(data_dir))

    hoplite_db = sqlite_usearch_impl.SQLiteUSearchDB.create(
        f"{conf.data_path}/{conf.hoplite_db_path}"
    )
    analyzer_db = db.AnalyzerDB(conf)

    with gr.Blocks() as homepage:
        gr.Markdown("Welcome to Perch Analyzer!")
    with homepage.route("Annotate"):
        annotate_page.annotate(
            config=conf, analyzer_db=analyzer_db, hoplite_db=hoplite_db
        )
    with homepage.route("Examine"):
        examine_page.examine(
            config=conf, analyzer_db=analyzer_db, hoplite_db=hoplite_db
        )
    with homepage.route("Summary"):
        summary_page.summary(
            config=conf, analyzer_db=analyzer_db, hoplite_db=hoplite_db
        )
    return homepage


if __name__ == "__main__":
    demo = home(Path("data"))
    demo.launch()
