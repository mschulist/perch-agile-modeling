def start_gui(data_dir: str):
    import subprocess
    import os
    from pathlib import Path

    # Get the directory where the GUI code is located
    gui_dir = Path(__file__).parent.parent.parent.parent
    
    # Set the data directory as an environment variable so the GUI can access it
    env = os.environ.copy()
    env["PERCH_ANALYZER_DATA_DIR"] = str(Path(data_dir).absolute())
    
    # Run reflex from the package root where rxconfig.py is located
    subprocess.run(["reflex", "run"], cwd=str(gui_dir), env=env)
