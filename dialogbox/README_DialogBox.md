# DialogBox 개선 가이드

## 개요

PySide6 기반의 파일/폴더 선택 다이얼로그 유틸리티 클래스입니다.

---

## 기존 vs 개선 비교

### 기존 DialogBox (dialogbox.py)

```python
from nextlib.dialogbox.dialogbox import FileDialogBox

# 파일 선택
file = FileDialogBox.open_file(
    title="파일 열기",
    filters="Text Files (*.txt);;All Files (*)"
)
# 반환: str | None
```

**문제점:**
- ❌ 반환 타입 불일치 (str vs Path)
- ❌ 에러 처리 없음
- ❌ 경로 기억 기능 없음
- ❌ 파일 검증 불가
- ❌ 기본 파일명 지정 불가

---

### 개선된 DialogBox (dialogbox_improved.py)

```python
from nextlib.dialogbox.dialogbox_improved import FileDialogBox, CommonFilters

# 파일 선택
file = FileDialogBox.open_file(
    title="파일 열기",
    filters=CommonFilters.TEXT,
    validate=lambda p: p.stat().st_size < 1024*1024  # 1MB 제한
)
# 반환: Path | None
```

**개선 사항:**
- ✅ 일관된 반환 타입 (Path)
- ✅ 완전한 에러 처리
- ✅ 경로 자동 기억
- ✅ 파일 검증 기능
- ✅ 기본 파일명 지정
- ✅ 로깅 지원
- ✅ 편의 함수 제공
- ✅ 공통 필터 제공

---

## 주요 개선 사항

### 1. 일관된 반환 타입

**기존:**
```python
file = FileDialogBox.open_file()    # str | None
files = FileDialogBox.open_files()  # list[Path]  ❌ 불일치
```

**개선:**
```python
file = FileDialogBox.open_file()    # Path | None
files = FileDialogBox.open_files()  # list[Path]   ✅ 일관성
```

---

### 2. 에러 처리

**기존:**
```python
# 에러 발생 시 프로그램 종료
dlg.selectedFiles()[0]  # IndexError 가능
```

**개선:**
```python
try:
    selected = dlg.selectedFiles()
    if selected:
        return Path(selected[0])
    return None
except Exception as e:
    logger.error(f"Error: {e}")
    return None
```

---

### 3. 경로 기억 기능

**개선:**
```python
# 첫 번째 선택
file1 = FileDialogBox.open_file()  # /home/user/documents/file1.txt

# 두 번째 선택 - 자동으로 이전 폴더에서 시작
file2 = FileDialogBox.open_file()  # /home/user/documents/ 에서 시작

# 설정으로 제어 가능
DialogBoxConfig.remember_paths = False  # 비활성화
```

---

### 4. 파일 검증

**개선:**
```python
def validate_file(path: Path) -> bool:
    # 파일 크기 제한
    if path.stat().st_size > 10 * 1024 * 1024:  # 10MB
        return False

    # 확장자 검증
    if path.suffix not in ['.txt', '.log']:
        return False

    return True

file = FileDialogBox.open_file(
    validate=validate_file
)
```

**복수 파일 검증:**
```python
files = FileDialogBox.open_files(
    validate=validate_file
)
# 유효하지 않은 파일은 자동으로 제외되고 경고 표시
```

---

### 5. 기본 파일명 지정

**개선:**
```python
# 저장 다이얼로그에 기본 파일명 표시
save_path = FileDialogBox.save_file(
    filters=CommonFilters.JSON,
    default_filename="config.json"
)
```

---

### 6. 전역 설정

**개선:**
```python
from nextlib.dialogbox.dialogbox_improved import DialogBoxConfig

# 경로 기억 기능
DialogBoxConfig.remember_paths = True  # 기본값

# 숨김 파일 표시
DialogBoxConfig.show_hidden_files = False

# 덮어쓰기 확인
DialogBoxConfig.confirm_overwrite = True
```

---

### 7. 공통 필터

**기존:**
```python
# 매번 필터 문자열 작성
filters = "Text Files (*.txt);;All Files (*)"
```

**개선:**
```python
from nextlib.dialogbox.dialogbox_improved import CommonFilters

# 미리 정의된 필터 사용
CommonFilters.TEXT     # "Text Files (*.txt);;All Files (*)"
CommonFilters.JSON     # "JSON Files (*.json);;All Files (*)"
CommonFilters.IMAGE    # "Image Files (*.png *.jpg ...);;All Files (*)"
CommonFilters.CAD      # "CAD Files (*.stp *.step ...);;All Files (*)"

# 커스텀 필터 생성
custom = CommonFilters.custom("log", "out", "txt")
# "Files (*.log *.out *.txt);;All Files (*)"
```

---

### 8. 편의 함수

**개선:**
```python
from nextlib.dialogbox.dialogbox_improved import (
    select_folder,   # 빠른 폴더 선택
    select_file,     # 빠른 파일 선택
    select_files,    # 빠른 복수 파일 선택
    save_as,         # 빠른 저장
)

# 간단한 사용
folder = select_folder()
file = select_file(filters=CommonFilters.TEXT)
files = select_files(filters=CommonFilters.IMAGE)
save_path = save_as(default_filename="output.txt")
```

---

## 사용 예제

### 기본 사용

