from pathlib import Path
import zipfile
from typing import Iterable, Optional


class ZipTool:
    @staticmethod
    def _ensure_zip_suffix(zip_path: Path) -> Path:
        return zip_path.with_suffix('.zip') if zip_path.suffix.lower() != '.zip' else zip_path

    @staticmethod
    def zip_file(
        src: Path | str,
        zip_path: Path | str,
        compress_level: int = 6
    ) -> Path:
        src = Path(src)
        zip_path = ZipTools._ensure_zip_suffix(Path(zip_path))

        with zipfile.ZipFile(
            zip_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compress_level
        ) as zf:
            zf.write(src, arcname=src.name)

        return zip_path

    @staticmethod
    def zip_folder(
        folder: Path | str,
        zip_path: Path | str,
        compress_level: int = 6
    ) -> Path:
        folder = Path(folder)
        zip_path = ZipTools._ensure_zip_suffix(Path(zip_path))

        with zipfile.ZipFile(
            zip_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compress_level
        ) as zf:
            for file in folder.rglob("*"):
                if file.is_file():
                    zf.write(file, arcname=file.relative_to(folder))

        return zip_path

    @staticmethod
    def zip_selected(
        folder: Path | str,
        zip_path: Path | str,
        extensions: Iterable[str],  # ex) extensions=[".json", ".csv"]
        compress_level: int = 6
    ) -> Path:
        folder = Path(folder)
        zip_path = ZipTools._ensure_zip_suffix(Path(zip_path))
        extensions = {ext.lower() for ext in extensions}

        with zipfile.ZipFile(
            zip_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=compress_level
        ) as zf:
            for file in folder.rglob("*"):
                if file.is_file() and file.suffix.lower() in extensions:
                    zf.write(file, arcname=file.relative_to(folder))

        return zip_path

    @staticmethod
    def unzip(
        zip_path: Path | str,
        dest_folder: Path | str = None
    ) -> Path:
        zip_path = Path(zip_path)
        if dest_folder is None:
            dest_folder = zip_path.with_suffix("")

        dest_folder = Path(dest_folder)
        dest_folder.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(dest_folder)

        return dest_folder
