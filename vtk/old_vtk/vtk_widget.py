from functools import partial
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QComboBox
from PySide6.QtGui import QAction, QIcon

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer
from vtkmodules.vtkCommonColor import vtkNamedColors

from nextlib.vtk.camera.camera import Camera
from nextlib.vtk.object.object_manager import ObjectManager
from nextlib.vtk.tool.axes_tool import AxesTool
from nextlib.vtk.tool.point_probe_tool import PointProbeTool
from nextlib.vtk.tool.ruler_tool import RulerTool
from nextlib.vtk.sources.geometry_source import GeometrySource
from nextlib.vtk.sources.mesh_loader import MeshLoader


RES_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = Path(RES_DIR / "vtk" / "res" / "icon")

class VtkWidget(QWidget): # QMainWindow
    def __init__(self, parent=None, registry=None):
        super().__init__(parent)
        self.parent = parent
        self.registry = registry
        self.camera_sync_lock = False

        if isinstance(self, QWidget):
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            self.toolbar = QToolBar("Viewer Toolbar", self)
            self.toolbar.setFloatable(True)
            self.toolbar.setMovable(True)
            layout.addWidget(self.toolbar)

            self.vtk_widget = QVTKRenderWindowInteractor(self)
            layout.addWidget(self.vtk_widget, stretch=1)

        # elif isinstance(self, QMainWindow):
        #     central_widget = QWidget()
        #     layout = QVBoxLayout(central_widget)
        #     layout.setContentsMargins(0, 0, 0, 0)
        #     layout.setSpacing(0)
        #
        #     self.toolbar = QToolBar("Viewer Toolbar", self)
        #     self.toolbar.setFloatable(True)
        #     self.toolbar.setMovable(True)
        #     self.addToolBar(self.toolbar)

        #     self.vtk_widget = QVTKRenderWindowInteractor(central_widget)
        #     layout.addWidget(self.vtk_widget, stretch=1)
        #
        #     self.setCentralWidget(central_widget)

        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

        self.camera = Camera(self)
        self.camera.init()

        self.obj_manager = ObjectManager(self.renderer)
        self.obj_manager.set_picking_callback(self.interactor)
        # self.obj_manager.selection_changed.connect(self.on_selection_changed)

        self.colors = vtkNamedColors()
        self.axes = AxesTool(self)
        self.ruler = RulerTool(self)
        
        self.point_tool = PointProbeTool(self.parent, self)  # 나중에 추가하는 방식으로 변경할 것
        # self.point_tool.center_moved.connect(self.on_box_center)
        # self.point_tool.show()

        self.geometry_source = GeometrySource()
        self.mesh_loader = MeshLoader()

        self._build_toolbar()

        self.set_widget_style()

        self.interactor.Initialize()
        # self.show()

    # def on_selection_changed(self, info:dict):
    #     print(info)

    def set_defaults(self):
        ...

    def end(self):
        if getattr(self, "_ended", False):
            return
        self._ended = True

        self.cleanup()

        if self.registry:
            self.registry.unregister(self)

    def closeEvent(self, event):
        self.end()

        super().closeEvent(event)

    def cleanup(self):
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
            print("[!!] Error (cleanup):", e)

    def set_widget_style(self):
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)  # Down
        self.renderer.GradientBackgroundOn()

    def make_icon(self, name: str) -> QIcon:
        return QIcon(str(Path(ICON_DIR / name) ))

    def on_axes_toggled(self, checked):
        icon_name = "axes_on.png" if checked else "axes_off.png"
        self.axe_action.setIcon(self.make_icon(icon_name))
        self.toggle_axes(checked)

    def on_ruler_toggled(self, checked):
        icon_name = "ruler_on.png" if checked else "ruler_off.png"
        self.ruler_action.setIcon(self.make_icon(icon_name))
        self.toggle_ruler(checked)

    def on_projection_toggled(self, checked):
        icon_name = "parallel.png" if checked else "perspective.png"
        self.projection_action.setIcon(self.make_icon(icon_name))
        self.toggle_projection(checked)

    def _build_toolbar(self):
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

        # Camera
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
        self.view_combo.setCurrentText("surface")
        self.view_combo.currentTextChanged.connect(self.on_view_style_changed)
        self.toolbar.addWidget(self.view_combo)

    def add_toolbar_action(self, text, slot, icon_name=None):
        act = QAction(self.make_icon(icon_name) if icon_name else QIcon(), text, self)
        act.triggered.connect(partial(slot))
        self.toolbar.addAction(act)

    def toggle_axes(self, checked: bool):
        if checked:
            self.axes.show()
            self.point_tool.show()
        else:
            self.axes.hide()
            self.point_tool.hide()

    def toggle_ruler(self, checked: bool):
        if checked:
            actors = [obj.actor for obj in self.obj_manager.objects.values()]
            self.ruler.show(actors)
        else:
            self.ruler.hide()

    def fit_to_scene(self):
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def toggle_projection(self, checked: bool):
        camera = self.renderer.GetActiveCamera()
        camera.SetParallelProjection(not camera.GetParallelProjection())
        self.vtk_widget.GetRenderWindow().Render()

    def on_view_style_changed(self, style):
        for obj in self.obj_manager.get_all_objects():
            self.obj_manager.apply("style", value=style, obj_id=obj.id)
        self.vtk_widget.GetRenderWindow().Render()

    def render_now(self):
        self.vtk_widget.GetRenderWindow().Render()
        QApplication.processEvents()
