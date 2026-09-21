"""Shared UI pieces.

Every page used to hand-roll its own label multiselect, window card and URL
building; they all live here now.
"""

from collections.abc import Awaitable, Callable, Iterable, Sequence
from contextlib import contextmanager
from pathlib import Path

from nicegui import context, ui

from perch_analyzer.gui.views import WindowView

STATIC_DIR = Path(__file__).parent / "static"
STATIC_URL = "/static"
LOGO_PATH = STATIC_DIR / "logo.png"
LOGO_URL = f"{STATIC_URL}/logo.png"
DOCS_URL = "https://mschulist.github.io/perch-agile-modeling/"

NAV_LINKS: tuple[tuple[str, str], ...] = (
    ("Annotate", "/annotate"),
    ("Examine", "/examine"),
    ("Classifiers", "/classifiers"),
    ("Audio Summary", "/summary"),
    ("Configuration", "/config"),
)

SaveHandler = Callable[[int, list[str]], Awaitable[None]]


@contextmanager
def page_layout(title: str | None = None):
    """Render the navbar and yield a centered container for the page body."""
    with ui.header().classes("items-center gap-6 px-6 py-3"):
        with ui.link(target="/").classes(
            "flex items-center gap-2 text-white no-underline"
        ):
            ui.image(LOGO_URL).props("tag=img").classes("h-9 w-9 object-contain")
            ui.label("Perch Analyzer").classes("text-lg font-bold")
        for text, target in NAV_LINKS:
            ui.link(text, target).classes("text-white no-underline hover:underline")

    with ui.column().classes("w-full max-w-[1500px] mx-auto p-6 gap-4") as container:
        if title:
            ui.label(title).classes("text-3xl font-bold")
        yield container


# The spectrogram PNGs are 640x480; capping width rather than height keeps
# them close to 1:1 instead of upscaling them into a blur.
SPECTROGRAM_MAX_WIDTH = "720px"


def spectrogram(src: str, max_width: str = SPECTROGRAM_MAX_WIDTH) -> ui.image:
    """Show a spectrogram at its natural aspect ratio.

    `ui.image` is Quasar's `q-img`, which fits the image into its own
    aspect-ratio box and crops the overflow; `tag=img` renders a plain `<img>`
    instead. Constraining width and leaving height automatic avoids the
    letterboxing that a height cap would produce.
    """
    return (
        ui.image(src)
        .props("tag=img")
        .classes(f"w-full max-w-[{max_width}] h-auto mx-auto")
    )


def window_media(
    spec_url: str, audio_url: str, max_width: str = SPECTROGRAM_MAX_WIDTH
) -> None:
    """A spectrogram with its audio player, centered and the same width."""
    spectrogram(spec_url, max_width=max_width)
    ui.audio(audio_url).classes(f"w-full max-w-[{max_width}] mx-auto")


async def wait_for_client() -> None:
    """Hand the page shell to the browser before doing anything slow.

    NiceGUI runs a page function to completion before responding, so work done
    before this point counts against the page's `response_timeout` and any
    spinner built before it is never actually seen.
    """
    await context.client.connected()


def loading(message: str = "Loading...") -> ui.column:
    """A centered spinner, returned so the caller can delete it when done."""
    with ui.column().classes("w-full items-center gap-2 p-8") as column:
        ui.spinner(size="lg")
        ui.label(message).classes("text-gray-500")
    return column


SELECTED_CLASSES = "bg-primary text-white"


