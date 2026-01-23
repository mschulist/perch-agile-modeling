import gradio as gr
from perch_analyzer.gui import annotate_page
from pathlib import Path


def home(data_dir: Path):
    with gr.Blocks() as homepage:
        gr.Markdown("Welcome to Perch Analyzer!")
    with homepage.route("Annotate"):
        annotate_page.annotate(data_dir)
    return homepage


if __name__ == "__main__":
    demo = home(Path("data"))
    demo.launch()
