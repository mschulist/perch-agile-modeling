from pydantic import BaseModel
import yaml


class Config(BaseModel):
    config_path: str
    project_name: str
    user_name: str
    classifiers_dir: str
    classifier_outputs_dir: str
    precomputed_windows_dir: str
    ARU_data_glob: str
    db_path: str

    def to_file(self):
        with open(self.config_path, "w") as f:
            yaml.dump(self.model_dump(), f, sort_keys=True, indent=4)

    @classmethod
    def load(cls, config_path: str):
        with open(config_path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)
