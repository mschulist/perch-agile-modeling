from pathlib import Path

from perch_analyzer.app_context import AppContext, ProjectNotInitializedError
from perch_analyzer.config.config import Config


def test_config_round_trip(project_dir: Path):
    config = Config.load(project_dir)
    config.user_name = "someone else"
    config.to_file()
    assert Config.load(project_dir).user_name == "someone else"


def test_context_overrides_stale_data_path(project_dir: Path):
    """A moved project should use where it was found, not where it was made."""
    config_file = project_dir / "config.yaml"
    config_file.write_text(
        config_file.read_text().replace(
            f"data_path: {project_dir}", "data_path: /gone/missing"
        )
    )
    assert Config.load(project_dir).data_path == "/gone/missing"
    assert AppContext(project_dir).config.data_path == str(project_dir.resolve())


def test_require_initialized(tmp_path: Path):
    import pytest

    with pytest.raises(ProjectNotInitializedError):
        AppContext(tmp_path / "empty").require_initialized()
