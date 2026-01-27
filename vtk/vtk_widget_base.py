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
from typing import Optional, Union, Dict, List

from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QComboBox
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401 (OpenGL 초기화 필요)
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer
import vtk

# VTK 경고 메시지 비활성화 (non-manifold triangulation 등)
vtk.vtkObject.GlobalWarningDisplayOff()

from nextlib.vtk.camera import Camera
from nextlib.vtk.core import ObjectManager, ObjectAccessor, GroupAccessor
from nextlib.vtk.core.scene_state import SceneState
from nextlib.vtk.tool import AxesTool, RulerTool, PointProbeTool


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

        # 선택적 도구들
        self._optional_tools: Dict[str, object] = {}
        self._optional_tool_actions: Dict[str, QAction] = {}

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
        # 객체 관리자 (카메라보다 먼저 생성 - 더블클릭 선택 지원)
        self.obj_manager = ObjectManager(self.renderer)
        self.obj_manager.selection_changed.connect(self._on_selection_changed)

        # 카메라 (obj_manager 전달하여 더블클릭 선택 지원)
        self.camera = Camera(self)
        self.camera.init(self.obj_manager)

        # Ctrl/Shift 클릭 및 Delete 키 콜백 설정
        self.obj_manager.set_picking_callback(self.interactor)

        # 도구
        self.axes = AxesTool(self)
        self.ruler = RulerTool(self)

        # 상태 조회
        self._state = SceneState(self)

    def _build_toolbar(self):
        """툴바 구성 - 서브클래스에서 오버라이드 가능"""
        # ===== 카메라 뷰 =====
        # Home
        self._add_action("Home", "home.png", self.camera.home)

        # 6방향 뷰
        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            self._add_action(
                name, f"{name.lower()}.png",
                partial(self.camera.set_view, name.lower())
            )

        self.toolbar.addSeparator()

        # ===== 줌 & 피팅 =====
        self._add_action("Zoom In", "zoom_in.png", lambda: self.camera.zoom_in())
        self._add_action("Zoom Out", "zoom_out.png", lambda: self.camera.zoom_out())
        self._add_action("Fit", "fit.png", self.fit_to_scene)

        # 투영 방식 토글
        self._projection_action = self._add_toggle_action(
            "Projection", "perspective.png", "parallel.png",
            self._on_projection_toggled, checked=False
        )

        self.toolbar.addSeparator()

        # ===== 선택 도구 =====
        self._add_action("Select All", "select_all.png", self._on_select_all)
        self._add_action("Deselect", "deselect.png", self._on_clear_selection)

        self.toolbar.addSeparator()

        # ===== 뷰 보조 도구 =====
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

        # ===== 뷰 스타일 =====
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

    def _on_select_all(self):
        """전체 선택"""
        all_ids = [obj.id for obj in self.obj_manager.get_all()]
        self.obj_manager.select_multiple(all_ids)

    def _on_clear_selection(self):
        """선택 해제"""
        self.obj_manager.clear_selection()

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

    # ===== 선택적 도구 관리 =====

    def add_tool(self, tool_name: str, icon_on: str = None, icon_off: str = None) -> bool:
        """선택적 도구를 툴바에 추가

        Args:
            tool_name: 도구 이름 ("point_probe" 등)
            icon_on: 활성화 아이콘 파일명 (선택)
            icon_off: 비활성화 아이콘 파일명 (선택)

        Returns:
            성공 여부

        사용 예시:
            widget.add_tool("point_probe")
            widget.add_tool("point_probe", "probe_on.png", "probe_off.png")
        """
        if tool_name in self._optional_tools:
            return False  # 이미 추가됨

        tool = None

        if tool_name == "point_probe":
            tool = PointProbeTool(self)
            icon_on = icon_on or "probe_on.png"
            icon_off = icon_off or "probe_off.png"
            tooltip = "Point Probe"
        else:
            print(f"[VtkWidgetBase] Unknown tool: {tool_name}")
            return False

        self._optional_tools[tool_name] = tool

        # 툴바에 토글 액션 추가
        action = self._add_toggle_action(
            tooltip, icon_on, icon_off,
            lambda checked, name=tool_name: self._on_optional_tool_toggled(name, checked),
            checked=False
        )
        self._optional_tool_actions[tool_name] = action

        return True

    def remove_tool(self, tool_name: str) -> bool:
        """선택적 도구 제거

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name not in self._optional_tools:
            return False

        tool = self._optional_tools.pop(tool_name)

        # 도구 정리
        if hasattr(tool, 'cleanup'):
            tool.cleanup()
        elif hasattr(tool, 'hide'):
            tool.hide()

        # 툴바에서 액션 제거
        if tool_name in self._optional_tool_actions:
            action = self._optional_tool_actions.pop(tool_name)
            self.toolbar.removeAction(action)

        return True

    def show_tool(self, tool_name: str) -> bool:
        """도구 표시

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name not in self._optional_tools:
            return False

        tool = self._optional_tools[tool_name]
        if hasattr(tool, 'show'):
            tool.show()

        # 툴바 액션 상태 업데이트
        if tool_name in self._optional_tool_actions:
            self._optional_tool_actions[tool_name].setChecked(True)

        return True

    def hide_tool(self, tool_name: str) -> bool:
        """도구 숨김

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name not in self._optional_tools:
            return False

        tool = self._optional_tools[tool_name]
        if hasattr(tool, 'hide'):
            tool.hide()

        # 툴바 액션 상태 업데이트
        if tool_name in self._optional_tool_actions:
            self._optional_tool_actions[tool_name].setChecked(False)

        return True

    def toggle_tool(self, tool_name: str) -> bool:
        """도구 토글

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name not in self._optional_tools:
            return False

        tool = self._optional_tools[tool_name]
        if hasattr(tool, 'toggle'):
            tool.toggle()

            # 툴바 액션 상태 업데이트
            if tool_name in self._optional_tool_actions:
                is_visible = getattr(tool, 'is_visible', False)
                self._optional_tool_actions[tool_name].setChecked(is_visible)

        return True

    def get_tool(self, tool_name: str) -> Optional[object]:
        """도구 객체 반환

        Args:
            tool_name: 도구 이름

        Returns:
            도구 객체 또는 None

        사용 예시:
            probe = widget.get_tool("point_probe")
            if probe:
                probe.center_moved.connect(my_handler)
        """
        return self._optional_tools.get(tool_name)

    def is_tool_visible(self, tool_name: str) -> bool:
        """도구 가시성 확인"""
        tool = self._optional_tools.get(tool_name)
        if tool and hasattr(tool, 'is_visible'):
            return tool.is_visible
        return False

    def has_tool(self, tool_name: str) -> bool:
        """도구 존재 여부 확인"""
        return tool_name in self._optional_tools

    def list_tools(self) -> List[str]:
        """추가된 도구 목록 반환"""
        return list(self._optional_tools.keys())

    def show_tool_button(self, tool_name: str) -> bool:
        """툴바에서 도구 버튼 표시

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name in self._optional_tool_actions:
            self._optional_tool_actions[tool_name].setVisible(True)
            return True
        return False

    def hide_tool_button(self, tool_name: str) -> bool:
        """툴바에서 도구 버튼 숨김 (도구 자체는 유지)

        Args:
            tool_name: 도구 이름

        Returns:
            성공 여부
        """
        if tool_name in self._optional_tool_actions:
            self._optional_tool_actions[tool_name].setVisible(False)
            return True
        return False

    def _on_optional_tool_toggled(self, tool_name: str, checked: bool):
        """선택적 도구 토글 핸들러"""
        if checked:
            self.show_tool(tool_name)
        else:
            self.hide_tool(tool_name)

    # ===== 정리 =====

    def cleanup(self):
        """리소스 정리"""
        try:
            # 선택적 도구 정리
            for tool_name in list(self._optional_tools.keys()):
                self.remove_tool(tool_name)

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
