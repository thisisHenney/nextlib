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
from PySide6.QtCore import Signal, Qt, QEvent

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer
import vtk

vtk.vtkObject.GlobalWarningDisplayOff()

from nextlib.vtk.camera import Camera
from nextlib.vtk.camera.cad_style import CADInteractorStyle
from nextlib.vtk.core import ObjectManager, ObjectAccessor, GroupAccessor
from nextlib.vtk.core.scene_state import SceneState
from nextlib.vtk.tool import AxesTool, RulerTool, PointProbeTool
from nextlib.vtk.scene_tree_widget import SceneTreeWidget


RES_DIR = Path(__file__).resolve().parent
ICON_DIR = RES_DIR / "res" / "icon"


class VtkWidgetBase(QMainWindow):
    """VTK 위젯 베이스 클래스 (QMainWindow 기반 - QToolBar 플로팅/도킹 지원)"""

    selection_changed = Signal(dict)
    escape_pressed = Signal()

    def __init__(self, parent: QWidget = None, registry=None):
        """
        Args:
            parent: 부모 위젯
            registry: VtkManager 레지스트리 (카메라 동기화용)
        """
        super().__init__(parent)

        self.registry = registry
        self.camera_sync_lock = False

        self.renderer: Optional[vtkRenderer] = None
        self.interactor = None
        self.vtk_widget: Optional[QVTKRenderWindowInteractor] = None
        self.camera: Optional[Camera] = None
        self.obj_manager: Optional[ObjectManager] = None
        self.axes: Optional[AxesTool] = None
        self.ruler: Optional[RulerTool] = None

        self._optional_tools: Dict[str, object] = {}
        self._optional_tool_actions: Dict[str, QAction] = {}

        self._ground_plane_actor = None

        self._scene_tree: Optional[SceneTreeWidget] = None
        self._scene_tree_enabled = False

        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._set_background()

        self.interactor.Initialize()

        self.vtk_widget.installEventFilter(self)

        self.init_default_scene()


    def _setup_ui(self):
        """UI 레이아웃 설정 (QMainWindow 기반)"""
        self.toolbar = QToolBar("VTK Toolbar", self)
        self.toolbar.setFloatable(False)
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self._main_splitter = QSplitter(Qt.Orientation.Horizontal, self)

        self._scene_tree = SceneTreeWidget(self._main_splitter)
        self._scene_tree.hide()

        self.vtk_frame = QFrame(self._main_splitter)
        self.vtk_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.vtk_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.vtk_frame.setLineWidth(1)

        frame_layout = QVBoxLayout(self.vtk_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        self.vtk_widget = QVTKRenderWindowInteractor(self.vtk_frame)
        frame_layout.addWidget(self.vtk_widget, stretch=1)

        self._progress_container = QFrame(self.vtk_frame)
        self._progress_container.setFixedHeight(24)
        progress_layout = QHBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(4, 2, 4, 2)
        progress_layout.setSpacing(8)

        self._progress_label = QLabel("Loading...")
        self._progress_label.setStyleSheet("font-size: 10pt;")
        self._progress_label.setFixedWidth(160)
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

        self._main_splitter.setSizes([0, 1])
        self._main_splitter.setStretchFactor(0, 0)
        self._main_splitter.setStretchFactor(1, 1)

        self.setCentralWidget(self._main_splitter)

    def _setup_vtk(self):
        """VTK 렌더러 및 인터랙터 설정"""
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

    def _setup_tools(self):
        """도구 초기화"""
        self.obj_manager = ObjectManager(self.renderer)
        self.obj_manager.selection_changed.connect(self._on_selection_changed)
        self.obj_manager.object_added.connect(self._on_object_added)

        if self._scene_tree:
            self._scene_tree.set_object_manager(self.obj_manager)

        self.camera = Camera(self)
        self.camera.init(self.obj_manager)

        self.obj_manager.set_picking_callback(self.interactor)

        self.axes = AxesTool(self)
        self.ruler = RulerTool(self)

        self._state = SceneState(self)

    def _build_toolbar(self):
        """툴바 구성 - 서브클래스에서 오버라이드 가능"""
        home = self._add_action("\u2302", "", self.camera.home)
        home.setToolTip("Home")

        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            self._add_action(
                name, f"{name.lower()}.png",
                partial(self.camera.set_view, name.lower())
            )

        self.toolbar.addSeparator()

        self._add_action("Zoom In", "zoom_in.png", lambda: self.camera.zoom_in())
        self._add_action("Zoom Out", "zoom_out.png", lambda: self.camera.zoom_out())
        self._add_action("Fit", "fit.png", self.fit_to_scene)

        self._projection_action = self._add_toggle_action(
            "Projection", "perspective.png", "parallel.png",
            self._on_projection_toggled, checked=False
        )

        self.toolbar.addSeparator()

        self._action_select_all = self._add_action("Select All", "select_all.png", self._on_select_all)
        self._action_deselect = self._add_action("Deselect", "deselect.png", self._on_clear_selection)

        self.toolbar.addSeparator()

        self._axes_action = self._add_toggle_action(
            "Axes", "axes_on.png", "axes_off.png",
            self._on_axes_toggled, checked=True
        )

        self._ruler_action = self._add_toggle_action(
            "Ruler", "ruler_on.png", "ruler_off.png",
            self._on_ruler_toggled, checked=False
        )

        self.toolbar.addSeparator()

        self._view_combo = QComboBox()
        self._view_combo.addItems([
            "wireframe",
            "surface",
            "surface with edge",
            "transparent",
        ])
        self._view_combo.setCurrentText("transparent")
        self._view_combo.currentTextChanged.connect(self._on_view_style_changed)
        self.toolbar.addWidget(self._view_combo)

        self._ground_plane_combo = QComboBox()
        self._ground_plane_combo.addItems(["Off", "XY", "YZ", "XZ"])
        self._ground_plane_combo.setCurrentText("XZ")
        self._ground_plane_combo.setToolTip("Ground Plane")
        self._ground_plane_combo.currentTextChanged.connect(self._on_ground_plane_changed)
        self.toolbar.addWidget(self._ground_plane_combo)

        self.toolbar.addSeparator()

        self._geom_visible_action = QAction("\U0001F4D0", self)
        self._geom_visible_action.setToolTip("Show Geometry")
        self._geom_visible_action.setCheckable(True)
        self._geom_visible_action.setChecked(True)
        self._geom_visible_action.triggered.connect(self._on_geometry_visibility_toggled)
        self.toolbar.addAction(self._geom_visible_action)

        self._mesh_visible_action = QAction("\U0001F5A7", self)
        self._mesh_visible_action.setToolTip("Show Mesh")
        self._mesh_visible_action.setCheckable(True)
        self._mesh_visible_action.setChecked(False)
        self._mesh_visible_action.triggered.connect(self._on_mesh_visibility_toggled)
        self.toolbar.addAction(self._mesh_visible_action)

        self._both_visible_action = QAction("\u229E", self)
        self._both_visible_action.setToolTip("Show Both (Geometry + Mesh)")
        self._both_visible_action.setCheckable(True)
        self._both_visible_action.setChecked(False)
        self._both_visible_action.triggered.connect(self._on_both_visibility_toggled)
        self.toolbar.addAction(self._both_visible_action)

        self._visibility_mode = "geometry"

        self.toolbar.addSeparator()

        self._scene_tree_action = QAction("\u2630", self)
        self._scene_tree_action.setToolTip("Scene Tree")
        self._scene_tree_action.setCheckable(True)
        self._scene_tree_action.setChecked(False)
        self._scene_tree_action.triggered.connect(self._on_scene_tree_toggled)
        self.toolbar.addAction(self._scene_tree_action)
        self._scene_tree_action.setVisible(False)

        self._clip_plane = None
        self._clip_actors = {}
        self._original_actors_visibility = {}
        self._clip_bounds = None
        self._clip_normal = None
        self._clip_mode = "off"
        self._clip_position = 50
        self._clip_invert = True
        self._clip_custom_normal = (0.0, 0.0, 1.0)
        self._clip_preview = False
        self._clip_preview_actor = None
        self._current_view_style = "transparent"

    def _set_background(self):
        """배경색 설정 - Fusion 360 스타일 화이트 그라데이션"""
        self.renderer.SetBackground(0.75, 0.78, 0.82)
        self.renderer.SetBackground2(0.98, 0.98, 1.0)
        self.renderer.GradientBackgroundOn()


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
            self._geom_visible_action.setChecked(True)

    def _on_mesh_visibility_toggled(self, checked: bool):
        """Mesh 가시성 토글 (사용자가 버튼 클릭)"""
        if checked:
            self.set_visibility_mode("mesh", apply_visibility=True)
        else:
            self._mesh_visible_action.setChecked(True)

    def _on_both_visibility_toggled(self, checked: bool):
        """Both (Geometry + Mesh) 가시성 토글 (사용자가 버튼 클릭)"""
        if checked:
            self.set_visibility_mode("both", apply_visibility=True)
        else:
            self._both_visible_action.setChecked(True)

    def _apply_visibility_mode(self, mode: str):
        """가시성 모드 실제 적용 (내부용)

        Args:
            mode: "geometry", "mesh", "both" 중 하나
        """
        for obj in self.obj_manager.get_all():
            group = getattr(obj, 'group', 'default')

            if mode == "geometry":
                obj.actor.SetVisibility(group == "geometry")
            elif mode == "mesh":
                obj.actor.SetVisibility(group == "mesh")
            elif mode == "both":
                obj.actor.SetVisibility(True)
                prop = getattr(obj.actor, 'GetProperty', None)
                if prop is not None:
                    if group == "geometry":
                        prop().SetOpacity(0.3)
                    else:
                        prop().SetOpacity(1.0)

        if mode != "both":
            for obj in self.obj_manager.get_all():
                prop = getattr(obj.actor, 'GetProperty', None)
                if prop is not None:
                    prop().SetOpacity(1.0)

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

        self._geom_visible_action.setChecked(mode == "geometry")
        self._mesh_visible_action.setChecked(mode == "mesh")
        self._both_visible_action.setChecked(mode == "both")

        if apply_visibility:
            self._apply_visibility_mode(mode)

    def _on_view_style_changed(self, style: str):
        """뷰 스타일 변경"""
        self._current_view_style = style
        self.obj_manager.all().style(style)

        self._apply_style_to_clip_actors(style)

        if self.obj_manager._selected_ids:
            self.obj_manager._update_selection_visual()

        self.render()

    def _on_ground_plane_changed(self, plane: str):
        """바닥 평면 변경"""
        if plane == "Off":
            self.hide_ground_plane()
        else:
            self.show_ground_plane(plane=plane.lower())

    def _on_scene_tree_toggled(self, checked: bool):
        """씬 트리 토글"""
        if checked:
            self.enable_scene_tree()
        else:
            self.disable_scene_tree()

    def _on_clip_mode_changed(self, mode: str):
        """클립 모드 변경 (내부 처리)"""
        self._clear_clip()
        self._remove_preview_plane()
        self._restore_original_visibility()

        if mode == "off":
            self._clip_bounds = None
            self._clip_normal = None
            self._clip_mode = "off"
            self.render()
            return

        if mode == "x":
            normal = (1, 0, 0)
        elif mode == "y":
            normal = (0, 1, 0)
        elif mode == "z":
            normal = (0, 0, 1)
        elif mode == "custom":
            normal = self._clip_custom_normal
        else:
            return

        self._clip_normal = normal
        self._clip_mode = mode

        self._calculate_clip_bounds()

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
                if not obj.actor.GetVisibility():
                    continue

                bounds = obj.actor.GetBounds()
                min_x = min(min_x, bounds[0])
                max_x = max(max_x, bounds[1])
                min_y = min(min_y, bounds[2])
                max_y = max(max_y, bounds[3])
                min_z = min(min_z, bounds[4])
                max_z = max(max_z, bounds[5])
            except Exception:
                continue

        if min_x == float("inf"):
            self._clip_bounds = None
            return

        self._clip_bounds = (min_x, max_x, min_y, max_y, min_z, max_z)

    def _on_clip_position_changed(self, value: int):
        """클립 위치 변경 (내부 처리)"""
        self._clip_position = value

        if self._clip_bounds is None or self._clip_normal is None:
            return

        if self._clip_preview:
            if self._clip_actors:
                self._clear_clip()
                self._restore_original_visibility()
            self._remove_preview_plane()
            self._show_preview_plane()
        else:
            self._clear_clip()
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

        slider_val = self._clip_position / 100.0
        min_x, max_x, min_y, max_y, min_z, max_z = self._clip_bounds

        if self._clip_normal == (1, 0, 0):
            clip_pos = min_x + (max_x - min_x) * slider_val
            origin = (clip_pos, (min_y + max_y) / 2, (min_z + max_z) / 2)
        elif self._clip_normal == (0, 1, 0):
            clip_pos = min_y + (max_y - min_y) * slider_val
            origin = ((min_x + max_x) / 2, clip_pos, (min_z + max_z) / 2)
        else:
            clip_pos = min_z + (max_z - min_z) * slider_val
            origin = ((min_x + max_x) / 2, (min_y + max_y) / 2, clip_pos)

        self._clip_plane = vtkPlane()
        self._clip_plane.SetOrigin(origin)
        self._clip_plane.SetNormal(self._clip_normal)

        for obj in all_objs:
            try:
                current_visibility = obj.actor.GetVisibility()

                if not current_visibility:
                    if obj.id in self._clip_actors:
                        try:
                            self.renderer.RemoveActor(self._clip_actors[obj.id])
                        except Exception:
                            pass
                        del self._clip_actors[obj.id]
                    continue

                self._original_actors_visibility[obj.id] = True

                obj.actor.SetVisibility(False)

                mapper = obj.actor.GetMapper()
                if mapper is None:
                    continue

                input_data = mapper.GetInput()
                if input_data is None:
                    continue

                clipper = vtkClipPolyData()
                clipper.SetInputData(input_data)
                clipper.SetClipFunction(self._clip_plane)
                if self._clip_invert:
                    clipper.InsideOutOn()
                clipper.Update()

                clip_mapper = vtkPolyDataMapper()
                clip_mapper.SetInputConnection(clipper.GetOutputPort())
                clip_mapper.ScalarVisibilityOff()

                clip_actor = vtkActor()
                clip_actor.SetMapper(clip_mapper)

                clip_actor.SetPosition(obj.actor.GetPosition())
                clip_actor.SetOrientation(obj.actor.GetOrientation())
                clip_actor.SetScale(obj.actor.GetScale())
                clip_actor.SetOrigin(obj.actor.GetOrigin())
                if obj.actor.GetUserMatrix():
                    clip_actor.SetUserMatrix(obj.actor.GetUserMatrix())

                from .core.object_manager import ObjectManager
                _STYLE_COLOR = ObjectManager._STYLE_COLOR
                orig_color = tuple(c / 255.0 for c in obj.color)
                prop = clip_actor.GetProperty()

                style = self._current_view_style
                if style == "wireframe":
                    prop.SetRepresentationToWireframe()
                    prop.EdgeVisibilityOff()
                    prop.SetColor(_STYLE_COLOR)
                    prop.SetOpacity(1.0)
                elif style == "surface":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOff()
                    prop.SetColor(orig_color)
                    prop.SetOpacity(1.0)
                elif style == "surface with edge":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOn()
                    prop.SetEdgeColor(0.12, 0.15, 0.25)
                    prop.SetColor(_STYLE_COLOR)
                    prop.SetOpacity(1.0)
                elif style == "transparent":
                    prop.SetRepresentationToSurface()
                    prop.EdgeVisibilityOff()
                    prop.SetOpacity(0.5)
                    prop.SetColor(orig_color)

                self.renderer.AddActor(clip_actor)
                self._clip_actors[obj.id] = clip_actor

            except Exception:
                continue

    def _clear_clip(self):
        """클립 액터 제거"""
        for obj_id, actor in self._clip_actors.items():
            try:
                self.renderer.RemoveActor(actor)
            except Exception:
                pass
        self._clip_actors.clear()
        self._clip_plane = None

    def _show_preview_plane(self):
        """클립 위치를 보여주는 미리보기 평면 표시"""
        from vtkmodules.vtkFiltersSources import vtkPlaneSource
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        if self._clip_bounds is None or self._clip_normal is None:
            return

        self._remove_preview_plane()

        min_x, max_x, min_y, max_y, min_z, max_z = self._clip_bounds
        slider_val = self._clip_position / 100.0

        margin = 0.1
        size_x = (max_x - min_x) * margin
        size_y = (max_y - min_y) * margin
        size_z = (max_z - min_z) * margin

        ext_min_x = min_x - size_x
        ext_max_x = max_x + size_x
        ext_min_y = min_y - size_y
        ext_max_y = max_y + size_y
        ext_min_z = min_z - size_z
        ext_max_z = max_z + size_z

        plane_source = vtkPlaneSource()

        if self._clip_normal == (1, 0, 0):
            clip_pos = min_x + (max_x - min_x) * slider_val
            plane_source.SetOrigin(clip_pos, ext_min_y, ext_min_z)
            plane_source.SetPoint1(clip_pos, ext_max_y, ext_min_z)
            plane_source.SetPoint2(clip_pos, ext_min_y, ext_max_z)
        elif self._clip_normal == (0, 1, 0):
            clip_pos = min_y + (max_y - min_y) * slider_val
            plane_source.SetOrigin(ext_min_x, clip_pos, ext_min_z)
            plane_source.SetPoint1(ext_max_x, clip_pos, ext_min_z)
            plane_source.SetPoint2(ext_min_x, clip_pos, ext_max_z)
        else:
            clip_pos = min_z + (max_z - min_z) * slider_val
            plane_source.SetOrigin(ext_min_x, ext_min_y, clip_pos)
            plane_source.SetPoint1(ext_max_x, ext_min_y, clip_pos)
            plane_source.SetPoint2(ext_min_x, ext_max_y, clip_pos)

        plane_source.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(plane_source.GetOutputPort())

        self._clip_preview_actor = vtkActor()
        self._clip_preview_actor.SetMapper(mapper)

        prop = self._clip_preview_actor.GetProperty()
        prop.SetColor(1.0, 0.3, 0.3)
        prop.SetOpacity(0.4)
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(1.0, 0.0, 0.0)
        prop.SetLineWidth(2.0)

        self.renderer.AddActor(self._clip_preview_actor)

    def _remove_preview_plane(self):
        """미리보기 평면 제거"""
        if self._clip_preview_actor:
            try:
                self.renderer.RemoveActor(self._clip_preview_actor)
            except Exception:
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

        from .core.object_manager import ObjectManager
        _STYLE_COLOR = ObjectManager._STYLE_COLOR

        for obj_id, actor in self._clip_actors.items():
            prop = actor.GetProperty()
            obj = self.obj_manager.get(obj_id)
            orig_color = tuple(c / 255.0 for c in obj.color) if obj else (0.6, 0.65, 0.7)

            if style == "wireframe":
                prop.SetRepresentationToWireframe()
                prop.EdgeVisibilityOff()
                prop.SetColor(_STYLE_COLOR)
                prop.SetOpacity(1.0)
            elif style == "surface":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOff()
                prop.SetColor(orig_color)
                prop.SetOpacity(1.0)
            elif style == "surface with edge":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOn()
                prop.SetEdgeColor(0.12, 0.15, 0.25)
                prop.SetColor(_STYLE_COLOR)
                prop.SetOpacity(1.0)
            elif style == "transparent":
                prop.SetRepresentationToSurface()
                prop.EdgeVisibilityOff()
                prop.SetOpacity(0.5)
                prop.SetColor(orig_color)

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

    def _on_object_added(self, obj_id: int, name: str):
        """객체 추가 이벤트 - 현재 view style 적용 + 바닥 평면 자동 업데이트"""
        obj = self.obj_manager.get(obj_id)
        if obj:
            self.obj_manager._apply_style(obj, self._current_view_style)
        self.update_ground_plane()


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
        """씬에 맞춰 카메라 리셋. 선택된 객체가 있으면 해당 영역으로만 fit."""
        bounds = self._get_selected_bounds()
        if bounds:
            self.camera.fit_to_bounds(bounds)
        else:
            self.camera.fit()

    def _get_selected_bounds(self):
        """선택된 객체들의 합산 bounds 반환. 없으면 None."""
        if not self.obj_manager or not self.obj_manager.selected_ids:
            return None
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")
        for sid in self.obj_manager.selected_ids:
            obj = self.obj_manager.get(sid)
            if not obj:
                continue
            try:
                b = obj.actor.GetBounds()
                min_x = min(min_x, b[0]); max_x = max(max_x, b[1])
                min_y = min(min_y, b[2]); max_y = max(max_y, b[3])
                min_z = min(min_z, b[4]); max_z = max(max_z, b[5])
            except Exception:
                continue
        if min_x == float("inf"):
            return None
        return (min_x, max_x, min_y, max_y, min_z, max_z)

    def render(self):
        """즉시 렌더링"""
        self.vtk_widget.GetRenderWindow().Render()

    def set_background(self, color1: tuple, color2: tuple = None):
        """배경색 설정

        Args:
            color1: RGB (0-1) 또는 (0-255)
            color2: 그라데이션용 두 번째 색상 (선택)
        """
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
        if mode not in ("off", "x", "y", "z", "custom"):
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

        self._remove_preview_plane()

        self._clip_preview = False
        self._apply_clip()
        self.render()

    def reset_clip(self):
        """클립을 원래 상태로 복원 (미리보기 평면은 유지)"""
        if self._clip_mode == "off":
            return

        self._clear_clip()

        self._restore_original_visibility()

        self._clip_preview = True
        self._show_preview_plane()
        self.render()

    def set_clip_invert(self, invert: bool):
        self._clip_invert = invert
        if self._clip_mode != "off" and not self._clip_preview:
            self._clear_clip()
            self._restore_original_visibility()
            self._apply_clip()
            self.render()

    def set_clip_custom_normal(self, nx: float, ny: float, nz: float):
        """커스텀 클립 법선 벡터 설정 (자동 정규화)"""
        import math
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-6:
            return
        self._clip_custom_normal = (nx / length, ny / length, nz / length)
        if self._clip_mode == "custom":
            self._clip_normal = self._clip_custom_normal
            self._on_clip_mode_changed("custom")

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
                if obj_id in self._original_actors_visibility:
                    pass
                else:
                    try:
                        self.renderer.RemoveActor(clip_actor)
                    except Exception:
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


    def show_ground_plane(self, plane: str = "xy", scale: float = 1.4, offset_ratio: float = 0.05):
        """객체 아래에 반투명 바닥 평면 표시

        Args:
            plane: 평면 종류 ("xy", "yz", "xz")
            scale: 평면 크기 배율 (기본 1.4 = 바운딩 박스의 1.4배)
            offset_ratio: 오프셋 비율 (기본 0.05 = 크기의 5% 오프셋)

        사용 예시:
            widget.show_ground_plane("xy")
            widget.show_ground_plane("yz", scale=1.5)
        """
        from vtkmodules.vtkFiltersSources import vtkPlaneSource
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        self.hide_ground_plane()

        all_objs = self.obj_manager.get_all()
        has_objects = False

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
                has_objects = True
            except Exception:
                continue

        if not has_objects or min_x == float("inf"):
            min_x, max_x = -1.0, 1.0
            min_y, max_y = -0.6, 1.4
            min_z, max_z = -1.0, 1.0
            scale = 1.0
            offset_ratio = 0.0

        size_x = max_x - min_x
        size_y = max_y - min_y
        size_z = max_z - min_z

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        center_z = (min_z + max_z) / 2

        plane_source = vtkPlaneSource()

        if plane == "xy":
            half_w = (size_x * scale) / 2
            half_h = (size_y * scale) / 2
            plane_pos = min_z - (size_z * offset_ratio)
            plane_source.SetOrigin(center_x - half_w, center_y - half_h, plane_pos)
            plane_source.SetPoint1(center_x + half_w, center_y - half_h, plane_pos)
            plane_source.SetPoint2(center_x - half_w, center_y + half_h, plane_pos)
        elif plane == "yz":
            half_w = (size_y * scale) / 2
            half_h = (size_z * scale) / 2
            plane_pos = min_x - (size_x * offset_ratio)
            plane_source.SetOrigin(plane_pos, center_y - half_w, center_z - half_h)
            plane_source.SetPoint1(plane_pos, center_y + half_w, center_z - half_h)
            plane_source.SetPoint2(plane_pos, center_y - half_w, center_z + half_h)
        elif plane == "xz":
            half_w = (size_x * scale) / 2
            half_h = (size_z * scale) / 2
            plane_pos = min_y - (size_y * offset_ratio)
            plane_source.SetOrigin(center_x - half_w, plane_pos, center_z - half_h)
            plane_source.SetPoint1(center_x + half_w, plane_pos, center_z - half_h)
            plane_source.SetPoint2(center_x - half_w, plane_pos, center_z + half_h)
        else:
            return

        plane_source.SetXResolution(10)
        plane_source.SetYResolution(10)
        plane_source.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(plane_source.GetOutputPort())

        self._ground_plane_actor = vtkActor()
        self._ground_plane_actor.SetMapper(mapper)

        prop = self._ground_plane_actor.GetProperty()
        prop.SetColor(0.85, 0.85, 0.88)
        prop.SetOpacity(0.5)
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(0.7, 0.7, 0.75)
        prop.SetLineWidth(1.0)

        self.renderer.AddActor(self._ground_plane_actor)

        self.render()

    def hide_ground_plane(self):
        """바닥 평면 숨기기"""
        if self._ground_plane_actor:
            try:
                self.renderer.RemoveActor(self._ground_plane_actor)
            except Exception:
                pass
            self._ground_plane_actor = None
            self.render()

    def update_ground_plane(self, scale: float = 1.4, offset_ratio: float = 0.05):
        """바닥 평면 업데이트 (객체 변경 후 호출)

        Args:
            scale: 평면 크기 배율
            offset_ratio: 오프셋 비율
        """
        if hasattr(self, '_ground_plane_combo'):
            plane = self._ground_plane_combo.currentText().lower()
            if plane != "off":
                self.show_ground_plane(plane=plane, scale=scale, offset_ratio=offset_ratio)

    def is_ground_plane_visible(self) -> bool:
        """바닥 평면 가시성 확인"""
        return self._ground_plane_actor is not None

    def init_default_scene(self):
        """기본 씬 초기화 (빈 화면에서 XZ 평면 + 45도 뷰)

        VTK 위젯이 처음 표시될 때 호출하여
        기본 바닥 평면과 카메라 뷰를 설정합니다.

        VTK 좌표계: X=오른쪽, Y=위쪽, Z=화면 앞쪽
        """
        if hasattr(self, '_ground_plane_combo'):
            plane = self._ground_plane_combo.currentText().lower()
            if plane != "off":
                self.show_ground_plane(plane=plane)

        cam = self.renderer.GetActiveCamera()
        cam.SetPosition(2, 3, 3)
        cam.SetFocalPoint(0, 0, 0)
        cam.SetViewUp(0, 1, 0)
        self.renderer.ResetCamera()
        self.render()


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
            return False

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

        if hasattr(tool, 'cleanup'):
            tool.cleanup()
        elif hasattr(tool, 'hide'):
            tool.hide()

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

        if hasattr(self, '_scene_tree_action'):
            self._scene_tree_action.setChecked(True)

        if self._scene_tree:
            self._scene_tree.show()
            self._scene_tree.refresh()
            self._main_splitter.setSizes([200, self.width() - 200])

    def disable_scene_tree(self):
        """씬 트리 패널 비활성화

        사용 예시:
            widget.disable_scene_tree()
        """
        if not self._scene_tree_enabled:
            return

        self._scene_tree_enabled = False

        if hasattr(self, '_scene_tree_action'):
            self._scene_tree_action.setChecked(False)

        if self._scene_tree:
            self._scene_tree.hide()
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


    def cleanup(self):
        """리소스 정리"""
        try:
            self._clear_clip()
            self._restore_original_visibility()

            self.hide_ground_plane()

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

    def eventFilter(self, obj, event):
        """VTK 위젯 마우스 stuck 방지: 위젯을 벗어나거나 포커스를 잃으면 버튼 강제 해제"""
        if obj is self.vtk_widget:
            if event.type() in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                self._release_vtk_buttons()
            elif event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    self._release_vtk_buttons()
                    self.escape_pressed.emit()
        return super().eventFilter(obj, event)

    def _release_vtk_buttons(self):
        """VTK 및 CADInteractorStyle의 마우스 버튼/드래그 상태를 강제 리셋
        Python 속성만 조작 — VTK C++ 메서드 호출 금지 (segfault 방지)"""
        try:
            if self.interactor:
                style = self.interactor.GetInteractorStyle()
                if isinstance(style, CADInteractorStyle):
                    style.reset_state()

            if self.vtk_widget and hasattr(self.vtk_widget, '_ActiveButton'):
                self.vtk_widget._ActiveButton = Qt.MouseButton.NoButton
        except Exception:
            pass

    def closeEvent(self, event):
        """닫기 이벤트"""
        self.cleanup()
        super().closeEvent(event)
