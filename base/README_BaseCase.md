# BaseCase 개선 가이드

## 개요

GUI 프로그램에서 데이터 관리를 위한 개선된 BaseCase 클래스입니다.

## 기존 vs 개선 비교

### 기존 BaseCase (basecase.py)

```python
@dataclass
class AppSettings(BaseCase):
    theme: str = "dark"

settings = AppSettings()
settings.set_path("./config")
settings.theme = "light"
settings.save()  # ❌ 에러 처리 없음, 백업 없음
```

**문제점:**
- ❌ 에러 처리 부재 (저장 실패 시 데이터 손실)
- ❌ 백업 기능 없음
- ❌ 변경 감지 없음
- ❌ 중첩 객체 미지원
- ❌ 데이터 검증 없음

---

### 개선된 BaseCase (basecase_improved.py)

```python
@dataclass
class AppSettings(BaseCase):
    theme: str = "dark"

    def __post_init__(self):
        super().__post_init__()

settings = AppSettings()
settings.set_path("./config")

# 변경 감지 콜백
settings.add_change_callback(lambda f, o, n: print(f"{f} changed"))

settings.theme = "light"  # ✅ 자동으로 dirty 플래그 설정
settings.save()  # ✅ 안전한 저장 + 백업
```

**개선 사항:**
- ✅ 완전한 에러 처리
- ✅ 자동 백업 시스템
- ✅ 변경 감지 및 이벤트
- ✅ 중첩 dataclass 지원
- ✅ 데이터 검증 기능
- ✅ 자동 저장 옵션
- ✅ Import/Export 기능
- ✅ 변경 사항 추적

---

## 주요 기능

### 1. 자동 백업
```python
settings = AppSettings()
settings.enable_backup(enabled=True, max_backups=5)
settings.save()  # 자동으로 백업 생성
```

**특징:**
- 저장 전 자동 백업 생성
- 타임스탬프 기반 백업 파일명
- 최대 백업 개수 제한
- 손상된 파일 발생 시 자동 복구 시도

---

### 2. 변경 감지 및 콜백
```python
def on_theme_change(field, old_value, new_value):
    if field == "theme":
        apply_theme(new_value)

settings.add_change_callback(on_theme_change)
settings.theme = "dark"  # 콜백 자동 실행
```

**활용 사례:**
- GUI 실시간 업데이트
- 설정 변경 로깅
- 검증 로직 연결
- Undo/Redo 시스템

---

### 3. 자동 저장
```python
settings = AppSettings()
settings.enable_auto_save(True)
settings.theme = "light"  # 자동으로 저장됨
```

**장점:**
- 사용자가 저장 버튼을 누를 필요 없음
- 데이터 손실 방지
- 실시간 동기화

---

### 4. 중첩 데이터 구조
```python
@dataclass
class WindowGeometry(BaseCase):
    width: int = 800
    height: int = 600

@dataclass
class AppState(BaseCase):
    window: WindowGeometry = None

    def __post_init__(self):
        super().__post_init__()
        if self.window is None:
            self.window = WindowGeometry()

state = AppState()
state.window.width = 1024  # 중첩 객체 지원
state.save()
```

---

### 5. 데이터 검증
```python
@dataclass
class AppSettings(BaseCase):
    font_size: int = 12

    def validate(self) -> tuple[bool, List[str]]:
        errors = []
        if self.font_size < 8 or self.font_size > 72:
            errors.append("Font size must be between 8 and 72")
        return len(errors) == 0, errors

settings = AppSettings()
settings.font_size = 100

valid, errors = settings.validate()
if not valid:
    print("Validation errors:", errors)
```

---

### 6. 변경 사항 추적
```python
settings = AppSettings()
settings.load()

settings.theme = "dark"
settings.font_size = 16

# 변경된 필드만 확인
changes = settings.get_changes()
# {'theme': 'dark', 'font_size': 16}

# 특정 필드 원래대로
settings.reset_field("theme")
```

---

### 7. Import/Export
```python
# 내보내기
settings.export_to_file("./backup/settings_backup.json")

# 가져오기
settings2 = AppSettings()
settings2.import_from_file("./backup/settings_backup.json")
```

---

### 8. 안전한 저장
```python
settings.save(mode=SaveMode.SAFE)  # 임시파일 -> 원본 대체
settings.save(mode=SaveMode.NORMAL)  # 직접 저장
```

**SAFE 모드:**
1. 임시 파일에 저장
2. 검증
3. 원본 대체
4. 실패 시 롤백

---

## GUI 프로그램 통합 예제

### PyQt/PySide
```python
from PyQt6.QtCore import QObject, pyqtSignal

@dataclass
class AppSettings(BaseCase):
    theme: str = "dark"

class SettingsManager(QObject):
    theme_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.settings = AppSettings()
        self.settings.set_path("./config")
        self.settings.add_change_callback(self._on_change)

    def _on_change(self, field, old, new):
        if field == "theme":
            self.theme_changed.emit(new)

# 사용
manager = SettingsManager()
manager.theme_changed.connect(lambda theme: print(f"Theme: {theme}"))
manager.settings.theme = "light"  # 시그널 발생
```

