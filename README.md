# NextLib

Python 유틸리티 라이브러리 모음

## 모듈 구성

### 1. openfoam
OpenFOAM 설정 파일 파싱 및 편집 라이브러리

- **PyFoamCase**: OpenFOAM 파일 읽기/쓰기/수정
- 주요 클래스: `FoamFile`
- [자세한 정보](openfoam/README.md)

#### 주요 기능
- OpenFOAM 설정 파일 파싱
- 값 조회/수정/삽입/삭제
- blocks, vertices, regions 등 특수 구조 지원
- 안전한 파일 저장

#### 사용 예제
```python
from nextlib.openfoam.PyFoamCase.foamfile import FoamFile

foam = FoamFile()
foam.load("path/to/file")
value = foam.get_value("outlet.type")
foam.set_value("outlet.type", "wall")
foam.save()
```

---

### 2. base
데이터 관리 기반 클래스

#### BaseCase
GUI 프로그램용 데이터 관리 클래스

**주요 기능:**
- JSON 기반 데이터 저장/로드
- 자동 백업 시스템
- 변경 감지 및 이벤트 콜백
- 중첩 dataclass 지원
- 데이터 검증
- 자동 저장 옵션
- Import/Export 기능

**사용 예제:**
```python
from dataclasses import dataclass
from nextlib.base.basecase_improved import BaseCase

@dataclass
class AppSettings(BaseCase):
    theme: str = "dark"
    language: str = "ko"

    def __post_init__(self):
        super().__post_init__()
        self.file = "settings.json"

settings = AppSettings()
settings.set_path("./config")
settings.enable_backup(True)
settings.load()

settings.theme = "light"  # 변경 감지
settings.save()  # 백업 포함 저장
```

[자세한 정보](base/README_BaseCase.md)

---

## 설치

```bash
# 저장소 클론
git clone <repository-url>

# 또는 직접 경로 추가
import sys
sys.path.insert(0, "/path/to/nextlib")
```

---

## 요구사항

- Python 3.10+
- 표준 라이브러리만 사용 (외부 의존성 없음)

---

## 테스트

### OpenFOAM 모듈
```bash
python -m openfoam.PyFoamCase.test_self_check
```

### Base 모듈
```bash
python base/example_usage.py
```

---

## 라이선스

MIT License

---

## 변경 이력

### 2026-01-16
- OpenFOAM 모듈 중복 코드 정리
- BaseCase 대폭 개선
  - 에러 처리 추가
  - 백업 시스템 구현
  - 변경 감지 및 콜백 시스템
  - 중첩 dataclass 지원
  - 자동 저장 기능
- 자체 점검 테스트 추가

---

## 기여

이슈 및 PR 환영합니다.
