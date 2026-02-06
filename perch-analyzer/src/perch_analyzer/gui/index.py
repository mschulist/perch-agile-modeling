import reflex as rx
from pathlib import Path
from starlette.staticfiles import StaticFiles
from perch_analyzer.gui import (
    summary_page,
    classifiers_page,
    examine_page,
    annotate_page,
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
            navbar_link("Summary", "/summary"),
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

# Mount the data directory as static files
data_path = Path("data").absolute()
app._api.mount("/data", StaticFiles(directory=str(data_path)), name="data")  # type: ignore