```python
from nextlib.dialogbox.dialogbox_improved import (
    FileDialogBox, DirDialogBox, CommonFilters
)

# 폴더 선택
folder = DirDialogBox.open_folder(
    parent=self,
    title="프로젝트 폴더 선택"
)

# 파일 열기
file = FileDialogBox.open_file(
    parent=self,
    title="설정 파일 열기",
    filters=CommonFilters.JSON
)

# 여러 파일 선택
files = FileDialogBox.open_files(
    parent=self,
    title="이미지 선택",
    filters=CommonFilters.IMAGE
)

# 파일 저장
save_path = FileDialogBox.save_file(
    parent=self,
    title="결과 저장",
    filters=CommonFilters.CSV,
    default_filename="result.csv"
)
```

---

### 고급 사용

#### 1. 파일 크기 제한
```python
def size_validator(path: Path) -> bool:
    max_size = 5 * 1024 * 1024  # 5MB
    return path.stat().st_size <= max_size

file = FileDialogBox.open_file(
    title="파일 선택 (5MB 이하)",
    validate=size_validator
)
```

#### 2. 내용 검증
```python
def json_validator(path: Path) -> bool:
    try:
        import json
        with open(path, 'r') as f:
            json.load(f)
        return True
    except:
        return False

file = FileDialogBox.open_file(
    title="유효한 JSON 파일 선택",
    filters=CommonFilters.JSON,
    validate=json_validator
)
```

#### 3. 경로 기억 제어
```python
# 이번만 경로 기억 안함
file = FileDialogBox.open_file(
    remember_path=False
)

# 전역 설정 변경
DialogBoxConfig.remember_paths = False
```

#### 4. 덮어쓰기 확인 제어
```python
# 덮어쓰기 확인 안함
save_path = FileDialogBox.save_file(
    confirm_overwrite=False
)
```

---

### GUI 프로그램 통합

#### PyQt/PySide
```python
from PySide6.QtWidgets import QMainWindow, QPushButton
from nextlib.dialogbox.dialogbox_improved import select_file, CommonFilters

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        btn = QPushButton("파일 열기", self)
        btn.clicked.connect(self.open_file)

    def open_file(self):
        file = select_file(
            parent=self,
            title="파일 선택",
            filters=CommonFilters.TEXT
        )

        if file:
            print(f"Selected: {file}")
            # 파일 처리
```

---

## 공통 필터 목록

```python
CommonFilters.ALL      # All Files (*)
CommonFilters.TEXT     # Text Files (*.txt)
CommonFilters.JSON     # JSON Files (*.json)
CommonFilters.CSV      # CSV Files (*.csv)
CommonFilters.EXCEL    # Excel Files (*.xlsx *.xls)
CommonFilters.IMAGE    # Image Files (*.png *.jpg ...)
CommonFilters.PDF      # PDF Files (*.pdf)
CommonFilters.CAD      # CAD Files (*.stp *.step ...)
CommonFilters.PYTHON   # Python Files (*.py)
CommonFilters.CPP      # C++ Files (*.cpp *.h *.hpp)

# 커스텀 필터
CommonFilters.custom("ext1", "ext2", ...)
```

---

## 마이그레이션 가이드

### 기존 코드
```python
from nextlib.dialogbox.dialogbox import FileDialogBox

file = FileDialogBox.open_file(
    title="파일 열기",
    filters="Text Files (*.txt);;All Files (*)"
)
# file: str | None

if file:
    path = Path(file)  # 수동 변환 필요
```

### 새 코드
```python
from nextlib.dialogbox.dialogbox_improved import FileDialogBox, CommonFilters

file = FileDialogBox.open_file(
    title="파일 열기",
    filters=CommonFilters.TEXT
)
# file: Path | None (자동으로 Path 객체)

if file:
    # 바로 Path 메서드 사용 가능
    content = file.read_text()
```

**주요 변경점:**
1. 반환 타입: `str | None` → `Path | None`
2. 필터: 문자열 → `CommonFilters` 상수 사용 권장
3. 새 기능: `validate`, `default_filename`, `remember_path` 매개변수 추가

---

## 성능 및 제한사항

### 성능
- ✅ 경로 캐싱으로 빠른 시작
- ✅ 검증 함수는 선택 시에만 실행 (성능 영향 최소)

### 제한사항
- 경로 기억은 프로세스 단위 (재시작 시 초기화)
- 영구 저장이 필요하면 설정 파일에 저장 필요

---

## 에러 처리

모든 메서드는 예외 발생 시 `None` 또는 빈 리스트를 반환합니다.

```python
try:
    file = FileDialogBox.open_file()
    if file:
        # 성공
        process_file(file)
    else:
        # 취소 또는 에러
        print("No file selected")
except Exception as e:
    # 이 코드는 실행되지 않음 (내부에서 처리)
    pass
```

에러는 로그로 기록됩니다:
```python
import logging
logging.basicConfig(level=logging.INFO)

# 로그 확인
# ERROR - Error in open_file: ...
```

---

## 테스트

```python
# 예제 실행
python dialogbox/example_dialogbox.py
```

---

## 결론

### 사용 권장:
✅ 모든 새 프로젝트
✅ 파일 검증이 필요한 경우
✅ UX 개선이 필요한 경우

### 기존 코드 유지:
⚠️ 레거시 프로젝트 (호환성 유지 필요)
⚠️ 단순한 스크립트 (오버헤드 불필요)

### 핵심 장점:
1. **안정성**: 완전한 에러 처리
2. **편리성**: 경로 기억 + 공통 필터
3. **확장성**: 검증 기능 + 커스터마이징
4. **일관성**: 통일된 반환 타입
