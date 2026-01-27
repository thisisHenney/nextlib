"""
개선된 DialogBox 모듈

주요 개선 사항:
- 일관된 반환 타입 (Path)
- 에러 처리 추가
- 경로 기억 기능
- 기본 파일명 지정
- 파일 검증 기능
- 확장 메타데이터
"""

from pathlib import Path
from typing import Callable, Optional
import logging
from PySide6.QtWidgets import QFileDialog, QMessageBox

logger = logging.getLogger(__name__)


class DialogBoxConfig:
    """다이얼로그 설정 관리"""

    # 경로 기억 기능
    last_dir_path: Path = Path.home()
    last_file_path: Path = Path.home()
    remember_paths: bool = True

    # 기본 설정
    show_hidden_files: bool = False
    confirm_overwrite: bool = True


class DirDialogBox:
    """개선된 폴더 선택 다이얼로그"""

    @staticmethod
    def open_folder(
        parent=None,
        title: str = "Select folder",
        path: Optional[str | Path] = None,
        remember_path: bool = True
    ) -> Optional[Path]:
        """
        폴더 선택 다이얼로그

        Args:
            parent: 부모 위젯
            title: 다이얼로그 제목
            path: 시작 경로
            remember_path: 선택한 경로 기억 여부

        Returns:
            선택된 폴더 경로 (Path) 또는 None
        """
        try:
            # 시작 경로 결정
            if path is None and DialogBoxConfig.remember_paths:
                path = DialogBoxConfig.last_dir_path
            elif path is None:
                path = Path.home()
            else:
                path = Path(path)

            # 경로 검증
            if not path.exists():
                logger.warning(f"Path does not exist: {path}, using home directory")
                path = Path.home()

            # getExistingDirectory 사용 (폴더 전용)
            options = QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks

            result = QFileDialog.getExistingDirectory(
                parent,
                title,
                str(path),
                options
            )

            if result:
                result_path = Path(result)

                # 경로 기억
                if remember_path and DialogBoxConfig.remember_paths:
                    DialogBoxConfig.last_dir_path = result_path

                logger.info(f"Selected folder: {result_path}")
                return result_path

            logger.debug("Folder selection cancelled")
            return None

        except Exception as e:
            logger.error(f"Error in open_folder: {e}")
            return None

    @staticmethod
    def create_folder(
        parent=None,
        title: str = "Create folder",
        path: Optional[str | Path] = None,
        remember_path: bool = True
    ) -> Optional[Path]:
        """
        폴더 생성 다이얼로그

        Args:
            parent: 부모 위젯
            title: 다이얼로그 제목
            path: 시작 경로
            remember_path: 선택한 경로 기억 여부

        Returns:
            생성된 폴더 경로 (Path) 또는 None
        """
        try:
            if path is None and DialogBoxConfig.remember_paths:
                path = DialogBoxConfig.last_dir_path
            elif path is None:
                path = Path.home()
            else:
                path = Path(path)

            if not path.exists():
                path = Path.home()

            # getExistingDirectory 사용 (폴더 전용)
            result = QFileDialog.getExistingDirectory(
                parent,
                title,
                str(path),
                QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
            )

            if result:
                result_path = Path(result)

                # 폴더가 없으면 생성
                if not result_path.exists():
                    result_path.mkdir(parents=True, exist_ok=True)
                    logger.info(f"Created folder: {result_path}")

                if remember_path and DialogBoxConfig.remember_paths:
                    DialogBoxConfig.last_dir_path = result_path

                return result_path

            return None

        except Exception as e:
            logger.error(f"Error in create_folder: {e}")
            return None


