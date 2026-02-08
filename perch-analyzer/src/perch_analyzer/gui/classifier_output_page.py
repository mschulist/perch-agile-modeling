import reflex as rx
from perch_analyzer.gui.state import ConfigState
from perch_analyzer.db import db


class ClassifierOutputState(rx.State):
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


def classifier_output_page():
    return rx.container(
        rx.heading(
            f"Classifier Output Id: {ClassifierOutputState.classifier_output_id}"
        ),
        rx.heading(f"Labels: {ClassifierOutputState.labels}"),
    )


# type: ignore
