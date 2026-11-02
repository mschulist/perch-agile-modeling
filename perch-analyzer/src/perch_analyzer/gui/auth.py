"""GUI logins.

Accounts live in analyzer.db (`AnalyzerDB.create_user` and friends) and are
managed with `perch-analyzer add_user`, or from the login page while no
account exists yet. A signed-in browser carries its username in NiceGUI's
per-browser `app.storage.user`, which is signed with the secret in
`<data_dir>/.gui_secret`.

`app.storage.user` is tied to the request, so read `current_user()` on the
event loop (in the page or handler) and pass the name into worker threads.
"""

import functools
import inspect
import logging
import secrets
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.responses import RedirectResponse
from nicegui import app, context, ui

from perch_analyzer.gui import settings
from perch_analyzer.gui.background import load, run_blocking
from perch_analyzer.gui.components import page_layout
from perch_analyzer.gui.services import project
from perch_analyzer.gui.session import (
    LOGIN_PATH,
    USERNAME_KEY,
    current_user,
    require_user,
    sign_in,
)

logger = logging.getLogger(__name__)


def load_or_create_secret(data_dir: Path) -> str:
    """The key that signs session cookies, kept so logins survive restarts."""
    path = data_dir / settings.SECRET_FILENAME
    if path.exists():
        secret = path.read_text().strip()
        if secret:
            return secret
    secret = secrets.token_urlsafe(32)
    path.write_text(secret)
    path.chmod(0o600)
    return secret


def safe_redirect(target: str | None) -> str:
    """Only follow redirects to paths on this site."""
    if not target or not target.startswith("/") or target.startswith("//"):
        return "/"
    return target


def login_url(target: str) -> str:
    return f"{LOGIN_PATH}?redirect_to={quote(target, safe='')}"


def _requested_path() -> str:
    url = context.client.request.url
    return url.path + (f"?{url.query}" if url.query else "")


def guarded(builder: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a page builder so signed-out visitors are sent to the login page.

    `functools.wraps` keeps the builder's signature visible to NiceGUI, so path
    parameters such as `classifier_id: int` still arrive converted.

    This touches analyzer.db before `wait_for_client()`, which pages otherwise
    avoid. It is one indexed lookup, and it has to happen before anything is
    rendered. It means an account removed with `remove_user` loses access on
    its next page load.
    """

    @functools.wraps(builder)
    async def page(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if user is None or not project().analyzer_db.user_exists(user):
            if user is not None:
                app.storage.user.pop(USERNAME_KEY, None)
            return RedirectResponse(login_url(_requested_path()))
        result = builder(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    return page


# --- Pages -------------------------------------------------------------------


def _field(label: str, *, password: bool = False) -> ui.input:
    field = (
        ui.input(label, password=password)
        .props("outlined dense")
        .classes("w-full")
        .mark(label.lower().replace(" ", "_"))
    )
    return field


async def login_page(redirect_to: str = "/") -> RedirectResponse | None:
    target = safe_redirect(redirect_to)
    services = project()
    if current_user() is not None:
        return RedirectResponse(target)

    first_account = services.analyzer_db.count_users() == 0

    with (
        page_layout(show_nav=False),
        ui.card().classes("w-full max-w-[420px] mx-auto gap-3 p-6"),
    ):
        if first_account:
            ui.label("Create the first account").classes("text-2xl font-bold")
            ui.label(
                "This project has no logins yet. The account you create here "
                "can then add others with `perch-analyzer add_user`."
            ).classes("text-sm text-gray-500")
        else:
            ui.label("Sign in").classes("text-2xl font-bold")

        username = _field("Username")
        password = _field("Password", password=True)
        confirm = _field("Confirm password", password=True) if first_account else None
        error = ui.label().classes("text-red-600 text-sm")

        async def submit() -> None:
            name = (username.value or "").strip()
            secret = password.value or ""
            if first_account:
                if confirm is not None and secret != (confirm.value or ""):
                    error.text = "Passwords do not match."
                    return
                try:
                    await load(services.analyzer_db.create_user, name, secret)
                except ValueError as exc:
                    error.text = str(exc).capitalize() + "."
                    return
            else:
                (ok,) = await load(_verify, name, secret)
                if not ok:
                    error.text = "Invalid username or password."
                    return
            sign_in(name)
            logger.info("%s signed in", name)
            ui.navigate.to(target)

        last = confirm or password
        last.on("keydown.enter", submit)
        ui.button(
            "Create account" if first_account else "Sign in", on_click=submit
        ).props("no-caps").classes("w-full").mark("submit")
    return None


def _verify(username: str, password: str) -> tuple[bool]:
    # Wrapped in a tuple: `load` treats a falsy-looking `None` as cancellation,
    # and a bare `False` reads too much like it at the call site.
    return (project().analyzer_db.verify_user(username, password),)


async def account_page() -> None:
    user = require_user()
    services = project()

    with (
        page_layout("Account"),
        ui.card().classes("w-full max-w-[480px] gap-3"),
    ):
        ui.label(f"Signed in as {user}").classes("text-lg font-medium")
        ui.separator()
        ui.label("Change password").classes("text-xl font-semibold")
        current = _field("Current password", password=True)
        new = _field("New password", password=True)
        confirm = _field("Confirm new password", password=True)
        error = ui.label().classes("text-red-600 text-sm")

        async def change() -> None:
            error.text = ""
            if (new.value or "") != (confirm.value or ""):
                error.text = "New passwords do not match."
                return
            (ok,) = await load(_verify, user, current.value or "")
            if not ok:
                error.text = "Current password is wrong."
                return
            try:
                await run_blocking(
                    services.analyzer_db.set_password, user, new.value or ""
                )
            except ValueError as exc:
                error.text = str(exc).capitalize() + "."
                return
            for field in (current, new, confirm):
                field.value = ""
            ui.notify("Password changed", type="positive")

        ui.button("Change password", on_click=change).props("no-caps").mark(
            "change_password"
        )