---

### Tkinter
```python
import tkinter as tk

class SettingsDialog:
    def __init__(self, parent):
        self.settings = AppSettings()
        self.settings.set_path("./config")
        self.settings.load()

        # GUI 생성
        self.theme_var = tk.StringVar(value=self.settings.theme)
        self.theme_var.trace_add("write", self._on_theme_change)

    def _on_theme_change(self, *args):
        self.settings.theme = self.theme_var.get()
        # 자동 저장 활성화 시 자동 저장됨
```

---

### wxPython
```python
class SettingsPanel(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = AppSettings()
        self.settings.set_path("./config")
        self.settings.add_change_callback(self._on_setting_change)

        # 설정 변경 시 자동으로 GUI 업데이트
        self.theme_choice = wx.Choice(self, choices=["light", "dark"])
        self.theme_choice.Bind(wx.EVT_CHOICE, self._on_theme_select)

    def _on_theme_select(self, event):
        self.settings.theme = self.theme_choice.GetStringSelection()

    def _on_setting_change(self, field, old, new):
        # GUI 업데이트 로직
        pass
```

---

## 마이그레이션 가이드

### 기존 코드
```python
# 기존
settings = OldBaseCase()
settings.set_path("./config")
settings.load()
settings.theme = "dark"
settings.save()
```

### 새 코드
```python
# 개선
settings = AppSettings()  # BaseCase 상속
settings.set_path("./config")
settings.enable_backup(True)  # 백업 활성화
settings.load()
settings.theme = "dark"
settings.save()  # 자동 백업 포함
```

**변경 최소화:**
- API 대부분 동일
- `__post_init__()` 추가만 필요
- 기존 JSON 파일 호환

---

## 권장 사용 패턴

### 1. 애플리케이션 설정
```python
@dataclass
class AppSettings(BaseCase):
    # 외관
    theme: str = "dark"
    language: str = "ko"
    font_family: str = "Arial"
    font_size: int = 12

    # 동작
    auto_save: bool = True
    auto_backup: bool = True
    check_updates: bool = True

    # 최근 파일
    recent_files: List[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        self.file = "settings.json"
```

---

### 2. 사용자 데이터
```python
@dataclass
class UserProfile(BaseCase):
    username: str = ""
    email: str = ""
    avatar_path: str = ""
    preferences: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.file = "user_profile.json"

    def validate(self) -> tuple[bool, List[str]]:
        errors = []
        if not self.email or "@" not in self.email:
            errors.append("Invalid email")
        return len(errors) == 0, errors
```

---

### 3. 프로젝트 파일
```python
@dataclass
class ProjectFile(BaseCase):
    project_name: str = "Untitled"
    version: str = "1.0.0"
    created_date: str = ""
    author: str = ""
    files: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        self.file = "project.json"
```

---

## 성능 고려사항

### 자동 저장 사용 시
```python
# ❌ 나쁜 예: 루프에서 자동 저장
settings.enable_auto_save(True)
for i in range(1000):
    settings.some_value = i  # 1000번 저장됨

# ✅ 좋은 예: 일괄 변경 후 저장
settings.enable_auto_save(False)
for i in range(1000):
    settings.some_value = i
settings.save()  # 1번만 저장
```

---

### 대용량 데이터
```python
# ❌ 나쁜 예: 모든 데이터를 dataclass에
@dataclass
class HugeData(BaseCase):
    massive_list: List[dict] = field(default_factory=list)  # 메모리 부족

# ✅ 좋은 예: 참조만 저장
@dataclass
class DataReference(BaseCase):
    data_file_path: str = ""  # 실제 데이터는 별도 파일
```

---

## 에러 처리 예제

```python
settings = AppSettings()

try:
    settings.set_path("./config")
    if not settings.load():
        print("Failed to load settings, using defaults")

    settings.theme = "dark"

    if not settings.save():
        print("Failed to save settings")

except Exception as e:
    print(f"Error: {e}")
    # 백업에서 복구 시도
    settings.reload()
```

---

## 테스트 코드

```python
def test_settings():
    settings = AppSettings()
    settings.set_path("./test_config")

    # 저장/로드 테스트
    settings.theme = "light"
    assert settings.save()

    settings2 = AppSettings()
    settings2.set_path("./test_config")
    assert settings2.load()
    assert settings2.theme == "light"

    # 변경 감지 테스트
    assert not settings2.is_dirty()
    settings2.theme = "dark"
    assert settings2.is_dirty()

    # 정리
    import shutil
    shutil.rmtree("./test_config")
```

---

## 결론

### 사용 추천:
✅ GUI 애플리케이션 설정
✅ 사용자 프로필/상태
✅ 프로젝트 파일
✅ 캐시 데이터

### 사용 비추천:
❌ 대용량 데이터 (DB 사용 권장)
❌ 실시간 스트리밍 데이터
❌ 바이너리 데이터 (별도 처리 필요)

### 핵심 장점:
1. **안전성**: 백업 + 복구 기능
2. **편리성**: 자동 저장 + 변경 감지
3. **확장성**: 콜백 시스템 + 검증
4. **호환성**: 기존 코드 최소 변경
