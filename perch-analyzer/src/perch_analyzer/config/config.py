from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_FILENAME = "config.yaml"


class Config(BaseModel):
    data_path: str
    project_name: str
    user_name: str
    classifiers_dir: str
    classifier_outputs_dir: str
    precomputed_windows_dir: str
    target_recordings_dir: str
    db_path: str
    hoplite_db_path: str
    embedding_model: str
    xenocanto_api_key: str

    def to_file(self) -> None:
        with open(Path(self.data_path) / CONFIG_FILENAME, "w") as f:
            yaml.safe_dump(self.model_dump(), f, sort_keys=True, indent=4)

    @classmethod
    def load(cls, data_path: str | Path) -> "Config":
        with open(Path(data_path) / CONFIG_FILENAME) as f:
            return cls(**yaml.safe_load(f))
