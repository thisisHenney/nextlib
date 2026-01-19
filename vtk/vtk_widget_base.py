"""
VTK 위젯 베이스 클래스

전처리/후처리 위젯의 공통 기능을 제공:
- 렌더러 및 인터랙터 설정
- 툴바 (카메라 뷰, 축, 눈금자, 투영 방식)
- 객체 관리자
- 카메라 컨트롤
"""
from functools import partial
from pathlib import Path
from typing import Optional, Union

from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QComboBox
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401 (OpenGL 초기화 필요)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer

from nextlib.vtk.camera import Camera
from nextlib.vtk.core import ObjectManager, ObjectAccessor, GroupAccessor
from nextlib.vtk.core.scene_state import SceneState
from nextlib.vtk.tool import AxesTool, RulerTool


# 리소스 경로
RES_DIR = Path(__file__).resolve().parent
ICON_DIR = RES_DIR / "res" / "icon"


class VtkWidgetBase(QWidget):
    """VTK 위젯 베이스 클래스"""

    # 시그널
    selection_changed = Signal(dict)

    def __init__(self, parent: QWidget = None, registry=None):
        """
        Args:
            parent: 부모 위젯
            registry: VtkManager 레지스트리 (카메라 동기화용)
        """
        super().__init__(parent)

        self.registry = registry
        self.camera_sync_lock = False

        # 컴포넌트 초기화
        self.renderer: Optional[vtkRenderer] = None
        self.interactor = None
        self.vtk_widget: Optional[QVTKRenderWindowInteractor] = None
        self.camera: Optional[Camera] = None
        self.obj_manager: Optional[ObjectManager] = None
        self.axes: Optional[AxesTool] = None
        self.ruler: Optional[RulerTool] = None

        # UI 설정
        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._set_background()

        self.interactor.Initialize()

    # ===== 초기화 =====

    def _setup_ui(self):
        """UI 레이아웃 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 툴바
        self.toolbar = QToolBar("VTK Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        layout.addWidget(self.toolbar)

        # VTK 위젯
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget, stretch=1)

    def _setup_vtk(self):
        """VTK 렌더러 및 인터랙터 설정"""
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

    def _setup_tools(self):
        """도구 초기화"""
        # 카메라
        self.camera = Camera(self)
        self.camera.init()

        # 객체 관리자
        self.obj_manager = ObjectManager(self.renderer)
        self.obj_manager.set_picking_callback(self.interactor)
        self.obj_manager.selection_changed.connect(self._on_selection_changed)

        # 도구
        self.axes = AxesTool(self)
        self.ruler = RulerTool(self)

        # 상태 조회
        self._state = SceneState(self)

    def _build_toolbar(self):
        """툴바 구성 - 서브클래스에서 오버라이드 가능"""
        # 축 토글
        self._axes_action = self._add_toggle_action(
            "Axes", "axes_on.png", "axes_off.png",
            self._on_axes_toggled, checked=True
        )

        # 눈금자 토글
        self._ruler_action = self._add_toggle_action(
            "Ruler", "ruler_on.png", "ruler_off.png",
            self._on_ruler_toggled, checked=False
        )

        self.toolbar.addSeparator()

        # 카메라 뷰
        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            self._add_action(
                name, f"{name.lower()}.png",
                partial(self.camera.set_view, name.lower())
            )

        self.toolbar.addSeparator()

        # Fit
        self._add_action("Fit", "fit.png", self.fit_to_scene)

        # 투영 방식 토글
        self._projection_action = self._add_toggle_action(
            "Projection", "perspective.png", "parallel.png",
            self._on_projection_toggled, checked=False
        )

        self.toolbar.addSeparator()

        # 뷰 스타일 콤보박스
        self._view_combo = QComboBox()
        self._view_combo.addItems([
            "wireframe",
            "surface",
            "surface with edge",
            "transparent",
        ])
        self._view_combo.setCurrentText("surface with edge")
        self._view_combo.currentTextChanged.connect(self._on_view_style_changed)
        self.toolbar.addWidget(self._view_combo)

    def _set_background(self):
        """배경색 설정"""
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # 상단
        self.renderer.SetBackground(0.65, 0.65, 0.70)   # 하단
        self.renderer.GradientBackgroundOn()

    # ===== 툴바 헬퍼 =====

    def _make_icon(self, name: str) -> QIcon:
        """아이콘 생성"""
        path = ICON_DIR / name
        if path.exists():
            return QIcon(str(path))
        return QIcon()

    def _add_action(self, text: str, icon_name: str, slot) -> QAction:
        """일반 액션 추가"""
        action = QAction(self._make_icon(icon_name), text, self)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    def _add_toggle_action(
        self, text: str, icon_on: str, icon_off: str,
        slot, checked: bool = False
    ) -> QAction:
        """토글 액션 추가"""
        icon = self._make_icon(icon_on if checked else icon_off)
        action = QAction(icon, text, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    # ===== 툴바 슬롯 =====

    def _on_axes_toggled(self, checked: bool):
        """축 토글"""
        icon_name = "axes_on.png" if checked else "axes_off.png"
        self._axes_action.setIcon(self._make_icon(icon_name))
        if checked:
            self.axes.show()
        else:
            self.axes.hide()

    def _on_ruler_toggled(self, checked: bool):
        """눈금자 토글"""
        icon_name = "ruler_on.png" if checked else "ruler_off.png"
        self._ruler_action.setIcon(self._make_icon(icon_name))
        if checked:
            actors = [obj.actor for obj in self.obj_manager.get_all()]
            self.ruler.show(actors)
        else:
            self.ruler.hide()

    def _on_projection_toggled(self, checked: bool):
        """투영 방식 토글"""
        icon_name = "parallel.png" if checked else "perspective.png"
        self._projection_action.setIcon(self._make_icon(icon_name))
        self.camera.set_parallel_projection(checked)

    def _on_view_style_changed(self, style: str):
        """뷰 스타일 변경"""
        self.obj_manager.all().style(style)

    def _on_selection_changed(self, info: dict):
        """선택 변경 이벤트"""
        self.selection_changed.emit(info)

    # ===== 공개 API =====

    @property
    def state(self) -> SceneState:
        """씬 상태 조회

        사용 예시:
            widget.state.selected_count      # 선택된 객체 수
            widget.state.selected_names      # 선택된 이름 리스트
            widget.state.object_count        # 전체 객체 수
            widget.state.view_style          # 현재 뷰 스타일
            widget.state.bounds              # 씬 바운딩 박스
            widget.state.summary()           # 전체 상태 딕셔너리
        """
        return self._state

    def object(self, identifier: Union[int, str]) -> Optional[ObjectAccessor]:
        """객체 접근 (체이닝)

        사용 예시:
            widget.object(0).hide()
            widget.object("cube").color(255, 0, 0)
        """
        return self.obj_manager.object(identifier)

    def group(self, group_name: str) -> GroupAccessor:
        """그룹 접근 (체이닝)

        사용 예시:
            widget.group("walls").show().style("wireframe")
        """
        return self.obj_manager.group(group_name)

    def all_objects(self) -> GroupAccessor:
        """모든 객체 접근 (체이닝)"""
        return self.obj_manager.all()

    def selected_objects(self) -> GroupAccessor:
        """선택된 객체 접근 (체이닝)"""
        return self.obj_manager.selected()

    def fit_to_scene(self):
        """씬에 맞춰 카메라 리셋"""
        self.camera.fit()

    def render(self):
        """즉시 렌더링"""
        self.vtk_widget.GetRenderWindow().Render()

    def set_background(self, color1: tuple, color2: tuple = None):
        """배경색 설정

        Args:
            color1: RGB (0-1) 또는 (0-255)
            color2: 그라데이션용 두 번째 색상 (선택)
        """
        # 0-255 범위를 0-1로 변환
        if max(color1) > 1:
            color1 = tuple(c / 255.0 for c in color1)

        if color2:
            if max(color2) > 1:
                color2 = tuple(c / 255.0 for c in color2)
            self.renderer.SetBackground(color1[0], color1[1], color1[2])
            self.renderer.SetBackground2(color2[0], color2[1], color2[2])
            self.renderer.GradientBackgroundOn()
        else:
            self.renderer.SetBackground(color1[0], color1[1], color1[2])
            self.renderer.GradientBackgroundOff()

        self.render()

    # ===== 정리 =====

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.interactor:
                self.interactor.Disable()
                self.interactor.TerminateApp()
                self.interactor = None

            if self.renderer:
                self.renderer.RemoveAllViewProps()
                self.renderer = None

            if self.vtk_widget:
                rw = self.vtk_widget.GetRenderWindow()
                if rw:
                    rw.Finalize()
                    rw.SetWindowInfo("")
                self.vtk_widget = None

        except Exception as e:
            print(f"[VtkWidgetBase] Cleanup error: {e}")

    def closeEvent(self, event):
        """닫기 이벤트"""
        self.cleanup()
        super().closeEvent(event)
