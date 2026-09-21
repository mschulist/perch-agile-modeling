from perch_analyzer.app_context import AppContext
from perch_analyzer.examine import examine_annotations

from . import project_shape as shape


def test_get_windows_by_label(ctx: AppContext):
    hoplite_db = ctx.hoplite_db
    windows = examine_annotations.get_windows_by_label(hoplite_db, "stejay")

    # Only the positively annotated ones; the pending UNCERTAIN windows carry
    # the same label but must not show up here.
    assert len(windows) == shape.NUM_MAIN
    assert all(w.recording.filename.endswith(".wav") for w in windows)
    assert all(any(a.label == "stejay" for a in w.annotations) for w in windows)


def test_get_windows_with_annotations_preserves_order(ctx: AppContext):
    windows = examine_annotations.get_windows_with_annotations(
        ctx.hoplite_db, [3, 1, 2]
    )
    assert [w.window.id for w in windows] == [3, 1, 2]


def test_update_labels_adds_and_removes(ctx: AppContext):
    hoplite_db = ctx.hoplite_db
    before = examine_annotations.get_window_ids_by_label(hoplite_db, "stejay")
    assert 1 in before

    examine_annotations.update_labels(
        config=ctx.config, hoplite_db=hoplite_db, window_id=1, new_labels=["rebnut"]
    )

    windows = examine_annotations.get_windows_with_annotations(hoplite_db, [1])
    assert [a.label for a in windows[0].annotations] == ["rebnut"]

    after = examine_annotations.get_window_ids_by_label(hoplite_db, "stejay")
    assert after == [wid for wid in before if wid != 1]
    assert 1 in examine_annotations.get_window_ids_by_label(hoplite_db, "rebnut")
