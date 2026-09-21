"""Counts and hoplite metadata for the project.

This page reads the databases on every request.  The Reflex version ran its
queries when the page component was built, which meant the numbers were frozen
at GUI startup.
"""

import json
from typing import Any

from ml_collections import config_dict
from nicegui import ui
from perch_hoplite.db import datatypes

from perch_analyzer.gui.background import io_bound
from perch_analyzer.gui.components import loading, page_layout
from perch_analyzer.gui.services import ProjectServices, project


def _gather(services: ProjectServices) -> dict[str, Any]:
    hoplite_db = services.hoplite_db
    analyzer_db = services.analyzer_db

    def count_annotations(label_type: datatypes.LabelType) -> int:
        return len(
            hoplite_db.get_all_annotations(
                filter=config_dict.create(eq=dict(label_type=label_type))
            )
        )

    return {
        "Classes": len(hoplite_db.count_each_label()),
        "Windows": hoplite_db.count_embeddings(),
        "Annotations": count_annotations(datatypes.LabelType.POSITIVE),
        "Recordings": len(hoplite_db.get_all_recordings()),
        "Target recordings": (
            f"{analyzer_db.count_target_recordings(True)} "
            f"({analyzer_db.count_target_recordings(False)} unfinished)"
        ),
        "Annotations to be labeled": count_annotations(datatypes.LabelType.UNCERTAIN),
        "_metadata": hoplite_db.get_metadata(None).to_dict(),
    }


async def summary_page() -> None:
    services = project()
    with page_layout("Audio Summary"):
        spinner = loading("Reading the databases...")
        body = ui.row().classes("w-full gap-8 items-start")

        summary = await io_bound(_gather, services)
        spinner.delete()

        with body:
            with ui.column().classes("gap-2"):
                for name, value in summary.items():
                    if name.startswith("_"):
                        continue
                    ui.label(f"{name}: {value}").classes("text-xl")

            with ui.column().classes("grow gap-2"):
                ui.label("Hoplite DB Metadata").classes("text-2xl font-bold")
                ui.code(
                    json.dumps(summary["_metadata"], indent=2, default=str),
                    language="json",
                ).classes("w-full")
