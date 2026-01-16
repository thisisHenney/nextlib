from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkCommonColor import vtkNamedColors
import numpy as np


class RulerTool(QObject):
    visibility_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self._renderer = parent.renderer
        self._interactor = parent.interactor

        self._show_state = False
        self.actor = None

        self._initialize()

    def _initialize(self):
        colors = vtkNamedColors()
        self.axis_x_color = colors.GetColor3d("orangered")
        self.axis_y_color = colors.GetColor3d("green_yellow")
        self.axis_z_color = colors.GetColor3d("deepskyblue")

    def _apply_style(self, actor):
        actor.SetUseTextActor3D(False)

        for i, color in enumerate([self.axis_x_color,
                                   self.axis_y_color,
                                   self.axis_z_color]):
            actor.GetTitleTextProperty(i).SetColor(color)
            actor.GetTitleTextProperty(i).SetFontSize(64)
            actor.GetLabelTextProperty(i).SetColor(color)

        actor.DrawXGridlinesOn()
        actor.DrawYGridlinesOn()
        actor.DrawZGridlinesOn()
        actor.SetGridLineLocation(actor.VTK_GRID_LINES_FURTHEST)

        actor.XAxisMinorTickVisibilityOn()
        actor.YAxisMinorTickVisibilityOn()
        actor.ZAxisMinorTickVisibilityOn()

        actor.SetFlyModeToOuterEdges()

    def show(self, actors, scale=1.05):
        if self._show_state and self.actor:
            self._renderer.RemoveActor(self.actor)
            self.actor = None

        # bounds 계산
        if not actors:
            bounds = [-0.5, 0.5, -0.5, 0.5, -0.5, 0.5]
        else:
            all_bounds = np.array([actor.GetBounds() for actor in actors])
            xmin, ymin, zmin = np.min(all_bounds[:, [0, 2, 4]], axis=0)
            xmax, ymax, zmax = np.max(all_bounds[:, [1, 3, 5]], axis=0)

            cx = (xmin + xmax) / 2
            cy = (ymin + ymax) / 2
            cz = (zmin + zmax) / 2

            sx = (xmax - xmin) * scale / 2
            sy = (ymax - ymin) * scale / 2
            sz = (zmax - zmin) * scale / 2

            if sx == 0 and sy == 0 and sz == 0:
                sx = sy = sz = 0.5

            bounds = [
                cx - sx, cx + sx,
                cy - sy, cy + sy,
                cz - sz, cz + sz,
            ]

        # 새 actor 생성
        actor = vtkCubeAxesActor()
        actor.SetCamera(self._renderer.GetActiveCamera())
        actor.SetBounds(bounds)
        self._apply_style(actor)

        # renderer에 추가
        self._renderer.AddActor(actor)
        self.actor = actor

        self._interactor.Render()

        # 상태 갱신 + 시그널 emit
        if not self._show_state:
            self._show_state = True
            self.visibility_changed.emit(True)

    def hide(self):
        if not self._show_state:
            return

        if self.actor:
            self._renderer.RemoveActor(self.actor)
            self.actor = None

        self._interactor.Render()

        self._show_state = False
        self.visibility_changed.emit(False)

    def is_show(self):
        return self._show_state
