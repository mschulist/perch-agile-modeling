"""Clicking around the pages.

These cover the interactions that broke in production: selecting a label used
to rebuild the list containing the button whose handler was running, and
paging used to recreate the pagination widget from its own change handler.
Both left NiceGUI dereferencing a garbage-collected parent element.
"""

from nicegui import ui
from nicegui.testing import User

from perch_analyzer.app_context import AppContext
from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.examine_page import PAGE_SIZE

from . import project_shape as shape


async def test_selecting_a_label_loads_its_windows(gui: User):
    await gui.open("/examine")
    await gui.should_see("stejay")

    gui.find("stejay").click()

    await gui.should_see(f"of {shape.NUM_MAIN}")
    await gui.should_see("Edit labels")


async def test_selecting_a_second_label_reloads(gui: User):
    """Selecting twice exercises the path that deleted the clicked button."""
    await gui.open("/examine")
    await gui.should_see("stejay")

    gui.find("stejay").click()
    await gui.should_see(f"of {shape.NUM_MAIN}")

    gui.find("mouchi").click()
    await gui.should_see(f"of {shape.NUM_OTHER}")


async def test_pagination_moves_between_pages(gui: User):
    await gui.open("/examine")
    await gui.should_see("stejay")

    gui.find("stejay").click()
    await gui.should_see(f"Showing 1-{PAGE_SIZE} of {shape.NUM_MAIN}")

    # NiceGUI camel-cases event names when registering listeners.
    gui.find(kind=ui.pagination).trigger("update:modelValue", 2)

    await gui.should_see(
        f"Showing {PAGE_SIZE + 1}-{shape.NUM_MAIN} of {shape.NUM_MAIN}"
    )


async def test_editing_labels_saves_and_drops_the_card(gui: User, ctx: AppContext):
    await gui.open("/examine")
    await gui.should_see("stejay")
    gui.find("stejay").click()
    await gui.should_see("Edit labels")

    gui.find("Edit labels").click()  # clicks the lowest-id match
    await gui.should_see("Save")

    select = min(gui.find(kind=ui.select).elements, key=lambda e: e.id)
    select.value = ["mouchi"]
    gui.find("Save").click()

    # The window no longer carries the label being browsed, so its card goes
    # away and the count drops.
    await gui.should_see(f"{shape.NUM_MAIN - 1} window(s) left under stejay")

    hoplite_db = ctx.hoplite_db.thread_split()
    assert 1 not in examine_annotations.get_window_ids_by_label(hoplite_db, "stejay")
    assert 1 in examine_annotations.get_window_ids_by_label(hoplite_db, "mouchi")


async def test_classifier_output_label_selection(gui: User):
    await gui.open("/classifier_output/1")
    await gui.should_see("stejay")

    gui.find("stejay").click()

    await gui.should_see("highest logit first")
    await gui.should_see("Classifier label: stejay")


async def test_annotate_submit_advances_to_the_next_window(gui: User):
    await gui.open("/annotate")
    await gui.should_see(f"{shape.NUM_UNCERTAIN} possible example(s) left")

    gui.find("Submit annotations").click()

    await gui.should_see(f"{shape.NUM_UNCERTAIN - 1} possible example(s) left")
