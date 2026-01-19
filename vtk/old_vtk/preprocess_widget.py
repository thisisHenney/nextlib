"""
전처리용 VTK 위젯
메쉬 파일(STL, OBJ 등)을 불러와 시각화하고 편집하는 기능 제공
"""
from functools import partial
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QComboBox, QFileDialog
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer
from vtkmodules.vtkCommonColor import vtkNamedColors

from nextlib.vtk.camera.camera import Camera
from nextlib.vtk.object.object_manager import ObjectManager
from nextlib.vtk.tool.axes_tool import AxesTool
from nextlib.vtk.tool.ruler_tool import RulerTool
from nextlib.vtk.sources.geometry_source import GeometrySource
from nextlib.vtk.sources.mesh_loader import MeshLoader


RES_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = Path(RES_DIR / "vtk" / "res" / "icon")


class PreprocessWidget(QWidget):
    """
    전처리용 VTK 위젯
    - 메쉬 파일 로딩 및 시각화
    - 객체 선택 및 편집
    - 뷰 컨트롤 (카메라, 축, 눈금자 등)
    """

    mesh_loaded = Signal(str)  # 메쉬 로드 완료 시그널
    selection_changed = Signal(dict)  # 선택 변경 시그널

    def __init__(self, parent=None, registry=None):
        super().__init__(parent)
        self.parent = parent
        self.registry = registry
        self.camera_sync_lock = False

        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()

        self.set_widget_style()
        self.interactor.Initialize()

    def _setup_ui(self):
        """UI 레이아웃 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = QToolBar("Preprocess Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        layout.addWidget(self.toolbar)

        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget, stretch=1)

    def _setup_vtk(self):
        """VTK 렌더러 및 인터랙터 설정"""
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

    def _setup_tools(self):
        """VTK 도구 초기화"""
        self.camera = Camera(self)
        self.camera.init()

        self.obj_manager = ObjectManager(self.renderer)
        self.obj_manager.set_picking_callback(self.interactor)
        self.obj_manager.selection_changed.connect(self._on_selection_changed)

        self.colors = vtkNamedColors()
        self.axes = AxesTool(self)
        self.ruler = RulerTool(self)

        self.geometry_source = GeometrySource()
        self.mesh_loader = MeshLoader()

    def _on_selection_changed(self, info: dict):
        """객체 선택 변경 이벤트"""
        self.selection_changed.emit(info)

    def _build_toolbar(self):
        """툴바 구성"""
        # 파일 로드
        self.add_toolbar_action("Load STL", self.load_stl_file, None)
        self.toolbar.addSeparator()

        # Axes, Ruler
        icon = self.make_icon("axes_on.png")
        self.axe_action = QAction(icon, "Axes On/Off", self)
        self.axe_action.setCheckable(True)
        self.axe_action.setChecked(True)
        self.axe_action.triggered.connect(self.on_axes_toggled)
        self.toolbar.addAction(self.axe_action)

        icon = self.make_icon("ruler_off.png")
        self.ruler_action = QAction(icon, "Ruler On/Off", self)
        self.ruler_action.setCheckable(True)
        self.ruler_action.setChecked(False)
        self.ruler_action.triggered.connect(self.on_ruler_toggled)
        self.toolbar.addAction(self.ruler_action)

        self.toolbar.addSeparator()

        # Camera Views
        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            act = QAction(self.make_icon(f"{name.lower()}.png"), name, self)
            act.triggered.connect(partial(self.camera.set_camera_view, name.lower()))
            self.toolbar.addAction(act)

        self.toolbar.addSeparator()

        # Fit
        self.add_toolbar_action("Fit", self.fit_to_scene, "fit.png")

        # Projection
        icon = self.make_icon("perspective.png")
        self.projection_action = QAction(icon, "Persp/Ortho", self)
        self.projection_action.setCheckable(True)
        self.projection_action.setChecked(False)
        self.projection_action.triggered.connect(self.on_projection_toggled)
        self.toolbar.addAction(self.projection_action)

        self.toolbar.addSeparator()

        # View Style ComboBox
        self.view_combo = QComboBox()
        self.view_combo.addItems([
            "wireframe",
            "surface",
            "surface with edge",
            "transparent surface",
        ])
        self.view_combo.setCurrentText("surface with edge")
        self.view_combo.currentTextChanged.connect(self.on_view_style_changed)
        self.toolbar.addWidget(self.view_combo)

    def make_icon(self, name: str) -> QIcon:
        """아이콘 생성"""
        return QIcon(str(Path(ICON_DIR / name)))

    def add_toolbar_action(self, text, slot, icon_name=None):
        """툴바 액션 추가"""
        act = QAction(self.make_icon(icon_name) if icon_name else QIcon(), text, self)
        act.triggered.connect(partial(slot))
        self.toolbar.addAction(act)

    # ===== 파일 로딩 =====

    def load_stl_file(self):
        """STL 파일 로드 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load STL File",
            "",
            "STL Files (*.stl);;All Files (*.*)"
        )
        if file_path:
            self.load_stl(file_path)

    def load_stl(self, file_path: str | Path, solid_split: bool = True):
        """STL 파일 로드"""
        actors = self.mesh_loader.load_stl(file_path, solid_split)

        if actors is None:
            return

        if not isinstance(actors, list):
            actors = [actors]

        file_name = Path(file_path).name
        for i, actor in enumerate(actors):
            name = f"{file_name}_part{i}" if len(actors) > 1 else file_name
            obj_id = self.obj_manager.add(actor, group=0, name=name)
            self.obj_manager.set_path(obj_id, str(file_path))

        self.fit_to_scene()
        self.mesh_loaded.emit(str(file_path))

    def add_geometry(self, geometry_type: str = "cube"):
        """기본 기하학 도형 추가"""
        if geometry_type == "cube":
            actor = self.geometry_source.make_cube()
        elif geometry_type == "sphere":
            actor = self.geometry_source.make_sphere()
        else:
            return

        # 먼저 객체 추가하고 ID를 받음
        obj_id = self.obj_manager.add(actor)
        # ID를 사용해서 이름 설정
        self.obj_manager.set_name(obj_id, f"{geometry_type}_{obj_id}")
        self.fit_to_scene()
        return obj_id

    # ===== 뷰 컨트롤 =====

    def on_axes_toggled(self, checked):
        """축 표시 토글"""
        icon_name = "axes_on.png" if checked else "axes_off.png"
        self.axe_action.setIcon(self.make_icon(icon_name))
        self.toggle_axes(checked)

    def on_ruler_toggled(self, checked):
        """눈금자 표시 토글"""
        icon_name = "ruler_on.png" if checked else "ruler_off.png"
        self.ruler_action.setIcon(self.make_icon(icon_name))
        self.toggle_ruler(checked)

    def on_projection_toggled(self, checked):
        """투영 방식 토글 (원근/평행)"""
        icon_name = "parallel.png" if checked else "perspective.png"
        self.projection_action.setIcon(self.make_icon(icon_name))
        self.toggle_projection(checked)

    def toggle_axes(self, checked: bool):
        """축 표시/숨김"""
        if checked:
            self.axes.show()
        else:
            self.axes.hide()

    def toggle_ruler(self, checked: bool):
        """눈금자 표시/숨김"""
        if checked:
            actors = [obj.actor for obj in self.obj_manager.objects.values()]
            self.ruler.show(actors)
        else:
            self.ruler.hide()

    def fit_to_scene(self):
        """씬에 맞춰 카메라 리셋"""
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def toggle_projection(self, checked: bool):
        """투영 방식 전환"""
        camera = self.renderer.GetActiveCamera()
        camera.SetParallelProjection(not camera.GetParallelProjection())
        self.vtk_widget.GetRenderWindow().Render()

    def on_view_style_changed(self, style: str):
        """뷰 스타일 변경"""
        for obj in self.obj_manager.get_all_objects():
            self.obj_manager.apply("style", value=style, obj_id=obj.id)
        self.vtk_widget.GetRenderWindow().Render()

    def set_widget_style(self):
        """위젯 스타일 설정 (배경색 등)"""
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)  # Down
        self.renderer.GradientBackgroundOn()

    # ===== 렌더링 =====

    def render_now(self):
        """즉시 렌더링"""
        self.vtk_widget.GetRenderWindow().Render()

    # ===== 정리 =====

    def end(self):
        """위젯 종료"""
        if getattr(self, "_ended", False):
            return
        self._ended = True

        self.cleanup()

        if self.registry:
            self.registry.unregister(self)

    def closeEvent(self, event):
        """닫기 이벤트"""
        self.end()
        super().closeEvent(event)

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

            rw = None
            if self.vtk_widget:
                rw = self.vtk_widget.GetRenderWindow()
            if rw:
                rw.Finalize()
                rw.SetWindowInfo("")
                rw = None
            self.vtk_widget = None

        except Exception as e:
            print(f"[!!] Error (cleanup): {e}")
