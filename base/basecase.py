import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import json
# from nextlib.utils.file import get_encoding_type

@dataclass
class BaseCase:
    name: str = ""
    path: str = ""
    file: str = "base_data.json"

    def init(self, name: str = "", file: str = ""):
        if name:
            self.name = name
        if file:
            self.file = file

    def set_defaults(self):
        self.name = ""
        self.path = ""

    def set_name(self, name: str):
        self.name = name

    def set_path(self, path: str):
        self.path = path
        p = Path(self.path)
        if not p.is_dir():
            p.mkdir(parents=True, exist_ok=True)
        if not self.name:
            self.name = p.name

    # def set_file(self, file: str):
    #     self.file = file

    def save(self):
        file_path = Path(self.path) / self.file
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=4)

    def load(self):
        file_path = Path(self.path) / self.file
        if not file_path.exists():
            self.save()
            return True

        # encoding_type = get_encoding_type(file_path)  # 다시 확인
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        exclude_keys = {"path", "file"}
        for key, value in data.items():
            if hasattr(self, key) and key not in exclude_keys:
                setattr(self, key, value)
        return True
