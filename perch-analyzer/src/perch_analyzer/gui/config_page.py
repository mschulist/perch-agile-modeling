import reflex as rx
from perch_analyzer.gui.state import ConfigState


def config_page() -> rx.Component:
    return rx.container(
        rx.vstack(
            rx.heading("Configuration", size="8", margin_bottom="4"),
            rx.card(
                rx.grid(
                    rx.vstack(
                        rx.text("Data Path", weight="bold", size="2"),
                        rx.text(ConfigState.config.data_path, size="3"),
                        align="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Project Name", weight="bold", size="2"),
                        rx.input(
                            value=ConfigState.edit_project_name,
                            on_change=ConfigState.set_edit_project_name,
                            size="3",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("User Name", weight="bold", size="2"),
                        rx.input(
                            value=ConfigState.edit_user_name,
                            on_change=ConfigState.set_edit_user_name,
                            size="3",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Embedding Model", weight="bold", size="2"),
                        rx.text(ConfigState.config.embedding_model, size="3"),
                        align="start",
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Xenocanto API Key", weight="bold", size="2"),
                        rx.input(
                            value=ConfigState.edit_xenocanto_api_key,
                            on_change=ConfigState.set_edit_xenocanto_api_key,
                            size="3",
                            width="100%",
                        ),
                        align="start",
                        spacing="1",
                    ),
                    columns="2",
                    spacing="4",
                    width="100%",
                ),
            ),
            rx.button(
                "Save Changes",
                on_click=ConfigState.save_config_changes,
                size="3",
                margin_top="4",
            ),
            spacing="4",
            width="100%",
            padding="4",
        ),
        max_width="1200px",
    )
