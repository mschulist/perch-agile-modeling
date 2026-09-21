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

# NiceGUI defaults both of these to 3s, which a project large enough to need
# spectrograms rendered on demand blows through easily.
#
# `response_timeout` bounds how long a page function may take to build. Pages
# call `wait_for_client()` before touching the databases so the slow part is
# outside this budget, but rendering can still be slow before the handshake
# completes on a loaded machine.
DEFAULT_RESPONSE_TIMEOUT = 60.0
# `reconnect_timeout` is how long the server keeps a client's state alive while
# the browser is away. Generous, so a tab that stalls during a long render is
# not thrown away mid-annotation.
DEFAULT_RECONNECT_TIMEOUT = 30.0


PAGES: tuple[tuple[str, object], ...] = (
    ("/", home_page.home_page),
    ("/annotate", annotate_page.annotate_page),
    ("/examine", examine_page.examine_page),
    ("/classifiers", classifiers_page.classifiers_page),
    ("/summary", summary_page.summary_page),
    ("/config", config_page.config_page),
    (
        "/single_classifier/{classifier_id}",
        single_classifier_page.single_classifier_page,
    ),
    ("/classifier_output/{output_id}", classifier_output_page.classifier_output_page),
)


def register_pages(
    response_timeout: float = DEFAULT_RESPONSE_TIMEOUT,
    reconnect_timeout: float = DEFAULT_RECONNECT_TIMEOUT,
) -> None:
    for route, builder in PAGES:
        ui.page(
            route,
            response_timeout=response_timeout,
            reconnect_timeout=reconnect_timeout,
        )(builder)  # type: ignore[arg-type]


def launch(
    ctx: AppContext,
    host: str = "127.0.0.1",
    port: int = 8000,
    show: bool = True,
    reload: bool = False,
    response_timeout: float = DEFAULT_RESPONSE_TIMEOUT,
    reconnect_timeout: float = DEFAULT_RECONNECT_TIMEOUT,
) -> None:
    setup_logging(ctx.data_dir)
    set_project(ProjectServices(ctx))
    register_pages(response_timeout, reconnect_timeout)

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
        reconnect_timeout=reconnect_timeout,
        favicon=LOGO_PATH,
        uvicorn_logging_level="warning",
        show_welcome_message=False,
    )
