from nicegui import ui

from perch_analyzer.gui.components import page_layout
from perch_analyzer.gui.services import project


def config_page() -> None:
    services = project()
    config = services.config

    with page_layout("Configuration"):
        with ui.card().classes("w-full"), ui.grid(columns=2).classes("w-full gap-4"):
            _read_only("Data Path", config.data_path)
            project_name = _text_input("Project Name", config.project_name)
            user_name = _text_input("User Name", config.user_name)
            _read_only("Embedding Model", config.embedding_model)
            api_key = _text_input("Xenocanto API Key", config.xenocanto_api_key)

        def save() -> None:
            config.project_name = project_name.value or ""
            config.user_name = user_name.value or ""
            config.xenocanto_api_key = api_key.value or ""
            config.to_file()
            ui.notify("Saved configuration", type="positive")

        ui.button("Save Changes", on_click=save).props("no-caps")


def _read_only(label: str, value: str) -> None:
    with ui.column().classes("gap-1"):
        ui.label(label).classes("text-sm font-bold")
        ui.label(value)


def _text_input(label: str, value: str) -> ui.input:
    with ui.column().classes("gap-1 w-full"):
        ui.label(label).classes("text-sm font-bold")
        return ui.input(value=value).props("dense outlined").classes("w-full")
