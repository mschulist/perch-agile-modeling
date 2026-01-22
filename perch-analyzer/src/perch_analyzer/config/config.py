from pydantic import BaseModel
import yaml


class Config(BaseModel):
    data_path: str
    project_name: str
    user_name: str
    classifiers_dir: str
    classifier_outputs_dir: str
    precomputed_windows_dir: str
    target_recordings_dir: str
    db_path: str
    throwaway_classes: list[str]
    hoplite_db_path: str
    train_ratio: float
    max_train_examples_per_label: int
    learning_rate: float
    weak_neg_rate: float
    num_train_steps: int
    embedding_model: str

    def to_file(self):
        with open(f"{self.data_path}/config.yaml", "w") as f:
            yaml.dump(self.model_dump(), f, sort_keys=True, indent=4)

    @classmethod
    def load(cls, data_path: str):
        with open(f"{data_path}/config.yaml", "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)
