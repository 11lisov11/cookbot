from pathlib import Path

import yaml

from .models import WorkspaceModel


class WorkspaceStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> WorkspaceModel:
        if not self.path.exists():
            return WorkspaceModel()
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        return WorkspaceModel.model_validate(data)