class SearchableList:
    """A filter box over a scrollable list of clickable items.

    Selecting an item only restyles the existing buttons. Rebuilding the list
    here would delete the very button whose click handler is running, and any
    element created afterwards in the ambient slot context would then fail to
    resolve its (garbage-collected) parent.
    """

    def __init__(
        self,
        items: Sequence[str],
        on_select: Callable[[str], object],
        *,
        placeholder: str = "Search labels...",
        selected: str | None = None,
        empty_message: str = "No labels found",
    ):
        self.items = list(items)
        self.on_select = on_select
        self.selected = selected
        self.empty_message = empty_message
        self._buttons: dict[str, ui.button] = {}

        with ui.column().classes("w-full gap-2"):
            # The search box lives outside the list, so rebuilding the list
            # from its handler never deletes the handler's own element.
            self._search = (
                ui.input(placeholder=placeholder)
                .props("dense clearable")
                .classes("w-full")
            )
            self._list = ui.column().classes(
                "w-full gap-1 overflow-y-auto max-h-[600px] border rounded p-2"
            )
        self._search.on_value_change(self._render)
        self._render()

    def set_items(self, items: Sequence[str]) -> None:
        self.items = list(items)
        self._render()

    def set_selected(self, item: str | None) -> None:
        """Highlight `item`, leaving the buttons themselves in place."""
        self.selected = item
        for value, button in self._buttons.items():
            self._apply_selection(button, value == item)

    @staticmethod
    def _apply_selection(button: ui.button, is_selected: bool) -> None:
        if is_selected:
            button.classes(add=SELECTED_CLASSES)
        else:
            button.classes(remove=SELECTED_CLASSES)

    def _render(self) -> None:
        query = (self._search.value or "").lower()
        matches = [item for item in self.items if query in item.lower()]
        self._buttons = {}
        self._list.clear()
        with self._list:
            if not matches:
                ui.label(self.empty_message).classes("text-gray-500 text-sm")
                return
            for item in matches:
                button = (
                    ui.button(item, on_click=lambda i=item: self.on_select(i))
                    .props("flat no-caps dense align=left")
                    .classes("w-full justify-start")
                )
                self._apply_selection(button, item == self.selected)
                self._buttons[item] = button


def label_editor(
    all_labels: Iterable[str],
    value: Sequence[str],
    on_change: Callable[[list[str]], object] | None = None,
) -> ui.select:
    """A multiselect that can also create labels that do not exist yet."""
    options = sorted({*all_labels, *value})
    select = (
        ui.select(
            options=options,
            value=list(value),
            multiple=True,
            with_input=True,
            new_value_mode="add-unique",
            label="Labels",
        )
        .props("use-chips dense")
        .classes("w-full")
    )
    if on_change is not None:
        select.on_value_change(lambda event: on_change(list(event.value or [])))
    return select


class WindowCard:
    """A spectrogram, an audio player and the window's labels.

    Pass `on_save` to make the labels editable.
    """

    def __init__(
        self,
        view: WindowView,
        all_labels: Sequence[str],
        on_save: SaveHandler | None = None,
    ):
        self.view = view
        self.all_labels = all_labels
        self.on_save = on_save
        self._build()

    def _build(self) -> None:
        view = self.view
        with ui.card().classes("w-full max-w-[780px] p-3 gap-2") as self.container:
            ui.label(view.filename).classes("text-xl font-semibold")

            with ui.row().classes("gap-6 items-center text-sm"):
                ui.label(f"Offsets: {view.offsets_label}").classes("font-medium")
                if view.classifier_label is not None:
                    ui.label(f"Classifier label: {view.classifier_label}").classes(
                        "font-medium"
                    )
                if view.logit is not None:
                    ui.label(f"Logit: {view.logit:.4f}").classes("font-medium")

            self.chips = ui.row().classes("gap-1 items-center min-h-[2rem]")
            self._render_chips()

            if self.on_save is not None:
                self._build_editor()

            window_media(view.spec_url, view.audio_url)

    def _render_chips(self) -> None:
        self.chips.clear()
        with self.chips:
            if not self.view.labels:
                ui.label("No labels").classes("text-gray-500 text-sm")
            for label in self.view.labels:
                ui.chip(label).props("outline dense")

    def _build_editor(self) -> None:
        self.edit_button = ui.button("Edit labels", on_click=self._start_editing).props(
            "outline dense no-caps"
        )

        self.editor = ui.column().classes("w-full gap-2")
        self.editor.visible = False
        with self.editor:
            self.select = label_editor(self.all_labels, self.view.labels)
            with ui.row().classes("gap-2"):
                ui.button("Save", on_click=self._save).props("dense no-caps")
                ui.button("Cancel", on_click=self._cancel).props(
                    "outline dense no-caps"
                )

    def _start_editing(self) -> None:
        self.select.value = list(self.view.labels)
        self.edit_button.visible = False
        self.editor.visible = True

    def _cancel(self) -> None:
        self.editor.visible = False
        self.edit_button.visible = True

    async def _save(self) -> None:
        assert self.on_save is not None
        labels = sorted(self.select.value or [])
        # Update our own UI before handing off: `on_save` is allowed to hide or
        # discard this card, and touching a deleted element afterwards warns.
        self.view.labels = labels
        self._render_chips()
        self._cancel()
        await self.on_save(self.view.window_id, labels)

    def hide(self) -> None:
        """Take this card off the page without deleting it."""
        self.container.visible = False
