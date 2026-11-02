"""Clicking around the pages.

These cover the interactions that broke in production: selecting a label used
to rebuild the list containing the button whose handler was running, and
paging used to recreate the pagination widget from its own change handler.
Both left NiceGUI dereferencing a garbage-collected parent element.
"""

from nicegui import ui
from nicegui.elements.mixins.value_element import ValueElement
from nicegui.testing import User

from perch_analyzer.app_context import AppContext
from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.examine_page import PAGE_SIZE

from . import project_shape as shape
from .conftest import TEST_PASSWORD, TEST_USERNAME, sign_in

# Long enough for a job subprocess to start Python, run and exit.
JOB_RETRIES = 150


def set_field(user: User, marker: str, value: object) -> None:
    (element,) = user.find(marker=marker).elements
    assert isinstance(element, ValueElement)
    element.value = value


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
    # Credited to whoever is signed in, not the config's user_name.
    (window,) = examine_annotations.get_windows_with_annotations(hoplite_db, [1])
    assert [a.provenance for a in window.annotations] == [TEST_USERNAME]


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


# --- Logins ----------------------------------------------------------------


async def test_signed_out_visitors_are_sent_to_login(gui_unauthenticated: User):
    await gui_unauthenticated.open("/annotate")
    await gui_unauthenticated.should_see("Sign in")
    await gui_unauthenticated.should_not_see("Annotation Info")


async def test_login_returns_to_the_requested_page(gui_unauthenticated: User):
    await gui_unauthenticated.open("/single_classifier/1")
    await gui_unauthenticated.should_see("Sign in")

    gui_unauthenticated.find(marker="username").type(TEST_USERNAME)
    gui_unauthenticated.find(marker="password").type(TEST_PASSWORD)
    gui_unauthenticated.find(marker="submit").click()

    # The path parameter still reaches the page through the auth wrapper.
    await gui_unauthenticated.should_see("Hyper Parameters")
    await gui_unauthenticated.should_see(TEST_USERNAME)


async def test_wrong_password_is_refused(gui_unauthenticated: User):
    await sign_in(gui_unauthenticated, TEST_USERNAME, "wrong")
    await gui_unauthenticated.should_see("Invalid username or password.")


async def test_first_account_can_be_created_from_the_login_page(
    gui_unauthenticated: User, ctx: AppContext
):
    ctx.analyzer_db.delete_user(TEST_USERNAME)

    await gui_unauthenticated.open("/login")
    await gui_unauthenticated.should_see("Create the first account")
    gui_unauthenticated.find(marker="username").type("ana")
    gui_unauthenticated.find(marker="password").type("pw")
    gui_unauthenticated.find(marker="confirm_password").type("pw")
    gui_unauthenticated.find(marker="submit").click()

    await gui_unauthenticated.should_see("Signed in as: ana")
    assert ctx.analyzer_db.verify_user("ana", "pw")


async def test_log_out(gui: User):
    gui.find("Log out").click()
    await gui.should_see("Sign in")
    await gui.open("/examine")
    await gui.should_see("Sign in")


async def test_removed_users_lose_access(gui: User, ctx: AppContext):
    ctx.analyzer_db.delete_user(TEST_USERNAME)
    await gui.open("/examine")
    await gui.should_see("Create the first account")


async def test_change_password(gui: User, ctx: AppContext):
    await gui.open("/account")
    gui.find(marker="current_password").type(TEST_PASSWORD)
    gui.find(marker="new_password").type("fresh")
    gui.find(marker="confirm_new_password").type("fresh")
    gui.find(marker="change_password").click()
    await gui.should_see("Password changed")
    assert ctx.analyzer_db.verify_user(TEST_USERNAME, "fresh")


async def test_data_route_requires_login_and_stays_in_bounds(
    gui_unauthenticated: User,
):
    client = gui_unauthenticated.http_client
    spectrogram = "/data/precomputed_windows/1.png"

    assert (await client.get(spectrogram)).status_code == 401

    await sign_in(gui_unauthenticated, TEST_USERNAME, TEST_PASSWORD)
    await gui_unauthenticated.should_see("Welcome to Perch Analyzer!")

    assert (await client.get(spectrogram)).status_code == 200
    for private in ("config.yaml", "analyzer.db", ".gui_secret", "../../etc/hosts"):
        assert (await client.get(f"/data/{private}")).status_code == 404, private


# --- Jobs ------------------------------------------------------------------


async def test_jobs_page_offers_only_gui_commands(gui: User):
    await gui.open("/jobs")
    for command in (
        "target_recordings",
        "search",
        "run_classifier",
        "gather_classifier_outputs",
    ):
        await gui.should_see(marker=f"form_{command}")
    await gui.should_not_see(marker="form_embed")
    await gui.should_not_see(marker="form_create_classifier")


async def test_jobs_page_runs_a_job_and_shows_its_log(gui: User, ctx: AppContext):
    await gui.open("/jobs")
    await gui.should_see(marker="form_gather_classifier_outputs")
    for dest, value in [
        ("classifier_output_id", 1),
        ("min_logit", -100),
        ("max_logit", 100),
        ("label", "mouchi"),
    ]:
        set_field(gui, f"gather_classifier_outputs.{dest}", value)
    gui.find(marker="start_gather_classifier_outputs").click()

    await gui.should_see("Job #1 finished.", retries=JOB_RETRIES)
    assert ctx.analyzer_db.get_classifier_output_labels(1) == ["mouchi", "stejay"]

    await gui.open("/jobs?job=1")
    await gui.should_see("Job #1: gather_classifier_outputs (succeeded)")
    await gui.should_see(f"started by {TEST_USERNAME}")


async def test_form_errors_are_shown_without_starting_a_job(gui: User):
    await gui.open("/jobs")
    await gui.should_see(marker="form_run_classifier")
    gui.find(marker="start_run_classifier").click()
    await gui.should_see("Check the form")


async def test_gather_from_the_classifier_output_page(gui: User):
    await gui.open("/classifier_output/1")
    await gui.should_see("Gather more windows")
    await gui.should_not_see("mouchi")

    set_field(gui, "min_logit", -100)
    set_field(gui, "max_logit", 100)
    set_field(gui, "label", "mouchi")
    gui.find(marker="start_gather_classifier_outputs").click()

    await gui.should_see("Job #1 finished.", retries=JOB_RETRIES)
    # The label list refreshes in place with the newly gathered label.
    await gui.should_see("mouchi")
    # The gather form's label picker offers "mouchi" too; click the list entry.
    gui.find(kind=ui.button, content="mouchi").click()
    await gui.should_see("highest logit first")


async def test_run_classifier_from_its_page(gui: User, ctx: AppContext):
    await gui.open("/single_classifier/1")
    await gui.should_see("Run this classifier over every window")
    gui.find(marker="start_run_classifier").click()

    await gui.should_see("Job #1 finished.", retries=JOB_RETRIES)
    await gui.should_see("Classifier Output Id: 2")
    assert [o.id for o in ctx.analyzer_db.get_all_classifier_outputs(1)] == [1, 2]
