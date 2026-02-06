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

from PySide6.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QToolBar, QComboBox, QFrame, QProgressBar, QLabel, QHBoxLayout, QSplitter
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal, Qt

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
from nextlib.vtk.scene_tree_widget import SceneTreeWidget


# 리소스 경로
RES_DIR = Path(__file__).resolve().parent
ICON_DIR = RES_DIR / "res" / "icon"


class VtkWidgetBase(QMainWindow):
    """VTK 위젯 베이스 클래스 (QMainWindow 기반 - QToolBar 플로팅/도킹 지원)"""

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

        # 바닥 평면 (ground plane)
        self._ground_plane_actor = None

        # 씬 트리 (기본 비활성화)
        self._scene_tree: Optional[SceneTreeWidget] = None
        self._scene_tree_enabled = False

        # UI 설정
        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._set_background()

        self.interactor.Initialize()

    # ===== 초기화 =====

    def _setup_ui(self):
        """UI 레이아웃 설정 (QMainWindow 기반)"""
        # 툴바 (QMainWindow 툴바 영역에 추가 - 플로팅/도킹 지원)
        self.toolbar = QToolBar("VTK Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)

        # 메인 스플리터 (씬 트리 + VTK 프레임)
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        # 씬 트리 위젯 (초기 숨김)
        self._scene_tree = SceneTreeWidget(self._main_splitter)
        self._scene_tree.hide()

        # VTK 위젯을 감싸는 프레임 (Styled Panel)
        self.vtk_frame = QFrame(self._main_splitter)
        self.vtk_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.vtk_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.vtk_frame.setLineWidth(1)

        # 프레임 내부 레이아웃
        frame_layout = QVBoxLayout(self.vtk_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        # VTK 위젯
        self.vtk_widget = QVTKRenderWindowInteractor(self.vtk_frame)
        frame_layout.addWidget(self.vtk_widget, stretch=1)

        # 프로그레스바 (하단에 배치, 기본 숨김)
        self._progress_container = QFrame(self.vtk_frame)
        self._progress_container.setFixedHeight(24)
        progress_layout = QHBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(4, 2, 4, 2)
        progress_layout.setSpacing(8)

        self._progress_label = QLabel("Loading...")
        self._progress_label.setFixedWidth(100)
        progress_layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 3px;
                background-color: #e8e8ec;
                text-align: center;
                color: #333;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:0.5 #22c55e,
                    stop:1 #f97316
                );
                border-radius: 2px;
            }
        """)
        progress_layout.addWidget(self._progress_bar, stretch=1)

        frame_layout.addWidget(self._progress_container)
        self._progress_container.hide()

        # 스플리터 설정 (씬 트리: 200px, VTK: 나머지)
        self._main_splitter.setSizes([0, 1])  # 씬 트리 숨김 상태
        self._main_splitter.setStretchFactor(0, 0)  # 씬 트리: 고정
        self._main_splitter.setStretchFactor(1, 1)  # VTK: 확장

        self.setCentralWidget(self._main_splitter)

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

        # 씬 트리에 ObjectManager 연결
        if self._scene_tree:
            self._scene_tree.set_object_manager(self.obj_manager)

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
        home = self._add_action("\u2302", "", self.camera.home)
        home.setToolTip("Home")

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

        self.toolbar.addSeparator()

        # ===== 가시성 토글 버튼 =====
        self._geom_visible_action = QAction("\U0001F4D0", self)  # 📐 (Geometry)
        self._geom_visible_action.setToolTip("Show Geometry")
        self._geom_visible_action.setCheckable(True)
        self._geom_visible_action.setChecked(True)
        self._geom_visible_action.triggered.connect(self._on_geometry_visibility_toggled)
        self.toolbar.addAction(self._geom_visible_action)

        self._mesh_visible_action = QAction("\U0001F5A7", self)  # 🖧 (Mesh)
        self._mesh_visible_action.setToolTip("Show Mesh")
        self._mesh_visible_action.setCheckable(True)
        self._mesh_visible_action.setChecked(False)
        self._mesh_visible_action.triggered.connect(self._on_mesh_visibility_toggled)
        self.toolbar.addAction(self._mesh_visible_action)

        self._both_visible_action = QAction("\u229E", self)  # ⊞ (Both)
        self._both_visible_action.setToolTip("Show Both (Geometry + Mesh)")
        self._both_visible_action.setCheckable(True)
        self._both_visible_action.setChecked(False)
        self._both_visible_action.triggered.connect(self._on_both_visibility_toggled)
        self.toolbar.addAction(self._both_visible_action)

        # 가시성 상태 추적
        self._visibility_mode = "geometry"  # "geometry", "mesh", "both"

        self.toolbar.addSeparator()

        # ===== 씬 트리 토글 (기본 숨김) =====
        self._scene_tree_action = QAction("\u2630", self)  # ☰ (햄버거 메뉴 아이콘)
        self._scene_tree_action.setToolTip("Scene Tree")
        self._scene_tree_action.setCheckable(True)
        self._scene_tree_action.setChecked(False)
        self._scene_tree_action.triggered.connect(self._on_scene_tree_toggled)
        self.toolbar.addAction(self._scene_tree_action)
        self._scene_tree_action.setVisible(False)  # 기본 숨김

        # 클립 관련 변수 초기화 (UI 컨트롤은 외부 패널에서 제공)
        self._clip_plane = None
        self._clip_actors = {}  # {obj_id: clipped_actor}
        self._original_actors_visibility = {}  # {obj_id: visibility}
        self._clip_bounds = None  # 전체 바운딩 박스
        self._clip_normal = None  # 현재 클립 방향
        self._clip_mode = "off"  # 현재 클립 모드
        self._clip_position = 50  # 현재 클립 위치 (0-100)
        self._clip_preview = False  # 미리보기 모드
        self._clip_preview_actor = None  # 미리보기 평면 액터
        self._current_view_style = "surface with edge"  # 현재 뷰 스타일

    def _set_background(self):
        """배경색 설정 - Fusion 360 스타일 화이트 그라데이션"""
        self.renderer.SetBackground(0.75, 0.78, 0.82)   # 하단 (미디엄 그레이)
        self.renderer.SetBackground2(0.98, 0.98, 1.0)   # 상단 (거의 흰색)
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

    def _on_geometry_visibility_toggled(self, checked: bool):
        """Geometry 가시성 토글 (사용자가 버튼 클릭)"""
        if checked:
            self.set_visibility_mode("geometry", apply_visibility=True)
        else:
            # 체크 해제 시 다시 체크 (최소 하나는 선택)
            self._geom_visible_action.setChecked(True)

    def _on_mesh_visibility_toggled(self, checked: bool):
        """Mesh 가시성 토글 (사용자가 버튼 클릭)"""
        if checked:
            self.set_visibility_mode("mesh", apply_visibility=True)
        else:
            # 체크 해제 시 다시 체크 (최소 하나는 선택)
            self._mesh_visible_action.setChecked(True)

    def _on_both_visibility_toggled(self, checked: bool):
        """Both (Geometry + Mesh) 가시성 토글 (사용자가 버튼 클릭)"""
        if checked:
            self.set_visibility_mode("both", apply_visibility=True)
        else:
            # 체크 해제 시 다시 체크 (최소 하나는 선택)
            self._both_visible_action.setChecked(True)

    def _apply_visibility_mode(self, mode: str):
        """가시성 모드 실제 적용 (내부용)

        Args:
            mode: "geometry", "mesh", "both" 중 하나
        """
        # 객체 가시성 업데이트
        for obj in self.obj_manager.get_all():
            group = getattr(obj, 'group', 'default')

            if mode == "geometry":
                obj.actor.SetVisibility(group == "geometry")
            elif mode == "mesh":
                obj.actor.SetVisibility(group == "mesh")
            elif mode == "both":
                # Both: geometry는 반투명, mesh는 불투명
                obj.actor.SetVisibility(True)
                if group == "geometry":
                    obj.actor.GetProperty().SetOpacity(0.3)
                else:
                    obj.actor.GetProperty().SetOpacity(1.0)

        # Both가 아닐 때 opacity 복원
        if mode != "both":
            for obj in self.obj_manager.get_all():
                obj.actor.GetProperty().SetOpacity(1.0)

        self.render()

    def get_visibility_mode(self) -> str:
        """현재 가시성 모드 반환"""
        return self._visibility_mode

    def set_visibility_mode(self, mode: str, apply_visibility: bool = False):
        """외부에서 가시성 모드 설정

        Args:
            mode: "geometry", "mesh", "both" 중 하나
            apply_visibility: True면 실제 가시성도 변경, False면 버튼 상태만 동기화
        """
        if mode not in ("geometry", "mesh", "both"):
            return

        self._visibility_mode = mode

        # 버튼 상태 동기화 (라디오 버튼처럼 동작)
        self._geom_visible_action.setChecked(mode == "geometry")
        self._mesh_visible_action.setChecked(mode == "mesh")
        self._both_visible_action.setChecked(mode == "both")

        # apply_visibility=True일 때만 실제 가시성 변경
        if apply_visibility:
            self._apply_visibility_mode(mode)

    def _on_view_style_changed(self, style: str):
        """뷰 스타일 변경"""
        self._current_view_style = style
        self.obj_manager.all().style(style)

        # 클립 액터에도 스타일 적용
        self._apply_style_to_clip_actors(style)
        self.render()

    def _on_scene_tree_toggled(self, checked: bool):
        """씬 트리 토글"""
        if checked:
            self.enable_scene_tree()
        else:
            self.disable_scene_tree()

    def _on_clip_mode_changed(self, mode: str):
        """클립 모드 변경 (내부 처리)"""
        # 기존 클립 및 미리보기 제거
        self._clear_clip()
        self._remove_preview_plane()
        # 원본 객체 가시성 복원 (클립 해제 또는 미리보기 모드로 전환 시)
        self._restore_original_visibility()

        if mode == "off":
            self._clip_bounds = None
            self._clip_normal = None
            self._clip_mode = "off"
            self.render()
            return

        # 클립 방향 결정
        if mode == "x":
            normal = (1, 0, 0)
        elif mode == "y":
            normal = (0, 1, 0)
        elif mode == "z":
            normal = (0, 0, 1)
        else:
            return

        self._clip_normal = normal
        self._clip_mode = mode

        # 전체 바운딩 박스 계산
        self._calculate_clip_bounds()

        # 미리보기 모드면 평면 표시, 아니면 실제 클립 적용
        if self._clip_preview:
            self._show_preview_plane()
        else:
            self._apply_clip()
        self.render()

    def _calculate_clip_bounds(self):
        """보이는 객체의 바운딩 박스 계산"""
        all_objs = self.obj_manager.get_all()
        if not all_objs:
            self._clip_bounds = None
            return

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")

        for obj in all_objs:
            try:
                # 보이지 않는 객체는 건너뛰기
                if not obj.actor.GetVisibility():
                    continue

                bounds = obj.actor.GetBounds()
                min_x = min(min_x, bounds[0])
                max_x = max(max_x, bounds[1])
                min_y = min(min_y, bounds[2])
                max_y = max(max_y, bounds[3])
                min_z = min(min_z, bounds[4])
                max_z = max(max_z, bounds[5])
            except:
                continue

        # 유효한 bounds 확인
        if min_x == float("inf"):
            self._clip_bounds = None
            return

        self._clip_bounds = (min_x, max_x, min_y, max_y, min_z, max_z)

    def _on_clip_position_changed(self, value: int):
        """클립 위치 변경 (내부 처리)"""
        self._clip_position = value

        if self._clip_bounds is None or self._clip_normal is None:
            return

        # 미리보기 모드면 평면만 업데이트, 아니면 실제 클립
        if self._clip_preview:
            # 기존 클립 제거 및 원본 복원 (실제 클립에서 미리보기로 전환된 경우)
            if self._clip_actors:
                self._clear_clip()
                self._restore_original_visibility()
            self._remove_preview_plane()
            self._show_preview_plane()
        else:
            # 기존 클립 액터 제거
            self._clear_clip()
            # 새 위치에서 클립 적용
            self._apply_clip()
        self.render()

    def _apply_clip(self):
        """보이는 객체에만 클립 적용 (반쪽 잘라서 내부 표시)"""
        from vtkmodules.vtkCommonDataModel import vtkPlane
        from vtkmodules.vtkFiltersCore import vtkClipPolyData
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        if self._clip_bounds is None or self._clip_normal is None:
            return

        all_objs = self.obj_manager.get_all()
        if not all_objs:
            return

        # 슬라이더 값에 따른 클립 위치 계산 (0-100 → bounds 범위)
        slider_val = self._clip_position / 100.0
        min_x, max_x, min_y, max_y, min_z, max_z = self._clip_bounds

        # 클립 방향에 따라 위치 결정
        if self._clip_normal == (1, 0, 0):  # X축
            clip_pos = min_x + (max_x - min_x) * slider_val
            origin = (clip_pos, (min_y + max_y) / 2, (min_z + max_z) / 2)
        elif self._clip_normal == (0, 1, 0):  # Y축
            clip_pos = min_y + (max_y - min_y) * slider_val
            origin = ((min_x + max_x) / 2, clip_pos, (min_z + max_z) / 2)
        else:  # Z축
            clip_pos = min_z + (max_z - min_z) * slider_val
            origin = ((min_x + max_x) / 2, (min_y + max_y) / 2, clip_pos)

        self._clip_plane = vtkPlane()
        self._clip_plane.SetOrigin(origin)
        self._clip_plane.SetNormal(self._clip_normal)

        # 각 객체에 클립 적용 (현재 보이는 객체만)
        for obj in all_objs:
            try:
                # 현재 가시성 확인 (탭 전환에 따라 변경된 상태)
                current_visibility = obj.actor.GetVisibility()

                # 현재 보이지 않는 객체는 건너뛰기 (기존 클립 액터 제거)
                if not current_visibility:
                    # 이미 클립 액터가 있으면 제거
                    if obj.id in self._clip_actors:
                        try:
                            self.renderer.RemoveActor(self._clip_actors[obj.id])
                        except:
                            pass
                        del self._clip_actors[obj.id]
                    continue

                # 원본 가시성 저장 (현재 보이는 상태)
                self._original_actors_visibility[obj.id] = True

                # 원본 숨기기
                obj.actor.SetVisibility(False)

                # 클립 액터 생성
                mapper = obj.actor.GetMapper()
                if mapper is None:
                    continue

                input_data = mapper.GetInput()
                if input_data is None:
                    continue

                # ClipPolyData로 반쪽 자르기
                clipper = vtkClipPolyData()
                clipper.SetInputData(input_data)
                clipper.SetClipFunction(self._clip_plane)
                clipper.Update()

                clip_mapper = vtkPolyDataMapper()
                clip_mapper.SetInputConnection(clipper.GetOutputPort())

                clip_actor = vtkActor()
                clip_actor.SetMapper(clip_mapper)

                # 원본 객체의 변환 정보 복사
                clip_actor.SetPosition(obj.actor.GetPosition())
                clip_actor.SetOrientation(obj.actor.GetOrientation())
                clip_actor.SetScale(obj.actor.GetScale())
                clip_actor.SetOrigin(obj.actor.GetOrigin())
                if obj.actor.GetUserMatrix():
                    clip_actor.SetUserMatrix(obj.actor.GetUserMatrix())

                # 클립된 객체 스타일 설정 (원본 색상 + 현재 뷰 스타일)
                orig_prop = obj.actor.GetProperty()
                prop = clip_actor.GetProperty()
                prop.SetColor(orig_prop.GetColor())

                # 현재 뷰 스타일 적용
                style = self._current_view_style
                if style == "wireframe":
                    prop.SetRepresentationToWireframe()
                    prop.EdgeVisibilityOff()
                elif style == "surface":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOff()
                elif style == "surface with edge":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOn()
                    prop.SetEdgeColor(0.3, 0.3, 0.35)  # Fusion 360 스타일
                elif style == "transparent":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOff()
                    prop.SetOpacity(0.5)

                self.renderer.AddActor(clip_actor)
                self._clip_actors[obj.id] = clip_actor

            except Exception:
                continue

    def _clear_clip(self):
        """클립 액터 제거"""
        for obj_id, actor in self._clip_actors.items():
            try:
                self.renderer.RemoveActor(actor)
            except:
                pass
        self._clip_actors.clear()
        self._clip_plane = None

    def _show_preview_plane(self):
        """클립 위치를 보여주는 미리보기 평면 표시"""
        from vtkmodules.vtkFiltersSources import vtkPlaneSource
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        if self._clip_bounds is None or self._clip_normal is None:
            return

        # 기존 미리보기 제거
        self._remove_preview_plane()

        min_x, max_x, min_y, max_y, min_z, max_z = self._clip_bounds
        slider_val = self._clip_position / 100.0

        # 평면 크기를 10% 확장
        margin = 0.1
        size_x = (max_x - min_x) * margin
        size_y = (max_y - min_y) * margin
        size_z = (max_z - min_z) * margin

        # 확장된 bounds
        ext_min_x = min_x - size_x
        ext_max_x = max_x + size_x
        ext_min_y = min_y - size_y
        ext_max_y = max_y + size_y
        ext_min_z = min_z - size_z
        ext_max_z = max_z + size_z

        # 클립 방향에 따른 평면 설정
        plane_source = vtkPlaneSource()

        if self._clip_normal == (1, 0, 0):  # X축
            clip_pos = min_x + (max_x - min_x) * slider_val
            plane_source.SetOrigin(clip_pos, ext_min_y, ext_min_z)
            plane_source.SetPoint1(clip_pos, ext_max_y, ext_min_z)
            plane_source.SetPoint2(clip_pos, ext_min_y, ext_max_z)
        elif self._clip_normal == (0, 1, 0):  # Y축
            clip_pos = min_y + (max_y - min_y) * slider_val
            plane_source.SetOrigin(ext_min_x, clip_pos, ext_min_z)
            plane_source.SetPoint1(ext_max_x, clip_pos, ext_min_z)
            plane_source.SetPoint2(ext_min_x, clip_pos, ext_max_z)
        else:  # Z축
            clip_pos = min_z + (max_z - min_z) * slider_val
            plane_source.SetOrigin(ext_min_x, ext_min_y, clip_pos)
            plane_source.SetPoint1(ext_max_x, ext_min_y, clip_pos)
            plane_source.SetPoint2(ext_min_x, ext_max_y, clip_pos)

        plane_source.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(plane_source.GetOutputPort())

        self._clip_preview_actor = vtkActor()
        self._clip_preview_actor.SetMapper(mapper)

        # 반투명 빨간색 평면 스타일
        prop = self._clip_preview_actor.GetProperty()
        prop.SetColor(1.0, 0.3, 0.3)  # 빨간색
        prop.SetOpacity(0.4)
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(1.0, 0.0, 0.0)  # 빨간 엣지
        prop.SetLineWidth(2.0)

        self.renderer.AddActor(self._clip_preview_actor)

    def _remove_preview_plane(self):
        """미리보기 평면 제거"""
        if self._clip_preview_actor:
            try:
                self.renderer.RemoveActor(self._clip_preview_actor)
            except:
                pass
            self._clip_preview_actor = None

    def _restore_original_visibility(self):
        """원본 객체 가시성 복원"""
        for obj_id, visibility in self._original_actors_visibility.items():
            obj = self.obj_manager.get(obj_id)
            if obj:
                obj.actor.SetVisibility(visibility)
        self._original_actors_visibility.clear()

    def _apply_style_to_clip_actors(self, style: str):
        """클립 액터에 뷰 스타일 적용"""
        if not self._clip_actors:
            return

        for actor in self._clip_actors.values():
            prop = actor.GetProperty()

            if style == "wireframe":
                prop.SetRepresentationToWireframe()
                prop.EdgeVisibilityOff()
            elif style == "surface":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOff()
            elif style == "surface with edge":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOn()
                prop.SetEdgeColor(0.1, 0.1, 0.4)
            elif style == "transparent":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOff()
                prop.SetOpacity(0.5)

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

    # ===== 클립 공개 API =====

    def set_clip_mode(self, mode: str, preview: bool = False):
        """클립 모드 설정

        Args:
            mode: "off", "x", "y", "z" 중 하나
            preview: True면 미리보기 평면만 표시, False면 실제 클립

        사용 예시:
            widget.set_clip_mode("x")  # X축 기준 클립
            widget.set_clip_mode("x", preview=True)  # X축 미리보기 평면
            widget.set_clip_mode("off")  # 클립 해제
        """
        mode = mode.lower()
        if mode not in ("off", "x", "y", "z"):
            return
        self._clip_preview = preview
        self._on_clip_mode_changed(mode)

    def set_clip_position(self, value: int, preview: bool = None):
        """클립 위치 설정

        Args:
            value: 0-100 사이 값 (0=최소, 50=중앙, 100=최대)
            preview: True면 미리보기만 (None이면 현재 상태 유지)

        사용 예시:
            widget.set_clip_position(50)  # 중앙에서 클립
            widget.set_clip_position(25, preview=True)  # 25% 위치 미리보기
        """
        value = max(0, min(100, value))
        if preview is not None:
            self._clip_preview = preview
        self._on_clip_position_changed(value)

    def apply_clip(self):
        """미리보기 상태에서 실제 클립 적용"""
        if self._clip_mode == "off":
            return

        # 미리보기 평면 제거
        self._remove_preview_plane()

        # 실제 클립 적용
        self._clip_preview = False
        self._apply_clip()
        self.render()

    def reset_clip(self):
        """클립을 원래 상태로 복원 (미리보기 평면은 유지)"""
        if self._clip_mode == "off":
            return

        # 적용된 클립 제거
        self._clear_clip()

        # 원본 가시성 복원
        self._restore_original_visibility()

        # 미리보기 모드로 전환하고 평면 다시 표시
        self._clip_preview = True
        self._show_preview_plane()
        self.render()

    def get_clip_mode(self) -> str:
        """현재 클립 모드 반환

        Returns:
            "off", "x", "y", "z" 중 하나
        """
        return self._clip_mode

    def get_clip_position(self) -> int:
        """현재 클립 위치 반환

        Returns:
            0-100 사이 값
        """
        return self._clip_position

    def is_clip_preview(self) -> bool:
        """현재 미리보기 모드 여부 반환"""
        return self._clip_preview

    def sync_clip_visibility(self):
        """클립 액터 가시성을 원본 객체 가시성과 동기화

        탭 전환 등으로 객체 가시성이 변경된 경우 호출하여
        클립 액터의 가시성도 함께 업데이트합니다.
        """
        if not self._clip_actors:
            return

        for obj_id, clip_actor in list(self._clip_actors.items()):
            obj = self.obj_manager.get(obj_id)
            if obj:
                # 원본 객체가 숨겨져 있으면 클립 액터도 숨김
                # (클립 적용 시 원본은 이미 숨겨진 상태이므로 저장된 가시성 확인)
                if obj_id in self._original_actors_visibility:
                    # 원본이 원래 보였던 객체인지 확인
                    # 현재 원본이 SetVisibility(False)로 숨겨진 상태이므로
                    # 해당 객체의 그룹이나 현재 탭 컨텍스트로 판단
                    pass
                else:
                    # 원본 가시성 정보가 없으면 클립 액터 제거
                    try:
                        self.renderer.RemoveActor(clip_actor)
                    except:
                        pass
                    del self._clip_actors[obj_id]
        self.render()

    def hide_clip_actors_for_group(self, group_name: str):
        """특정 그룹의 클립 액터 숨기기

        Args:
            group_name: 숨길 그룹 이름 (예: "geometry")
        """
        if not self._clip_actors:
            return

        for obj_id, clip_actor in list(self._clip_actors.items()):
            obj = self.obj_manager.get(obj_id)
            if obj and hasattr(obj, 'group') and obj.group == group_name:
                clip_actor.SetVisibility(False)
        self.render()

    def show_clip_actors_for_group(self, group_name: str):
        """특정 그룹의 클립 액터 보이기

        Args:
            group_name: 보일 그룹 이름 (예: "geometry")
        """
        if not self._clip_actors:
            return

        for obj_id, clip_actor in list(self._clip_actors.items()):
            obj = self.obj_manager.get(obj_id)
            if obj and hasattr(obj, 'group') and obj.group == group_name:
                clip_actor.SetVisibility(True)
        self.render()

    # ===== 바닥 평면 (Ground Plane) =====

    def show_ground_plane(self, scale: float = 1.4, offset_ratio: float = 0.05):
        """객체 아래에 반투명 X-Y 바닥 평면 표시

        Args:
            scale: 평면 크기 배율 (기본 1.4 = 바운딩 박스의 1.4배)
            offset_ratio: Z 아래 오프셋 비율 (기본 0.05 = 높이의 5% 아래)

        사용 예시:
            widget.show_ground_plane()
            widget.show_ground_plane(scale=1.5, offset_ratio=0.1)
        """
        from vtkmodules.vtkFiltersSources import vtkPlaneSource
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        # 기존 바닥 평면 제거
        self.hide_ground_plane()

        # 전체 바운딩 박스 계산
        all_objs = self.obj_manager.get_all()
        if not all_objs:
            return

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")

        for obj in all_objs:
            try:
                if not obj.actor.GetVisibility():
                    continue
                bounds = obj.actor.GetBounds()
                min_x = min(min_x, bounds[0])
                max_x = max(max_x, bounds[1])
                min_y = min(min_y, bounds[2])
                max_y = max(max_y, bounds[3])
                min_z = min(min_z, bounds[4])
                max_z = max(max_z, bounds[5])
            except:
                continue

        if min_x == float("inf"):
            return

        # 바운딩 박스 크기
        size_x = max_x - min_x
        size_y = max_y - min_y
        size_z = max_z - min_z

        # 중심점
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        # scale 배율로 평면 크기 확장
        half_width = (size_x * scale) / 2
        half_height = (size_y * scale) / 2

        # Z 위치: 바운딩 박스 아래 (offset_ratio만큼 아래)
        plane_z = min_z - (size_z * offset_ratio)

        # 평면 생성
        plane_source = vtkPlaneSource()
        plane_source.SetOrigin(center_x - half_width, center_y - half_height, plane_z)
        plane_source.SetPoint1(center_x + half_width, center_y - half_height, plane_z)
        plane_source.SetPoint2(center_x - half_width, center_y + half_height, plane_z)
        plane_source.SetXResolution(10)
        plane_source.SetYResolution(10)
        plane_source.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(plane_source.GetOutputPort())

        self._ground_plane_actor = vtkActor()
        self._ground_plane_actor.SetMapper(mapper)

        # 반투명 스타일 설정 - Fusion 360 스타일
        prop = self._ground_plane_actor.GetProperty()
        prop.SetColor(0.85, 0.85, 0.88)  # 라이트 그레이
        prop.SetOpacity(0.5)  # 반투명
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(0.7, 0.7, 0.75)  # 미디엄 그레이 격자선
        prop.SetLineWidth(1.0)

        self.renderer.AddActor(self._ground_plane_actor)

        self.render()

    def hide_ground_plane(self):
        """바닥 평면 숨기기"""
        if self._ground_plane_actor:
            try:
                self.renderer.RemoveActor(self._ground_plane_actor)
            except:
                pass
            self._ground_plane_actor = None
            self.render()

    def update_ground_plane(self, scale: float = 1.4, offset_ratio: float = 0.05):
        """바닥 평면 업데이트 (객체 변경 후 호출)

        Args:
            scale: 평면 크기 배율
            offset_ratio: Z 아래 오프셋 비율
        """
        if self._ground_plane_actor:
            self.show_ground_plane(scale, offset_ratio)

    def is_ground_plane_visible(self) -> bool:
        """바닥 평면 가시성 확인"""
        return self._ground_plane_actor is not None

    # ===== 프로그레스바 =====

    def show_progress(self, label: str = "Loading...", value: int = 0, maximum: int = 100):
        """프로그레스바 표시

        Args:
            label: 프로그레스바 왼쪽에 표시할 텍스트
            value: 현재 값 (0~maximum)
            maximum: 최대값
        """
        self._progress_label.setText(label)
        self._progress_bar.setMaximum(maximum)
        self._progress_bar.setValue(value)
        self._progress_container.show()

    def update_progress(self, value: int, label: str = None):
        """프로그레스바 값 업데이트

        Args:
            value: 현재 값
            label: 레이블 텍스트 (None이면 변경 안 함)
        """
        self._progress_bar.setValue(value)
        if label is not None:
            self._progress_label.setText(label)

    def hide_progress(self):
        """프로그레스바 숨기기"""
        self._progress_container.hide()
        self._progress_bar.setValue(0)

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

    # ===== 씬 트리 =====

    def enable_scene_tree(self):
        """씬 트리 패널 활성화

        VTK 위젯 왼쪽에 CAD 스타일의 객체 트리를 표시합니다.
        사용자가 직접 객체 가시성을 제어할 수 있습니다.

        사용 예시:
            widget.enable_scene_tree()
        """
        if self._scene_tree_enabled:
            return

        self._scene_tree_enabled = True

        # 툴바 버튼 상태 동기화
        if hasattr(self, '_scene_tree_action'):
            self._scene_tree_action.setChecked(True)

        if self._scene_tree:
            self._scene_tree.show()
            self._scene_tree.refresh()
            # 스플리터 크기 조정 (씬 트리: 200px)
            self._main_splitter.setSizes([200, self.width() - 200])

    def disable_scene_tree(self):
        """씬 트리 패널 비활성화

        사용 예시:
            widget.disable_scene_tree()
        """
        if not self._scene_tree_enabled:
            return

        self._scene_tree_enabled = False

        # 툴바 버튼 상태 동기화
        if hasattr(self, '_scene_tree_action'):
            self._scene_tree_action.setChecked(False)

        if self._scene_tree:
            self._scene_tree.hide()
            # 스플리터 크기 조정 (씬 트리: 0px)
            self._main_splitter.setSizes([0, self.width()])

    def toggle_scene_tree(self):
        """씬 트리 패널 토글

        사용 예시:
            widget.toggle_scene_tree()
        """
        if self._scene_tree_enabled:
            self.disable_scene_tree()
        else:
            self.enable_scene_tree()

    def is_scene_tree_enabled(self) -> bool:
        """씬 트리 활성화 여부 반환"""
        return self._scene_tree_enabled

    @property
    def scene_tree(self) -> Optional[SceneTreeWidget]:
        """씬 트리 위젯 반환

        사용 예시:
            tree = widget.scene_tree
            if tree:
                tree.set_group_visible("geometry", False)
                tree.visibility_changed.connect(my_handler)
        """
        return self._scene_tree

    def refresh_scene_tree(self):
        """씬 트리 새로고침

        ObjectManager와 씬 트리를 동기화합니다.

        사용 예시:
            widget.refresh_scene_tree()
        """
        if self._scene_tree:
            self._scene_tree.refresh()

    # ===== 정리 =====

    def cleanup(self):
        """리소스 정리"""
        try:
            # 클립 정리
            self._clear_clip()
            self._restore_original_visibility()

            # 바닥 평면 정리
            self.hide_ground_plane()

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
