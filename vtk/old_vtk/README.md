# NextLib VTK Widgets

PySide6 기반 VTK 위젯 라이브러리로, GUI에 바로 통합할 수 있는 전처리 및 후처리 시각화 도구를 제공합니다.

## 주요 기능

### PreprocessWidget (전처리 위젯)
- STL, OBJ 등 메쉬 파일 로딩
- 3D 객체 선택 및 편집
- 다양한 뷰 스타일 (wireframe, surface, transparent 등)
- 카메라 컨트롤 (6방향 뷰, fit, 원근/평행 투영)
- 축 및 눈금자 표시

### PostprocessWidget (후처리 위젯)
- OpenFOAM 케이스 파일 로딩
- 필드 데이터 시각화 (압력, 속도, 온도 등)
- 3D 볼륨 및 슬라이스 뷰
- 스칼라 바 (컬러맵 범례)
- 타임스텝 지원

## 설치

```bash
pip install PySide6
pip install vtk
```

## 사용 예제

### 전처리 위젯

```python
from PySide6.QtWidgets import QApplication
from nextlib.vtk import PreprocessWidget

app = QApplication([])
widget = PreprocessWidget()
widget.show()

# STL 파일 로드
widget.load_stl("path/to/mesh.stl")

# 또는 기본 도형 추가
widget.add_geometry("cube")

app.exec()
```

### 후처리 위젯

```python
from PySide6.QtWidgets import QApplication
from nextlib.vtk import PostprocessWidget

app = QApplication([])
widget = PostprocessWidget()
widget.show()

# OpenFOAM 케이스 로드
widget.load_foam("path/to/case.foam")

# 슬라이스 모드 활성화
widget.enable_slice_mode(True)

app.exec()
```

### 듀얼 뷰어 (전처리 + 후처리)

```python
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from nextlib.vtk import PreprocessWidget, PostprocessWidget, vtk_manager

app = QApplication([])

# 메인 윈도우
main_widget = QWidget()
layout = QHBoxLayout(main_widget)

# 전처리 위젯
pre = PreprocessWidget(registry=vtk_manager)
vtk_manager.register("pre", pre)
layout.addWidget(pre)

# 후처리 위젯
post = PostprocessWidget(registry=vtk_manager)
vtk_manager.register("post", post)
layout.addWidget(post)

main_widget.show()

# 카메라 동기화 (선택사항)
vtk_manager.sync_cameras("pre", ["post"])

app.exec()
```

## 코드 구조

```
vtk/
├── preprocess_widget.py      # 전처리 위젯
├── postprocess_widget.py     # 후처리 위젯
├── vtk_widget.py             # 기본 위젯 (레거시)
├── vtk_manager.py            # 뷰어 관리 및 카메라 동기화
├── camera/                   # 카메라 컨트롤
│   ├── camera.py
│   └── cad_style.py
├── object/                   # 객체 관리
│   ├── object_manager.py
│   └── object_data.py
├── sources/                  # 데이터 소스
│   ├── mesh_loader.py
│   └── geometry_source.py
├── tool/                     # 도구
│   ├── axes_tool.py
│   ├── ruler_tool.py
│   └── point_probe_tool.py
├── res/                      # 리소스
│   └── icon/                 # 아이콘
└── post/                     # 후처리 실험 코드 (참고용)
```

## 시그널 (Signals)

### PreprocessWidget
- `mesh_loaded(str)`: 메쉬 파일 로드 완료 시
- `selection_changed(dict)`: 객체 선택 변경 시

### PostprocessWidget
- `case_loaded(str)`: OpenFOAM 케이스 로드 완료 시
- `field_changed(str)`: 필드 선택 변경 시

## API 주요 메서드

### PreprocessWidget

```python
# 파일 로딩
load_stl(file_path, solid_split=True)
load_stl_file()  # 파일 다이얼로그

# 도형 추가
add_geometry(geometry_type="cube")  # "cube" 또는 "sphere"

# 뷰 컨트롤
fit_to_scene()
toggle_axes(checked)
toggle_ruler(checked)
toggle_projection(checked)

# 렌더링
render_now()
```

### PostprocessWidget

```python
# 파일 로딩
load_foam(file_path)
load_foam_file()  # 파일 다이얼로그

# 슬라이스 모드
enable_slice_mode(enabled=True)

# 스칼라 바
on_scalar_bar_toggled(checked)

# 뷰 컨트롤
fit_to_scene()

# 렌더링
render_now()
```

## 발견된 버그 수정 사항

1. **object_manager.py**: `set_group`, `set_name`, `set_path` 메서드에서 조건문 수정
   - `if obj is None:` → `if obj is not None:`

## 개선 권장 사항

1. **post 폴더 정리**: 실험 코드들을 통합 또는 제거
2. **주석 처리된 코드 정리**: vtk_widget.py의 QMainWindow 관련 코드
3. **PointProbeTool 옵션화**: 현재 하드코딩되어 있음
4. **테스트 추가**: 단위 테스트 및 통합 테스트
5. **문서화**: 각 클래스 및 메서드에 대한 docstring 보강

## 참고

- 예제 파일: `example_preprocess.py`, `example_postprocess.py`, `example_both.py`
- VTK 공식 문서: https://vtk.org/documentation/
- PySide6 공식 문서: https://doc.qt.io/qtforpython/
