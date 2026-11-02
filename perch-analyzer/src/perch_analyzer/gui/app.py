"""GUI entry point.

The whole GUI runs in this process on a single port: NiceGUI ships its
frontend prebuilt, so there is no node toolchain and nothing to compile before
the server can start.
"""

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import Response
from fastapi.responses import FileResponse
from nicegui import app, ui

from perch_analyzer.app_context import AppContext
from perch_analyzer.gui import (
    annotate_page,
    auth,
    classifier_output_page,
    classifiers_page,
    config_page,
    examine_page,
    home_page,
    jobs_page,
    single_classifier_page,
    summary_page,
)
from perch_analyzer.gui.components import LOGO_PATH, STATIC_DIR, STATIC_URL
from perch_analyzer.gui.services import ProjectServices, project, set_project
from perch_analyzer.gui.session import LOGIN_PATH, current_user
from perch_analyzer.gui.settings import (
    DEFAULT_RECONNECT_TIMEOUT,
    DEFAULT_RESPONSE_TIMEOUT,
)
from perch_analyzer.logging_config import setup_logging

logger = logging.getLogger(__name__)

TITLE = "Perch Analyzer"

# Every page except the login page requires a signed-in user.
PAGES: tuple[tuple[str, Callable[..., Any]], ...] = (
    ("/", home_page.home_page),
    ("/annotate", annotate_page.annotate_page),
    ("/examine", examine_page.examine_page),
    ("/classifiers", classifiers_page.classifiers_page),
    ("/jobs", jobs_page.jobs_page),
    ("/summary", summary_page.summary_page),
    ("/config", config_page.config_page),
    ("/account", auth.account_page),
    (
        "/single_classifier/{classifier_id}",
        single_classifier_page.single_classifier_page,
    ),
    ("/classifier_output/{output_id}", classifier_output_page.classifier_output_page),
)

DATA_URL = "/data"


def register_pages(
    response_timeout: float = DEFAULT_RESPONSE_TIMEOUT,
    reconnect_timeout: float = DEFAULT_RECONNECT_TIMEOUT,
) -> None:
    def page(route: str) -> Callable[[Callable[..., Any]], Any]:
        return ui.page(
            route,
            response_timeout=response_timeout,
            reconnect_timeout=reconnect_timeout,
        )

    page(LOGIN_PATH)(auth.login_page)
    for route, builder in PAGES:
        page(route)(auth.guarded(builder))

    # A route rather than `add_static_files`: it checks the session, and it
    # serves only rendered windows and target recordings. The project
    # directory also holds config.yaml (with the Xeno-canto API key) and both
    # databases.
    app.add_api_route(f"{DATA_URL}/{{path:path}}", serve_data, methods=["GET"])


def _servable_dirs() -> list[Path]:
    config = project().config
    data_dir = Path(config.data_path).resolve()
    return [
        (data_dir / config.precomputed_windows_dir).resolve(),
        (data_dir / config.target_recordings_dir).resolve(),
    ]


async def serve_data(path: str) -> Response:
    """Serve a window's audio or spectrogram (or a target recording)."""
    if current_user() is None:
        return Response(status_code=401)
    config = project().config
    file = (Path(config.data_path) / path).resolve()
    if not file.is_file() or not any(file.is_relative_to(d) for d in _servable_dirs()):
        return Response(status_code=404)
    return FileResponse(file)


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
    services = ProjectServices(ctx)
    set_project(services)
    register_pages(response_timeout, reconnect_timeout)
    app.add_static_files(STATIC_URL, STATIC_DIR)

    # Mark jobs a previous server left running as interrupted, now rather than
    # whenever someone first opens the Jobs page.
    _ = services.jobs
    app.on_shutdown(services.jobs.shutdown)

    if services.analyzer_db.count_users() == 0:
        logger.info(
            "no logins yet: the first visitor to the login page will create one"
        )

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
        storage_secret=auth.load_or_create_secret(ctx.data_dir),
    )
