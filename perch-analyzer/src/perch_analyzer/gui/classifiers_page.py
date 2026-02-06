import gradio as gr
from perch_analyzer.db import db


def classifiers(db: db.AnalyzerDB):
    all_classifiers = db.get_all_classifiers()

    with gr.Blocks() as classifiers_block:
        gr.Markdown("# Trained Classifiers", elem_classes="text-2xl")

        if not all_classifiers:
            gr.Markdown("*No classifiers found. Train a classifier to see it here.*")

        for classifier in all_classifiers:
            formatted_date = classifier.datetime.strftime("%B %d, %Y at %I:%M %p")

            # Extract metrics
            auc_roc = classifier.metrics.get("roc_auc", "N/A")
            cmap = classifier.metrics.get("cmap", "N/A")
            top1_acc = classifier.metrics.get("top1_acc", "N/A")

            # Format metrics with 4 decimal places if they're numeric
            if isinstance(auc_roc, (int, float)):
                auc_roc = f"{auc_roc:.4f}"
            if isinstance(cmap, (int, float)):
                cmap = f"{cmap:.4f}"
            if isinstance(top1_acc, (int, float)):
                top1_acc = f"{top1_acc:.4f}"

            with gr.Group():
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown(f"### Classifier id: {classifier.id}")
                        gr.Markdown(f"*{formatted_date}*")
                    with gr.Column(scale=2):
                        with gr.Row():
                            gr.Markdown("### Performance Metrics")
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown(f"**AUC-ROC**  \n## {auc_roc}")
                            with gr.Column():
                                gr.Markdown(f"**CMAP**  \n## {cmap}")
                            with gr.Column():
                                gr.Markdown(f"**Top-1 Accuracy**  \n## {top1_acc}")

        return classifiers_block