class FileDialogBox:
    """개선된 파일 선택 다이얼로그"""

    @staticmethod
    def open_file(
        parent=None,
        title: str = "Open file",
        filters: str = "All Files (*)",
        path: Optional[str | Path] = None,
        remember_path: bool = True,
        validate: Optional[Callable[[Path], bool]] = None
    ) -> Optional[Path]:
        """
        단일 파일 선택 다이얼로그

        Args:
            parent: 부모 위젯
            title: 다이얼로그 제목
            filters: 파일 필터 (예: "Text Files (*.txt);;All Files (*)")
            path: 시작 경로
            remember_path: 선택한 경로 기억 여부
            validate: 파일 검증 함수 (Path -> bool)

        Returns:
            선택된 파일 경로 (Path) 또는 None
        """
        try:
            if path is None and DialogBoxConfig.remember_paths:
                path = DialogBoxConfig.last_file_path
            elif path is None:
                path = Path.home()
            else:
                path = Path(path)

            # 파일 경로인 경우 부모 디렉토리 사용
            if path.is_file():
                path = path.parent

            if not path.exists():
                path = Path.home()

            dlg = QFileDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setNameFilter(filters)
            dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
            dlg.setDirectory(str(path))

            if dlg.exec():
                selected_files = dlg.selectedFiles()
                if selected_files:
                    result = Path(selected_files[0])

                    # 파일 존재 확인
                    if not result.exists():
                        logger.warning(f"Selected file does not exist: {result}")
                        return None

                    # 커스텀 검증
                    if validate and not validate(result):
                        logger.warning(f"File validation failed: {result}")
                        if parent:
                            QMessageBox.warning(
                                parent,
                                "Validation Error",
                                "The selected file is not valid."
                            )
                        return None

                    # 경로 기억
                    if remember_path and DialogBoxConfig.remember_paths:
                        DialogBoxConfig.last_file_path = result.parent

                    logger.info(f"Selected file: {result}")
                    return result

            return None

        except Exception as e:
            logger.error(f"Error in open_file: {e}")
            return None

    @staticmethod
    def open_files(
        parent=None,
        title: str = "Open files",
        filters: str = "All Files (*)",
        path: Optional[str | Path] = None,
        remember_path: bool = True,
        validate: Optional[Callable[[Path], bool]] = None
    ) -> list[Path]:
        """
        복수 파일 선택 다이얼로그

        Args:
            parent: 부모 위젯
            title: 다이얼로그 제목
            filters: 파일 필터
            path: 시작 경로
            remember_path: 선택한 경로 기억 여부
            validate: 파일 검증 함수

        Returns:
            선택된 파일 경로 리스트 (list[Path])
        """
        try:
            if path is None and DialogBoxConfig.remember_paths:
                path = DialogBoxConfig.last_file_path
            elif path is None:
                path = Path.home()
            else:
                path = Path(path)

            if path.is_file():
                path = path.parent

            if not path.exists():
                path = Path.home()

            dlg = QFileDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setNameFilter(filters)
            dlg.setFileMode(QFileDialog.FileMode.ExistingFiles)
            dlg.setDirectory(str(path))

            if dlg.exec():
                selected_files = dlg.selectedFiles()
                if selected_files:
                    results = [Path(f) for f in selected_files if Path(f).exists()]

                    # 검증
                    if validate:
                        valid_results = []
                        invalid_count = 0

                        for result in results:
                            if validate(result):
                                valid_results.append(result)
                            else:
                                invalid_count += 1
                                logger.warning(f"File validation failed: {result}")

                        if invalid_count > 0 and parent:
                            QMessageBox.warning(
                                parent,
                                "Validation Warning",
                                f"{invalid_count} file(s) failed validation and were skipped."
                            )

                        results = valid_results

                    # 경로 기억
                    if results and remember_path and DialogBoxConfig.remember_paths:
                        DialogBoxConfig.last_file_path = results[0].parent

                    logger.info(f"Selected {len(results)} file(s)")
                    return results

            return []

        except Exception as e:
            logger.error(f"Error in open_files: {e}")
            return []

    @staticmethod
    def save_file(
        parent=None,
        title: str = "Save file",
        filters: str = "All Files (*)",
        path: Optional[str | Path] = None,
        default_filename: str = "",
        remember_path: bool = True,
        confirm_overwrite: Optional[bool] = None
    ) -> Optional[Path]:
        """
        파일 저장 다이얼로그

        Args:
            parent: 부모 위젯
            title: 다이얼로그 제목
            filters: 파일 필터
            path: 시작 경로
            default_filename: 기본 파일명
            remember_path: 선택한 경로 기억 여부
            confirm_overwrite: 덮어쓰기 확인 (None이면 전역 설정 사용)

        Returns:
            저장할 파일 경로 (Path) 또는 None
        """
        try:
            if path is None and DialogBoxConfig.remember_paths:
                path = DialogBoxConfig.last_file_path
            elif path is None:
                path = Path.home()
            else:
                path = Path(path)

            if path.is_file():
                path = path.parent

            if not path.exists():
                path = Path.home()

            dlg = QFileDialog(parent)
            dlg.setWindowTitle(title)
            dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
            dlg.setNameFilter(filters)
            dlg.setDirectory(str(path))

            # 기본 파일명 설정
            if default_filename:
                dlg.selectFile(default_filename)

            # 덮어쓰기 확인 설정
            if confirm_overwrite is None:
                confirm_overwrite = DialogBoxConfig.confirm_overwrite

            if confirm_overwrite:
                dlg.setOption(QFileDialog.Option.DontConfirmOverwrite, False)
            else:
                dlg.setOption(QFileDialog.Option.DontConfirmOverwrite, True)

            if dlg.exec():
                selected_files = dlg.selectedFiles()
                if selected_files:
                    result = Path(selected_files[0])

                    # 확장자가 없으면 필터에서 추출하여 추가
                    if not result.suffix and filters != "All Files (*)":
                        # "Text Files (*.txt)" -> ".txt"
                        import re
                        match = re.search(r'\*\.(\w+)', filters)
                        if match:
                            ext = match.group(1)
                            result = result.with_suffix(f'.{ext}')

                    # 경로 기억
                    if remember_path and DialogBoxConfig.remember_paths:
                        DialogBoxConfig.last_file_path = result.parent

                    logger.info(f"Save file path: {result}")
                    return result

            return None

        except Exception as e:
            logger.error(f"Error in save_file: {e}")
            return None


