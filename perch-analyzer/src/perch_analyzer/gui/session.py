"""Who is signed in to this browser.

Kept apart from `gui/auth.py` (the login pages) so that `components.py` can
show the signed-in user without an import cycle.
"""

from nicegui import app, ui

USERNAME_KEY = "username"
LOGIN_PATH = "/login"


def current_user() -> str | None:
    """The signed-in username, or None.

    `app.storage.user` is tied to the request, so this only works on the event
    loop. Read it in the page or handler and pass the name into worker threads.
    """
    value = app.storage.user.get(USERNAME_KEY)
    return value if isinstance(value, str) and value else None


def require_user() -> str:
    """The signed-in username, for code that only runs on guarded pages."""
    user = current_user()
    if user is None:
        raise RuntimeError("no user is signed in")
    return user


def sign_in(username: str) -> None:
    app.storage.user[USERNAME_KEY] = username


def sign_out() -> None:
    app.storage.user.pop(USERNAME_KEY, None)
    ui.navigate.to(LOGIN_PATH)
