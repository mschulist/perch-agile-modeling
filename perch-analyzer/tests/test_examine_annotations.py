from perch_hoplite.db import datatypes

from perch_analyzer.app_context import AppContext
from perch_analyzer.examine import examine_annotations


def test_get_windows_by_label(ctx: AppContext):
    hoplite_db = ctx.hoplite_db
    windows = examine_annotations.get_windows_by_label(hoplite_db, "stejay")

    assert [w.window.id for w in windows] == [1, 3]
    assert all(w.recording.filename.endswith(".wav") for w in windows)
    assert all(any(a.label == "stejay" for a in w.annotations) for w in windows)


def test_get_windows_with_annotations_preserves_order(ctx: AppContext):
    windows = examine_annotations.get_windows_with_annotations(
        ctx.hoplite_db, [3, 1, 2]
    )
    assert [w.window.id for w in windows] == [3, 1, 2]


def test_update_labels_adds_and_removes(ctx: AppContext):
    hoplite_db = ctx.hoplite_db
    examine_annotations.update_labels(
        config=ctx.config, hoplite_db=hoplite_db, window_id=1, new_labels=["rebnut"]
    )

    windows = examine_annotations.get_windows_with_annotations(hoplite_db, [1])
    assert [a.label for a in windows[0].annotations] == ["rebnut"]
    assert "stejay" not in hoplite_db.get_all_labels(
        label_type=datatypes.LabelType.POSITIVE
    ) or examine_annotations.get_window_ids_by_label(hoplite_db, "stejay") == [3]
