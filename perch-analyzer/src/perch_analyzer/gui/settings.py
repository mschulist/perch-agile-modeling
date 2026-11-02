"""GUI defaults that the CLI needs without importing NiceGUI.

`cli.gui_args` reads these to build `--help`. Keeping them out of `gui/app.py`
means building the parser, which every command and every GUI-launched job
subprocess does, never pays for importing NiceGUI.
"""

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

# Where NiceGUI keeps per-browser session storage, relative to the project.
STORAGE_DIRNAME = ".nicegui"
# The secret that signs session cookies, generated on first launch.
SECRET_FILENAME = ".gui_secret"
