from pathlib import Path
from PySide6.QtWidgets import QFileDialog

# Filter Option
# (ex) ext: "CAD Files (*.stp *.step);;STL Files (*.stl);;All Files (*)"

class DirDialogBox:
    @staticmethod
    def open_folder(parent=None, title="Select folder",
                    path: str | Path | None = None) -> str | None:
        if path is None:
            path = Path.home()

        dlg = QFileDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        dlg.setDirectory(str(path))

        if dlg.exec():
            return dlg.selectedFiles()[0]
        return None

    @staticmethod
    def create_folder(parent=None, title="Create folder",
                      path: str | Path | None = None) -> str | None:
        if path is None:
            path = Path.home()

        dlg = QFileDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setFileMode(QFileDialog.Directory)
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setOption(QFileDialog.ShowDirsOnly, True)
        dlg.setDirectory(str(path))

        if dlg.exec():
            return dlg.selectedFiles()[0]
        return None


class FileDialogBox:
    @staticmethod
    def open_file(parent=None, title="Open file",
                  filters="All Files (*)",
                  path: str | Path | None = None) -> str | None:
        if path is None:
            path = Path.home()

        dlg = QFileDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setNameFilter(filters)
        dlg.setFileMode(QFileDialog.ExistingFile)
        dlg.setDirectory(str(path))

        if dlg.exec():
            return dlg.selectedFiles()[0]
        return None

    @staticmethod
    def open_files(parent=None, title="Open files",
                   filters="All Files (*)", path: str | Path | None = None) -> list[Path]:
        if path is None:
            path = Path.home()

        dlg = QFileDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setNameFilter(filters)
        dlg.setFileMode(QFileDialog.ExistingFiles)
        dlg.setDirectory(str(path))

        if dlg.exec():
            return [p for p in dlg.selectedFiles()]
        return []

    @staticmethod
    def save_file(parent=None, title="Save file",
                  filters="All Files (*)",
                  path: str | Path | None = None) -> str | None:
        if path is None:
            path = Path.home()

        dlg = QFileDialog(parent)
        dlg.setWindowTitle(title)
        dlg.setAcceptMode(QFileDialog.AcceptSave)
        dlg.setNameFilter(filters)
        dlg.setDirectory(str(path))

        if dlg.exec():
            return dlg.selectedFiles()[0]
        return None
