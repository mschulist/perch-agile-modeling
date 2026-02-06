def start_gui(data_dir: str):
    import subprocess
    import os
    import tempfile
    from pathlib import Path

    # Set the data directory as an environment variable so the GUI can access it
    env = os.environ.copy()
    env["PERCH_ANALYZER_DATA_DIR"] = str(Path(data_dir).absolute())

    # Create a temporary directory for running reflex
    # This is needed because reflex requires an rxconfig.py in the working directory
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create rxconfig.py dynamically in the temp directory
        rxconfig_content = """import reflex as rx

config = rx.Config(
    app_name="Perch_Analyzer",
    app_module_import="perch_analyzer.gui.index",
    backend_port=8000,
    frontend_port=3000,
    plugins=[rx.plugins.sitemap.SitemapPlugin()],
)
"""
        (tmpdir_path / "rxconfig.py").write_text(rxconfig_content)

        # Run reflex from the temporary directory
        subprocess.run(["reflex", "run"], cwd=str(tmpdir_path), env=env)
