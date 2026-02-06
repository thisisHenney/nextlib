"""
개선된 BaseCase - GUI 프로그램용 데이터 관리 클래스

주요 기능:
- 완전한 에러 처리
- 자동 백업 시스템
- 변경 감지 및 이벤트 시스템
- 중첩 dataclass 지원
- 데이터 검증
- 부분 저장/로드
- 자동 저장 (옵션)
"""

import logging
import json
import shutil
from dataclasses import dataclass, asdict, fields, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from enum import Enum


logger = logging.getLogger(__name__)


class SaveMode(Enum):
    """저장 모드"""
    NORMAL = "normal"           # 일반 저장
    BACKUP = "backup"           # 백업 포함 저장
    SAFE = "safe"              # 안전 저장 (임시파일 -> 원본 대체)


@dataclass
class BaseCase:
    """
    개선된 BaseCase 클래스

    사용 예제:
        @dataclass
        class AppSettings(BaseCase):
            theme: str = "dark"
            language: str = "ko"
            auto_save: bool = True
            recent_files: List[str] = None

            def __post_init__(self):
                super().__post_init__()
                if self.recent_files is None:
                    self.recent_files = []

        settings = AppSettings()
        settings.set_path("./config")
        settings.load()
        settings.theme = "light"  # 변경 감지됨
        settings.save()
    """

    name: str = ""
    path: str = ""
    file: str = "base_data.json"

    def __post_init__(self):
        """초기화 후 처리"""
        self._initialized = False
        self._change_callbacks: List[Callable] = []
        self._dirty = False  # 변경 여부 플래그
        self._auto_save = False
        self._backup_enabled = True
        self._max_backups = 5
        self._original_data = {}  # 로드된 원본 데이터
        self._excluded_fields = {"path", "file", "name"}

        # 내부 상태 필드 (저장하지 않음)
        self._internal_fields = {
            "_initialized", "_change_callbacks", "_dirty", "_auto_save",
            "_backup_enabled", "_max_backups", "_original_data",
            "_excluded_fields", "_internal_fields"
        }

        self._initialized = True

    # ============================================================
    # 기본 설정 메서드
    # ============================================================

    def init(self, name: str = "", file: str = "", path: str = ""):
        """
        초기화

        Args:
            name: 케이스 이름
            file: 파일명
            path: 저장 경로
        """
        if name:
            self.name = name
        if file:
            self.file = file
        if path:
            self.set_path(path)

    def set_defaults(self):
        """기본값으로 리셋 (서브클래스에서 오버라이드)"""
        self.name = ""
        self.path = ""
        self._dirty = False

    def set_name(self, name: str):
        """이름 설정"""
        self.name = name

    def set_path(self, path: str):
        """
        경로 설정 및 디렉토리 자동 생성

        Args:
            path: 저장 경로
        """
        self.path = path
        p = Path(self.path)

        try:
            if not p.is_dir():
                p.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {p}")
        except Exception as e:
            logger.error(f"Failed to create directory {p}: {e}")
            raise

        if not self.name:
            self.name = p.name

    def enable_auto_save(self, enabled: bool = True):
        """자동 저장 활성화/비활성화"""
        self._auto_save = enabled

    def enable_backup(self, enabled: bool = True, max_backups: int = 5):
        """
        백업 기능 설정

        Args:
            enabled: 백업 활성화 여부
            max_backups: 최대 백업 파일 개수
        """
        self._backup_enabled = enabled
        self._max_backups = max_backups

    # ============================================================
    # 변경 감지 및 이벤트 시스템
    # ============================================================

    def __setattr__(self, name: str, value: Any):
        """속성 변경 감지"""
        # 초기화 전이거나 내부 필드는 그냥 설정
        if not hasattr(self, '_initialized') or not self._initialized:
            super().__setattr__(name, value)
            return

        if name in self._internal_fields:
            super().__setattr__(name, value)
            return

        # 기존 값과 다를 때만 변경 처리
        old_value = getattr(self, name, None)
        if old_value != value:
            super().__setattr__(name, value)

            # dirty 플래그 설정 (제외 필드 제외)
            if name not in self._excluded_fields:
                self._dirty = True
                self._on_change(name, old_value, value)

                # 자동 저장
                if self._auto_save:
                    try:
                        self.save()
                    except Exception as e:
                        logger.error(f"Auto-save failed: {e}")
        else:
            super().__setattr__(name, value)

    def _on_change(self, field_name: str, old_value: Any, new_value: Any):
        """
        속성 변경 시 호출되는 내부 메서드

        Args:
            field_name: 변경된 필드명
            old_value: 이전 값
            new_value: 새 값
        """
        # 콜백 실행
        for callback in self._change_callbacks:
            try:
                callback(field_name, old_value, new_value)
            except Exception as e:
                logger.error(f"Change callback error: {e}")

    def add_change_callback(self, callback: Callable):
        """
        변경 감지 콜백 추가

        Args:
            callback: 콜백 함수 (field_name, old_value, new_value)를 인자로 받음

        Example:
            def on_theme_change(field, old, new):
                if field == "theme":
                    print(f"Theme changed: {old} -> {new}")

            settings.add_change_callback(on_theme_change)
        """
        if callback not in self._change_callbacks:
            self._change_callbacks.append(callback)

    def remove_change_callback(self, callback: Callable):
        """변경 감지 콜백 제거"""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def is_dirty(self) -> bool:
        """변경 사항이 있는지 확인"""
        return self._dirty

    def mark_clean(self):
        """변경 사항 초기화"""
        self._dirty = False

    # ============================================================
    # 저장 메서드
    # ============================================================

    def save(self, mode: SaveMode = SaveMode.SAFE) -> bool:
        """
        데이터 저장

        Args:
            mode: 저장 모드

        Returns:
            성공 여부
        """
        if not self.path:
            logger.error("Path is not set. Call set_path() first.")
            return False

        file_path = Path(self.path) / self.file

        try:
            # 데이터 준비
            data = self._to_dict()

            # 백업 생성
            if self._backup_enabled and file_path.exists():
                self._create_backup(file_path)

            # 저장 모드에 따라 처리
            if mode == SaveMode.SAFE:
                self._save_safe(file_path, data)
            else:
                self._save_normal(file_path, data)

            self._dirty = False
            self._original_data = data.copy()
            logger.info(f"Data saved: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            return False

    def _save_normal(self, file_path: Path, data: dict):
        """일반 저장"""
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _save_safe(self, file_path: Path, data: dict):
        """안전 저장 (임시파일 사용)"""
        temp_file = file_path.with_suffix('.tmp')

        try:
            # 임시 파일에 저장
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # 원본 파일 대체
            if file_path.exists():
                file_path.unlink()
            temp_file.rename(file_path)

        except Exception as e:
            # 실패 시 임시 파일 삭제
            if temp_file.exists():
                temp_file.unlink()
            raise e

    def _create_backup(self, file_path: Path):
        """백업 파일 생성"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"
            backup_path = file_path.parent / "backups"

            # 백업 디렉토리 생성
            backup_path.mkdir(exist_ok=True)

            # 백업 파일 복사
            backup_file = backup_path / backup_name
            shutil.copy2(file_path, backup_file)

            # 오래된 백업 삭제
            self._cleanup_old_backups(backup_path, file_path.stem)

            logger.info(f"Backup created: {backup_file}")

        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")

    def _cleanup_old_backups(self, backup_dir: Path, prefix: str):
        """오래된 백업 파일 삭제"""
        try:
            backups = sorted(
                backup_dir.glob(f"{prefix}_backup_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # 최대 개수를 초과하는 백업 삭제
            for old_backup in backups[self._max_backups:]:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup}")

        except Exception as e:
            logger.warning(f"Failed to cleanup old backups: {e}")

    # ============================================================
    # 로드 메서드
    # ============================================================

    def load(self, create_if_missing: bool = True) -> bool:
        """
        데이터 로드

        Args:
            create_if_missing: 파일이 없을 때 새로 생성할지 여부

        Returns:
            성공 여부
        """
        if not self.path:
            logger.error("Path is not set. Call set_path() first.")
            return False

        file_path = Path(self.path) / self.file

        # 파일이 없으면 생성
        if not file_path.exists():
            if create_if_missing:
                logger.info(f"File not found, creating new: {file_path}")
                return self.save()
            else:
                logger.error(f"File not found: {file_path}")
                return False

        try:
            # JSON 로드
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 데이터 적용
            self._from_dict(data)

            self._original_data = data.copy()
            self._dirty = False
            logger.info(f"Data loaded: {file_path}")
            return True

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {file_path}: {e}")

            # 백업에서 복구 시도
            if self._try_restore_from_backup(file_path):
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            return False

    def _try_restore_from_backup(self, file_path: Path) -> bool:
        """백업에서 복구 시도"""
        try:
            backup_dir = file_path.parent / "backups"
            if not backup_dir.exists():
                return False

            backups = sorted(
                backup_dir.glob(f"{file_path.stem}_backup_*"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            for backup in backups:
                try:
                    logger.info(f"Trying to restore from backup: {backup}")
                    with open(backup, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    self._from_dict(data)

                    # 복구된 데이터를 저장
                    self.save()

                    logger.info(f"Successfully restored from backup: {backup}")
                    return True

                except Exception as e:
                    logger.warning(f"Failed to restore from {backup}: {e}")
                    continue

            return False

        except Exception as e:
            logger.error(f"Backup restore failed: {e}")
            return False

    def reload(self) -> bool:
        """파일에서 다시 로드 (변경사항 버림)"""
        return self.load(create_if_missing=False)

    # ============================================================
    # 직렬화 메서드
    # ============================================================

    def _to_dict(self, include_internal: bool = False) -> dict:
        """
        dataclass를 dict로 변환 (중첩 dataclass 지원)

        Args:
            include_internal: 내부 필드 포함 여부

        Returns:
            딕셔너리
        """
        result = {}

        for field in fields(self):
            field_name = field.name

            # 제외 필드 건너뛰기
            if field_name in self._excluded_fields:
                continue

            # 내부 필드 건너뛰기
            if not include_internal and field_name in self._internal_fields:
                continue

            value = getattr(self, field_name)

            # 중첩 dataclass 처리
            if is_dataclass(value):
                if hasattr(value, '_to_dict'):
                    result[field_name] = value._to_dict()
                else:
                    result[field_name] = asdict(value)

            # 리스트 내부의 dataclass 처리
            elif isinstance(value, list):
                result[field_name] = [
                    item._to_dict() if is_dataclass(item) and hasattr(item, '_to_dict')
                    else asdict(item) if is_dataclass(item)
                    else item
                    for item in value
                ]

            # 일반 값
            else:
                result[field_name] = value

        return result

    def _from_dict(self, data: dict):
        """
        dict에서 dataclass로 변환 (중첩 dataclass 지원)

        Args:
            data: 로드할 딕셔너리
        """
        for key, value in data.items():
            if hasattr(self, key) and key not in self._excluded_fields:
                try:
                    # 필드 타입 가져오기
                    field_type = None
                    for field in fields(self):
                        if field.name == key:
                            field_type = field.type
                            break

                    # 타입에 맞게 변환
                    if field_type and is_dataclass(field_type):
                        # 중첩 dataclass 처리
                        if isinstance(value, dict):
                            nested_obj = field_type()
                            if hasattr(nested_obj, '_from_dict'):
                                nested_obj._from_dict(value)
                            else:
                                for k, v in value.items():
                                    if hasattr(nested_obj, k):
                                        setattr(nested_obj, k, v)
                            setattr(self, key, nested_obj)
                        else:
                            setattr(self, key, value)
                    else:
                        setattr(self, key, value)

                except Exception as e:
                    logger.warning(f"Failed to set field '{key}': {e}")

    # ============================================================
    # 유틸리티 메서드
    # ============================================================

    def get_changes(self) -> Dict[str, Any]:
        """
        원본과 비교하여 변경된 필드 반환

        Returns:
            {field_name: new_value} 딕셔너리
        """
        if not self._original_data:
            return {}

        current = self._to_dict()
        changes = {}

        for key, value in current.items():
            if key not in self._original_data or self._original_data[key] != value:
                changes[key] = value

        return changes

    def reset_field(self, field_name: str) -> bool:
        """
        특정 필드를 원본 값으로 되돌림

        Args:
            field_name: 필드명

        Returns:
            성공 여부
        """
        if field_name in self._original_data:
            try:
                setattr(self, field_name, self._original_data[field_name])
                return True
            except Exception as e:
                logger.error(f"Failed to reset field '{field_name}': {e}")
                return False
        return False

    def export_to_file(self, file_path: str) -> bool:
        """
        다른 파일로 내보내기

        Args:
            file_path: 내보낼 파일 경로

        Returns:
            성공 여부
        """
        try:
            export_path = Path(file_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            data = self._to_dict()
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            logger.info(f"Data exported: {export_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False

    def import_from_file(self, file_path: str) -> bool:
        """
        다른 파일에서 가져오기

        Args:
            file_path: 가져올 파일 경로

        Returns:
            성공 여부
        """
        try:
            import_path = Path(file_path)
            if not import_path.exists():
                logger.error(f"Import file not found: {import_path}")
                return False

            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._from_dict(data)
            self._dirty = True

            logger.info(f"Data imported: {import_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to import data: {e}")
            return False

    def validate(self) -> tuple[bool, List[str]]:
        """
        데이터 유효성 검사 (서브클래스에서 오버라이드)

        Returns:
            (유효 여부, 오류 메시지 리스트)
        """
        return True, []

    def __repr__(self) -> str:
        """문자열 표현"""
        data = self._to_dict()
        return f"{self.__class__.__name__}({data})"
