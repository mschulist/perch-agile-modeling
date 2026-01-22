import gradio as gr
from perch_analyzer.gui import embed_page


with gr.Blocks() as homepage:
    "Welcome to Perch Analyzer!"
with homepage.route("Embed"):
    embed_page.embed.render()
