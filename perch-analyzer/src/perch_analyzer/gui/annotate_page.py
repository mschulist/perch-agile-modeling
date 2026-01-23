import gradio as gr
from pathlib import Path


def annotate(data_dir: Path):
    with gr.Blocks() as annotate_blocks:
        gr.Markdown(f"Annotating data from: {data_dir}")
    return annotate_blocks
