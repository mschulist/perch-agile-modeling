import reflex as rx
import os
from pathlib import Path
from starlette.staticfiles import StaticFiles
from perch_analyzer.gui import (
    summary_page,
    classifiers_page,
    examine_page,
    annotate_page,
    config_page,
    single_classifier_page,
    classifier_output_page,
)


def navbar_link(text: str, url: str) -> rx.Component:
    return rx.link(rx.text(text, size="4", weight="medium"), href=url)


def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            navbar_link("Home", "/"),
            navbar_link("Annotate", "/annotate"),
            navbar_link("Examine", "/examine"),
            navbar_link("Classifiers", "/classifiers"),
            navbar_link("Audio Summary", "/summary"),
            navbar_link("Configuration", "/config"),
            spacing="4",
        ),
        padding="2em",
    )


def with_navbar(page_content: rx.Component) -> rx.Component:
    """Wrapper that adds navbar to any page content."""
    return rx.vstack(navbar(), page_content, spacing="0", width="100%", align="center")


def index():
    return rx.text("Welcome to Perch Analyzer!")


app = rx.App()

app.add_page(lambda: with_navbar(index()), route="/")
app.add_page(lambda: with_navbar(annotate_page.annotate()), route="/annotate")
app.add_page(lambda: with_navbar(examine_page.examine()), route="/examine")
app.add_page(lambda: with_navbar(classifiers_page.classifiers()), route="/classifiers")
app.add_page(lambda: with_navbar(summary_page.summary()), route="/summary")
app.add_page(lambda: with_navbar(config_page.config_page()), route="/config")
app.add_page(
    lambda: with_navbar(single_classifier_page.single_classifier_page()),
    route="/single_classifier/[id]",
)
app.add_page(
    lambda: with_navbar(classifier_output_page.classifier_output_page()),
    route="/classifier_output/[id]",
)

# Mount the data directory as static files
# Get data path from environment variable, fallback to "data" for backwards compatibility
data_path = Path(os.environ.get("PERCH_ANALYZER_DATA_DIR", "data")).absolute()
app._api.mount("/data", StaticFiles(directory=str(data_path)), name="data")  # type: ignore
