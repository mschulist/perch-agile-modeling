"""GUI entry point.

The whole GUI runs in this process on a single port: NiceGUI ships its
frontend prebuilt, so there is no node toolchain and nothing to compile before
the server can start.
"""

import logging

from nicegui import app, ui

from perch_analyzer.app_context import AppContext
from perch_analyzer.gui import (
    annotate_page,
    classifier_output_page,
    classifiers_page,
    config_page,
    examine_page,
    home_page,
    single_classifier_page,
    summary_page,
)
from perch_analyzer.gui.components import LOGO_PATH, STATIC_DIR, STATIC_URL
from perch_analyzer.gui.services import ProjectServices, set_project
from perch_analyzer.logging_config import setup_logging

logger = logging.getLogger(__name__)

TITLE = "Perch Analyzer"


def register_pages() -> None:
    ui.page("/")(home_page.home_page)
    ui.page("/annotate")(annotate_page.annotate_page)
    ui.page("/examine")(examine_page.examine_page)
    ui.page("/classifiers")(classifiers_page.classifiers_page)
    ui.page("/summary")(summary_page.summary_page)
    ui.page("/config")(config_page.config_page)
    ui.page("/single_classifier/{classifier_id}")(
        single_classifier_page.single_classifier_page
    )
    ui.page("/classifier_output/{output_id}")(
        classifier_output_page.classifier_output_page
    )


def launch(
    ctx: AppContext,
    host: str = "127.0.0.1",
    port: int = 8000,
    show: bool = True,
    reload: bool = False,
) -> None:
    setup_logging(ctx.data_dir)
    set_project(ProjectServices(ctx))
    register_pages()

    # Spectrograms and window audio are read straight out of the project
    # directory, from the same origin as the pages.
    app.add_static_files("/data", ctx.data_dir)
    app.add_static_files(STATIC_URL, STATIC_DIR)

    logger.info("serving %s from %s", TITLE, ctx.data_dir)
    ui.run(
        host=host,
        port=port,
        title=TITLE,
        show=show,
        reload=reload,
        favicon=LOGO_PATH,
        uvicorn_logging_level="warning",
        show_welcome_message=False,
    )
