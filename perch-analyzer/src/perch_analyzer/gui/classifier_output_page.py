import reflex as rx
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.db import db
import matplotlib.pyplot as plt
from reflex_pyplot import pyplot
import polars as pl


def logits_distribution_plot(logits: pl.Series, title: str):
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.set_title(title)
    ax.hist(logits, bins=50, edgecolor="black")
    ax.set_xlabel("Logit Value")
    ax.set_ylabel("Frequency")
    ax.grid(True, alpha=0.3)

    plt.close(fig)
    return fig


class ClassifierOutputState(rx.State):
    selected_label: str = ""

    @rx.var
    def classifier_output_id(self) -> str:
        """Get the classifier output ID from the URL route parameter."""
        return self.router.page.params.get("id", "")

    def _get_classifier_output(self) -> db.ClassifierOutput | None:
        """Helper method to get the classifier object from the database."""
        if not self.classifier_output_id:
            return None

        analyzer_db = ConfigState.get_analyzer_db()
        try:
            return analyzer_db.get_classifier_output(int(self.classifier_output_id))
        except Exception as e:
            print(f"Error loading classifier output: {e}")
            return None

    def _get_classifier(self) -> db.Classifier | None:
        classifier_output = self._get_classifier_output()
        if not classifier_output:
            return None

        analyzer_db = ConfigState.get_analyzer_db()
        return analyzer_db.get_classifier(classifier_output.classifier_id)

    @rx.var
    def labels(self) -> list[str]:
        classifier = self._get_classifier()
        if not classifier:
            return []
        return classifier.labels

    @rx.event
    def set_selected_label(self, label: str):
        """Set the selected label and trigger plot update."""
        self.selected_label = label

    @rx.var
    def logits_plot(self) -> plt.Figure | None:
        """Generate a plot of logits for the selected label."""
        if not self.selected_label:
            return None

        classifier_output = self._get_classifier_output()
        if not classifier_output:
            return None

        try:
            # Use lazy scanning to efficiently read the parquet file
            lazy_df = pl.scan_parquet(classifier_output.parquet_path)

            # Filter for the selected label and collect only the logit column
            logits_df = (
                lazy_df.filter(pl.col("label") == self.selected_label)
                .select("logit")
                .collect()
            )

            if logits_df.height == 0:
                return None

            logits = logits_df["logit"]

            return logits_distribution_plot(
                logits, f"Logit Distribution for {self.selected_label}"
            )
        except Exception as e:
            print(f"Error loading logits: {e}")
            return None


def classifier_output_page():
    return rx.container(
        rx.heading(
            f"Classifier Output Id: {ClassifierOutputState.classifier_output_id}"
        ),
        rx.vstack(
            rx.hstack(
                rx.heading("Select a Label", size="5"),
                rx.select(
                    ClassifierOutputState.labels,
                    placeholder="Choose a label...",
                    value=ClassifierOutputState.selected_label,
                    on_change=ClassifierOutputState.set_selected_label,
                ),
                margin_top="1em",
            ),
            rx.cond(
                ClassifierOutputState.selected_label != "",
                rx.vstack(
                    rx.heading(
                        f"Logits for: {ClassifierOutputState.selected_label}", size="4"
                    ),
                    pyplot(ClassifierOutputState.logits_plot),
                    spacing="4",
                ),
                rx.text("Select a label to view the logit distribution"),
            ),
            spacing="4",
            width="100%",
        ),
    )


# type: ignore
