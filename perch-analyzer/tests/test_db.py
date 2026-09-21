from perch_analyzer.app_context import AppContext
from perch_analyzer.db import db


def test_get_all_classifiers_skips_weights(ctx: AppContext):
    classifiers = ctx.analyzer_db.get_all_classifiers()
    assert len(classifiers) == 1
    info = classifiers[0]
    assert not isinstance(info, db.Classifier)
    assert float(info.metrics["roc_auc"]) == 0.9
    assert info.labels == ["stejay", "mouchi"]


def test_get_classifier_loads_weights(ctx: AppContext):
    classifier = ctx.analyzer_db.get_classifier(1)
    assert classifier.linear_classifier.beta.shape == (128, 2)
    assert list(classifier.linear_classifier.classes) == ["stejay", "mouchi"]


def test_classifier_output_labels_and_dedupe_keys(ctx: AppContext):
    analyzer_db = ctx.analyzer_db
    assert analyzer_db.get_classifier_output_labels(1) == ["stejay"]
    assert analyzer_db.get_existing_output_window_keys(1) == {
        (1, "stejay"),
        (2, "stejay"),
    }


def test_insert_classifier_output_windows_is_batched(ctx: AppContext):
    analyzer_db = ctx.analyzer_db
    inserted = analyzer_db.insert_classifier_output_windows(
        1, [(3, 0.5, "mouchi"), (4, 0.25, "mouchi")]
    )
    assert inserted == 2
    assert analyzer_db.get_classifier_output_labels(1) == ["mouchi", "stejay"]


def test_count_target_recordings_on_empty_project(ctx: AppContext):
    assert ctx.analyzer_db.count_target_recordings(True) == 0
    assert ctx.analyzer_db.get_target_recording_xc_ids() == set()


def test_logits_survive_a_round_trip(ctx: AppContext):
    """The logit column used to be declared as an integer."""
    analyzer_db = ctx.analyzer_db
    windows = analyzer_db.get_all_classifier_output_windows(1, label="stejay")
    assert sorted(w.logit for w in windows) == [1.25, 2.5]
