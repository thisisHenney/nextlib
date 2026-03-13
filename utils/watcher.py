import time
from pathlib import Path

from PySide6.QtCore import Signal, QFileSystemWatcher

from nextlib.utils.file import find_items


class DirectoryWatcher(QFileSystemWatcher):
    changed = Signal(str, list, list)

    def __init__(self, path=''):
        super().__init__()

        self.path = str(Path(path).resolve()) if path else ''
        self._file_list_in_dir = []
        self._watching = False

    def _init_connect(self):
        self.directoryChanged.connect(self.on_directory_changed)

    def start(self, path=''):
        if path:
            self.path = str(Path(path).resolve())
        self._file_list_in_dir = find_items(self.path, recursive=False)

        self.addPath(str(self.path))
        self._init_connect()

        self._watching = True

    def end(self):
        self.removePaths(self.directories())
        self.directoryChanged.disconnect()
        self._watching = False

    def is_watching(self):
        return self._watching

    def get_monitoring_paths(self):
        return self.directories()

    def on_directory_changed(self, path):
        _added, _removed = self.find_changed_files(path)
        if _added or _removed:
            self.changed.emit(path, _added, _removed)

    def find_changed_files(self, path):
        found_files = find_items(path, recursive=False)
        _added = set(found_files) - set(self._file_list_in_dir)
        _removed = set(self._file_list_in_dir) - set(found_files)

        self._file_list_in_dir = found_files
        return list(_added), list(_removed)