# 편의 함수들
def select_folder(parent=None, title: str = "Select folder") -> Optional[Path]:
    """빠른 폴더 선택"""
    return DirDialogBox.open_folder(parent, title)


def select_file(parent=None, title: str = "Select file", filters: str = "All Files (*)") -> Optional[Path]:
    """빠른 파일 선택"""
    return FileDialogBox.open_file(parent, title, filters)


def select_files(parent=None, title: str = "Select files", filters: str = "All Files (*)") -> list[Path]:
    """빠른 복수 파일 선택"""
    return FileDialogBox.open_files(parent, title, filters)


def save_as(parent=None, title: str = "Save as", filters: str = "All Files (*)", default_filename: str = "") -> Optional[Path]:
    """빠른 저장"""
    return FileDialogBox.save_file(parent, title, filters, default_filename=default_filename)


# 자주 사용하는 필터들
class CommonFilters:
    """자주 사용하는 파일 필터"""

    ALL = "All Files (*)"
    TEXT = "Text Files (*.txt);;All Files (*)"
    JSON = "JSON Files (*.json);;All Files (*)"
    CSV = "CSV Files (*.csv);;All Files (*)"
    EXCEL = "Excel Files (*.xlsx *.xls);;All Files (*)"
    IMAGE = "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
    PDF = "PDF Files (*.pdf);;All Files (*)"
    CAD = "CAD Files (*.stp *.step *.iges *.igs);;STL Files (*.stl);;All Files (*)"
    PYTHON = "Python Files (*.py);;All Files (*)"
    CPP = "C++ Files (*.cpp *.h *.hpp);;All Files (*)"

    @staticmethod
    def custom(*extensions: str) -> str:
        """
        커스텀 필터 생성

        Args:
            *extensions: 확장자 리스트 (예: "txt", "log")

        Returns:
            필터 문자열
        """
        ext_pattern = " ".join(f"*.{ext}" for ext in extensions)
        return f"Files ({ext_pattern});;All Files (*)"
