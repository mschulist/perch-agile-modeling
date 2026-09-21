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
uv run pytest           # 26 tests; builds every GUI page headlessly
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
- **analyzer** (`<data_dir>/analyzer.db`) — classifiers, classifier outputs and
  target recordings. SQLAlchemy, ours, in `db/tables.py` and `db/db.py`.

A project directory also holds `config.yaml`, `classifiers/`,
`classifier_outputs/`, `target_recordings/` and `precomputed_windows/`.

### Modules

```
cli.py              argparse; a Command table, one handler per subcommand
app_context.py      AppContext: lazily opens config + both databases
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

### Long jobs stay on the CLI

`embed`, `search`, `create_classifier` and `run_classifier` are CLI-only by
design. The GUI is for annotating and reviewing. Don't add job launching to it
without asking.

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

## Gotchas

- perch-hoplite is pinned to a git revision in `[tool.uv.sources]`. Its API
  moves; check signatures against `.venv/lib/python3.12/site-packages/perch_hoplite/`
  rather than trusting docs after a bump.
- `db/tables.py` still carries `max_train_examples_per_label`. It is vestigial
  (hoplite dropped it) and kept only because existing databases declare the
  column `NOT NULL`.
- `xenocanto.get_xc_ids` retries `while status_code != 200` and only breaks out
  on 401, so a 404 or 500 loops forever. Known bug, not yet fixed.
- Test data under `perch-analyzer/data/` is gitignored and holds a real
  Xeno-canto API key. Don't copy it into anything committed.
