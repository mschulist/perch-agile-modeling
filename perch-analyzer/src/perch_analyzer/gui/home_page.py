import gradio as gr
from perch_analyzer.gui import embed_page


with gr.Blocks() as demo:
    "Welcome to Perch Analyzer!"
with demo.route("Embed"):
    embed_page.demo.render()
