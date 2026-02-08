from perch_analyzer.gui.state import ConfigState
from perch_analyzer.db import db
import reflex as rx

NA_STR = "N/A"


def classifier_card() -> rx.Component:
    """Create a card component for a single classifier."""
    return rx.box(
        rx.hstack(
            rx.vstack(
                rx.heading("Hyper Parameters", size="5"),
                rx.text(f"Training Ratio: {SingleClassifierState.train_ratio}"),
                rx.text(
                    f"Number of Training Steps: {SingleClassifierState.num_train_steps}"
                ),
                rx.text(f"Weak Negative Rate: {SingleClassifierState.weak_neg_rate}"),
                rx.text(f"Learning Rate: {SingleClassifierState.learning_rate}"),
                rx.box(
                    rx.text(f"Labels: {SingleClassifierState.labels}"),
                    max_height="20em",
                    overflow_y="auto",
                    max_width="20em",
                ),
                align="start",
                spacing="2",
            ),
            rx.vstack(
                rx.heading("Performance Metrics", size="5"),
                rx.hstack(
                    rx.vstack(
                        rx.text("AUC-ROC", weight="bold"),
                        rx.heading(SingleClassifierState.formatted_auc_roc, size="7"),
                        align="center",
                    ),
                    rx.vstack(
                        rx.text("CMAP", weight="bold"),
                        rx.heading(SingleClassifierState.formatted_cmap, size="7"),
                        align="center",
                    ),
                    rx.vstack(
                        rx.text("Top-1 Accuracy", weight="bold"),
                        rx.heading(SingleClassifierState.formatted_top1_acc, size="7"),
                        align="center",
                    ),
                    spacing="6",
                ),
                align="start",
                spacing="2",
            ),
            spacing="8",
            align="start",
        ),
        padding="1.5em",
        border="1px solid #e0e0e0",
        border_radius="8px",
        margin_bottom="1em",
        width="100%",
    )


def classifier_output_card(classifier_output_id: int) -> rx.Component:
    return rx.box(
        rx.heading(f"Classifier Output Id: {classifier_output_id}"),
        border="1px solid #e0e0e0",
        border_radius="8px",
        padding="0.5em",
        margin_top="1em",
        on_click=rx.redirect(f"/classifier_output/{classifier_output_id}"),
        cursor="pointer",
        transition="background-color 0.3s ease",
        _hover={
            "background_color": "#444444",
        },
    )


class SingleClassifierState(ConfigState):
    @rx.var
    def classifier_id(self) -> str:
        """Get the classifier ID from the URL route parameter."""
        return self.router.page.params.get("id", "")

    def _get_classifier(self) -> db.Classifier | None:
        """Helper method to get the classifier object from the database."""
        if not self.classifier_id:
            return None

        analyzer_db = ConfigState.get_analyzer_db()
        try:
            return analyzer_db.get_classifier(int(self.classifier_id))
        except Exception as _:
            return None

    @rx.var
    def classifier(self) -> db.Classifier | None:
        """Get the classifier object from the database."""
        return self._get_classifier()

    @rx.var
    def formatted_datetime(self) -> str:
        """Format the classifier datetime."""
        clf = self._get_classifier()
        if clf:
            return clf.datetime.strftime("%B %d, %Y at %I:%M %p")
        return ""

    @rx.var
    def formatted_auc_roc(self) -> str:
        """Format AUC-ROC metric."""
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        auc_roc = clf.metrics.get("roc_auc")
        if auc_roc is not None:
            return f"{auc_roc:.4f}"
        return NA_STR

    @rx.var
    def formatted_cmap(self) -> str:
        """Format CMAP metric."""
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        cmap = clf.metrics.get("cmap")
        if cmap is not None:
            return f"{cmap:.4f}"
        return NA_STR

    @rx.var
    def formatted_top1_acc(self) -> str:
        """Format Top-1 Accuracy metric."""
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        top1_acc = clf.metrics.get("top1_acc")
        if top1_acc is not None:
            return f"{top1_acc:.4f}"
        return NA_STR

    @rx.var
    def train_ratio(self) -> str:
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        return str(clf.train_ratio)

    @rx.var
    def learning_rate(self) -> str:
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        return str(clf.learning_rate)

    @rx.var
    def weak_neg_rate(self) -> str:
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        return str(clf.weak_neg_rate)

    @rx.var
    def num_train_steps(self) -> str:
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        return str(clf.num_train_steps)

    @rx.var
    def labels(self) -> str:
        clf = self._get_classifier()
        if not clf:
            return NA_STR
        return str(clf.labels)

    @rx.var
    def classifier_outputs(self) -> list[db.ClassifierOutput]:
        clf = self._get_classifier()
        if not clf:
            return []
        analyzer_db = ConfigState.get_analyzer_db()
        return analyzer_db.get_all_classifier_outputs(clf.id)


def single_classifier_page():
    return rx.container(
        rx.cond(
            SingleClassifierState.classifier.is_none(),  # type: ignore
            rx.heading(
                f"No classifier found with id: {SingleClassifierState.classifier_id}"
            ),
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        f"Classifier id: {SingleClassifierState.classifier_id}",
                        size="8",
                    ),
                    rx.heading(
                        f"({SingleClassifierState.formatted_datetime})", size="4"
                    ),
                    align="center",
                ),
                classifier_card(),
            ),
        ),
        rx.divider(orientation="horizontal", margin_top="1em", margin_bottom="1em"),
        rx.heading("Classifier Outputs", size="8"),
        SingleClassifierState.classifier_outputs.foreach(
            lambda classifier_output: classifier_output_card(classifier_output.id)
        ),
    )


# type: ignore
