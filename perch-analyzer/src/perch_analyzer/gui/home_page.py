from nicegui import ui

from perch_analyzer.gui.components import DOCS_URL, LOGO_URL, page_layout
from perch_analyzer.gui.services import project


def home_page() -> None:
    config = project().config
    with page_layout():
        with ui.row().classes("items-center gap-4"):
            ui.image(LOGO_URL).props("tag=img").classes("h-24 w-24 object-contain")
            with ui.column().classes("gap-1"):
                ui.label("Welcome to Perch Analyzer!").classes("text-3xl font-bold")
                ui.link("Read the documentation", DOCS_URL, new_tab=True).classes(
                    "text-lg"
                )

        with ui.card().classes("gap-1"):
            ui.label(f"Project: {config.project_name}").classes("text-lg font-medium")
            ui.label(f"User: {config.user_name}").classes("text-gray-600")
            ui.label(f"Embedding model: {config.embedding_model}").classes(
                "text-gray-600"
            )
            ui.label(f"Data directory: {config.data_path}").classes("text-gray-600")
