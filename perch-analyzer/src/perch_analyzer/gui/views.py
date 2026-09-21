"""The shape of a window as the GUI displays it, and how to build one."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from perch_analyzer.examine import examine_annotations
from perch_analyzer.gui.services import ProjectServices


@dataclass
class WindowView:
    """Everything a window card needs to render."""

    window_id: int
    filename: str
    offsets: Sequence[float]
    labels: list[str]
    audio_url: str
    spec_url: str
    # Set only when the window came from a classifier output.
    classifier_label: str | None = None
    logit: float | None = None

    @property
    def offsets_label(self) -> str:
        if len(self.offsets) >= 2:
            return f"{self.offsets[0]:.2f}s - {self.offsets[1]:.2f}s"
        return f"{self.offsets[0]:.2f}s"


@dataclass
class WindowPage:
    """One page of window views, plus how many there are in total."""

    views: list[WindowView] = field(default_factory=list)
    total: int = 0


def build_views(
    services: ProjectServices,
    window_ids: Sequence[int],
    classifier_labels: dict[int, tuple[str, float]] | None = None,
) -> list[WindowView]:
    """Build views for `window_ids`, rendering any missing assets first.

    Rendering happens in parallel up front so the per-window URL lookups below
    are pure path joins.
    """
    if not window_ids:
        return []

    services.precompute_windows(window_ids)

    hoplite_db = services.hoplite_db
    windows = examine_annotations.get_windows_with_annotations(hoplite_db, window_ids)

    views: list[WindowView] = []
    for entry in windows:
        audio_url, spec_url = services.window_urls(entry.window.id)
        classifier_label, logit = (classifier_labels or {}).get(
            entry.window.id, (None, None)
        )
        views.append(
            WindowView(
                window_id=entry.window.id,
                filename=entry.recording.filename,
                offsets=entry.window.offsets,
                labels=sorted({ann.label for ann in entry.annotations}),
                audio_url=audio_url,
                spec_url=spec_url,
                classifier_label=classifier_label,
                logit=logit,
            )
        )
    return views
