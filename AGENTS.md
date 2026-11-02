# Perch Analyzer

Bioacoustics tooling for the *agile modeling* workflow: embed a pile of ARU
recordings, search them with known target recordings, annotate the hits, train
a small classifier on those annotations, and run it back over the whole
dataset. Built on [perch-hoplite](https://github.com/google-research/perch-hoplite).

## Layout

| Path | What it is |
| --- | --- |
| `perch-analyzer/` | The Python package. **This is the project.** |
| `perch-analyzer-docs/` | Docusaurus user documentation. Update it when CLI flags or GUI pages change. |
| `legacy/` | The previous Next.js + Firebase implementation. Not maintained; do not extend. |

Work in `perch-analyzer/` unless the task is specifically about the docs site.

## Getting set up

```bash
cd perch-analyzer
uv sync                 # installs deps and the `perch-analyzer` entry point (editable)
```

`uv sync` is required — the project declares `[build-system]` and
`tool.uv.package = true`, and without it the `perch-analyzer` command will not
exist.

## Checks to run before you finish

```bash
cd perch-analyzer
uv run pytest           # builds every GUI page headlessly and runs real job subprocesses
uvx ruff format src tests scripts
uvx ruff check src tests
uvx pyrefly check       # reads [tool.pyrefly] from pyproject.toml; must be 0 errors
```

All three are configured in `pyproject.toml`; run them without extra flags so
you get the project's settings rather than the tools' defaults.

## Architecture

### Two databases

- **hoplite** (`<data_dir>/hoplite/`) — recordings, windows, embedding vectors
  and annotations. SQLite plus a usearch vector index, owned by perch-hoplite.
  Queried through `config_dict` filters; see `HopliteDBInterface`'s docstring
  for the filter grammar (`eq`, `isin`, `approx`, ...).
- **analyzer** (`<data_dir>/analyzer.db`) — classifiers, classifier outputs,
  target recordings and GUI logins (`users`). SQLAlchemy, ours, in
  `db/tables.py` and `db/db.py`. Keep schema changes additive: `create_all`
  adds new tables to old databases but never alters existing ones.

A project directory also holds `config.yaml`, `classifiers/`,
`classifier_outputs/`, `target_recordings/`, `precomputed_windows/`, and,
once the GUI has run, `jobs/` (one `<id>.json` + `<id>.log` per job),
`.gui_secret` (signs session cookies) and `.nicegui/` (session storage).

### Modules

```
cli.py              argparse; a Command table, one handler per subcommand.
                    Also the GUI bridge: gui_commands, command_arguments, to_argv
app_context.py      AppContext: lazily opens config + both databases
auth.py             salted scrypt password hashing (stdlib only)
jobs.py             JobManager: runs gui=True commands as subprocesses
logging_config.py   console + file logging
config/             Config (pydantic/yaml), project initialization
embed/              wraps perch_hoplite EmbedWorker
target_recordings/  Xeno-canto download + peak slicing (audio_utils.py and
                    signal.py are ported from Perch — leave their logic alone)
search/             embed a target recording, find nearest windows, mark them UNCERTAIN
classify/           linear_model.py (numpy inference), classifier.py (TF training),
                    classify.py (batch inference to parquet), classifier_outputs.py
examine/            annotation queries, and rendering windows to .wav + .png
db/                 AnalyzerDB
gui/                NiceGUI app
```

## Conventions that matter

**Do not import TensorFlow at module scope.** `perch_hoplite.agile.classifier`
pulls in TensorFlow, which costs ~4.5s. Training is the only thing that needs
it, so it is imported *inside* `classify/classifier.py:train_classifier()`.
Everything else — including loading and running a trained classifier — goes
through `classify/linear_model.py`, which is pure numpy and writes a JSON
format byte-identical to hoplite's. `tests/test_linear_model.py` guards this;
keep `perch-analyzer --help` under ~0.2s.

**Commands import their own dependencies.** CLI handlers import their module
lazily so `init` never pays for jax, polars or TensorFlow. `AppContext` opens
the config and each database on first access.

**Building the parser must not import NiceGUI.** `cli.gui_args` reads its
defaults from `gui/settings.py` for this reason. Every GUI job builds the
parser in a fresh process, and NiceGUI reads `NICEGUI_STORAGE_PATH` when it is
first imported, which `handle_gui` sets. `tests/test_cli.py` guards this.

**Leave the root logger alone.** `logging_config.setup_logging` pins root to
WARNING on purpose: perch-hoplite logs every SQL statement it executes through
absl at INFO. Log through `logging.getLogger(__name__)`, never
`logging.info(...)`.

**Query in bulk.** The hoplite API makes per-row lookups easy and slow. Prefer
one `get_all_windows(filter=isin(...))` over a loop of `get_window`; see
`examine/examine_annotations.get_windows_with_annotations` for the pattern.

**SQLite connections cannot cross threads.** Call `hoplite_db.thread_split()`
in any worker thread. `gui/services.py` caches one handle per thread.

### GUI notes

The GUI is NiceGUI, in-process, on one port. There is no build step and no
node toolchain — that is the point, so keep it that way.

- Pages are registered in `gui/app.py` and run per request, so they always read
  fresh data. Do not hoist database work to module import time.
- Blocking work goes through `gui/background.py`: `load()` for callbacks that
  return a value (it raises `CancelledError` rather than handing back NiceGUI's
  ambiguous `None`), `run_blocking()` for callbacks that return nothing.
  Passing a void callback to `load()` raises `CancelledError` on every call,
  and because that is a `BaseException` it is not logged.
- **Never delete the element whose handler is running.** Clicking a list item
  must not rebuild the list, and a paging handler must not recreate the pager;
  NiceGUI holds the parent by weakref, so anything created afterwards in the
  ambient slot context dies with "The parent element this slot belongs to has
  been deleted". Restyle in place (`SearchableList.set_selected`), resize in
  place (`pager.props(f"max={n}")`), or hide (`WindowCard.hide()`).
- Pages must `await wait_for_client()` before touching the databases. Until
  that returns the browser has nothing, so spinners are invisible and the work
  counts against the page's `response_timeout`.
- `ui.image` is Quasar's `q-img` and crops to its own aspect-ratio box. Use
  `gui/components.spectrogram()` (which passes `tag=img`) for spectrograms.
- Shared widgets live in `gui/components.py`. Add to it rather than
  re-implementing a label picker per page.
- Window lists are paginated; load ids first, then details for the visible page
  only.
- Page timeouts default to 60s (build) and 30s (reconnect), overridable with
  `--page_timeout` and `--reconnect_timeout`. NiceGUI's own 3s defaults are far
  too short once spectrograms are rendered on demand.

### Logins

- Every page except `/login` is wrapped by `gui/auth.guarded` in
  `register_pages`. The wrapper returns a `RedirectResponse` to the login page
  when nobody is signed in, or when the account has since been removed. A new
  page needs no extra code, as long as it is listed in `gui/app.PAGES`.
- The signed-in name lives in `app.storage.user`, reached through
  `gui/session.current_user()`. That storage is bound to the request, so read
  it on the event loop and pass the name into `load()`/`run_blocking()`
  callbacks. Never read it inside a worker thread.
- Labels written from the GUI are credited to that name
  (`update_labels(..., provenance=user)`). `config.user_name` is only the CLI's
  identity.
- `/data/...` is a route (`gui/app.serve_data`), not static files. It requires
  a login and serves only `precomputed_windows/` and `target_recordings/`. The
  project directory also holds `config.yaml` (with the Xeno-canto API key) and
  both databases.
- There are no roles and no locking of windows between annotators, by design.

### Jobs: which commands the GUI may start

Commands with `gui=True` in `cli.COMMANDS` (`target_recordings`, `search`,
`run_classifier`, `gather_classifier_outputs`) can be started from the GUI.
`embed` and `create_classifier` stay CLI-only because they want a GPU and
careful tuning. Don't flip them without asking.

- `JobManager` runs `python -m perch_analyzer <cmd>` as a subprocess, so heavy
  imports and models never load into the GUI process. Status and output are
  kept in files under `jobs/` (no DB table). A command can only have one run
  at a time.
- `gui/job_forms.JobForm` builds its fields from the command's argparse
  actions, so a new flag shows up in the GUI automatically. Pass `fixed=` to
  pre-set a field on a contextual page, and `options=` to offer choices.
- A job that writes to hoplite must commit in small transactions. Python's
  sqlite3 holds the write lock from the first INSERT until commit, and a
  long-held lock makes GUI label saves fail with "database is locked". See
  `search/search.py`.

## Testing

`tests/conftest.py` builds a real project on disk — hoplite database, windows
cut from `ARU_test_data/`, annotations, a classifier and a classifier output —
and exposes it as `project_dir`, `ctx` and `gui`. Its dimensions live in
`tests/project_shape.py` so tests can assert against them. The `gui` fixture
wires the pages up to NiceGUI's simulated client, so page tests exercise the
real server-side rendering without a browser.

`tests/test_gui_interactions.py` clicks through the pages. Add to it when you
touch an event handler: rendering a page proves far less than driving it, and
every GUI bug found so far has been in a handler, not in a first render.

Commands that need the 779 MB perch_v2 download or the Xeno-canto API
(`embed`, `search`, `target_recordings`) are not covered; verify those by hand.
`tests/test_jobs.py` and the job tests in `test_gui_interactions.py` run
`gather_classifier_outputs` and `run_classifier` for real, as subprocesses,
against the fixture project, which includes a small classifier output parquet.

The `gui` fixture signs in as `conftest.TEST_USERNAME`. Use
`gui_unauthenticated` to test the login flow itself.

## Gotchas

- perch-hoplite is pinned to a git revision in `[tool.uv.sources]`. Its API
  moves; check signatures against `.venv/lib/python3.12/site-packages/perch_hoplite/`
  rather than trusting docs after a bump.
- `db/tables.py` still carries `max_train_examples_per_label`. It is vestigial
  (hoplite dropped it) and kept only because existing databases declare the
  column `NOT NULL`.
- `xenocanto.get_xc_ids` retries only on 429/5xx, at most `MAX_ATTEMPTS`
  times. It used to loop forever on a 404, which would hang a GUI job.
- Test data under `perch-analyzer/data/` is gitignored and holds a real
  Xeno-canto API key. Don't copy it into anything committed.
