import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python_server.lib.db import AccountsDB
from python_server.lib.perch_utils.classify import ClassifyFromLabels
from python_server.lib.perch_utils.projects import load_hoplite_db


def make_classifier():
    accounts_db = AccountsDB()
    classifier = ClassifyFromLabels(
        db=accounts_db,
        hoplite_db=load_hoplite_db(3),
        project_id=1,
        classify_path="data/classify",
    )
    classifier.threaded_classify(batch_size=32768)


if __name__ == "__main__":
    print("running")
    make_classifier()
