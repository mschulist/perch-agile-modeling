"""Smoke tests that actually build every page, using NiceGUI's simulated client.

These exercise the page functions server-side (no browser), which is where the
database work and rendering happen.
"""

from nicegui.testing import User

from perch_analyzer.app_context import AppContext

from . import project_shape as shape


async def test_home_page(gui: User):
    await gui.open("/")
    await gui.should_see("Welcome to Perch Analyzer!")
    await gui.should_see("Read the documentation")


async def test_summary_page(gui: User):
    await gui.open("/summary")
    await gui.should_see("Audio Summary")
    await gui.should_see(f"Windows: {shape.NUM_WINDOWS}")
    await gui.should_see(f"Annotations: {shape.NUM_MAIN + shape.NUM_OTHER}")
    await gui.should_see(f"Annotations to be labeled: {shape.NUM_UNCERTAIN}")


async def test_config_page(gui: User):
    await gui.open("/config")
    await gui.should_see("Configuration")
    await gui.should_see("Embedding Model")


async def test_classifiers_page(gui: User):
    await gui.open("/classifiers")
    await gui.should_see("Trained Classifiers")
    await gui.should_see("Classifier id: 1")
    await gui.should_see("0.9000")  # roc_auc


async def test_single_classifier_page(gui: User):
    await gui.open("/single_classifier/1")
    await gui.should_see("Classifier id: 1")
    await gui.should_see("Hyper Parameters")
    await gui.should_see("Classifier Outputs")
    await gui.should_see("Classifier Output Id: 1")


async def test_single_classifier_page_missing_id(gui: User):
    await gui.open("/single_classifier/999")
    await gui.should_see("No classifier found with id: 999")


async def test_examine_page_lists_labels(gui: User):
    await gui.open("/examine")
    await gui.should_see("Examine")
    await gui.should_see("Select a label to view windows.")
    await gui.should_see("stejay")
    await gui.should_see("mouchi")


async def test_classifier_output_page(gui: User):
    await gui.open("/classifier_output/1")
    await gui.should_see("Classifier Output ID: 1")
    await gui.should_see("Select a label to view windows.")
    await gui.should_see("stejay")


async def test_annotate_page_shows_next_window(gui: User):
    await gui.open("/annotate")
    await gui.should_see("Annotate")
    await gui.should_see("Annotation Info")
    await gui.should_see("Target Label: stejay")
    await gui.should_see("2 possible example(s) left")


async def test_annotate_page_when_nothing_left(gui: User, ctx: AppContext):
    from ml_collections import config_dict
    from perch_hoplite.db import datatypes

    hoplite_db = ctx.hoplite_db
    for annotation in hoplite_db.get_all_annotations(
        config_dict.create(eq=dict(label_type=datatypes.LabelType.UNCERTAIN))
    ):
        hoplite_db.remove_annotation(annotation.id)
    hoplite_db.commit()

    await gui.open("/annotate")
    await gui.should_see("No more windows to annotate!")
