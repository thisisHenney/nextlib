from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor


class AxesTool(QObject):
    visibility_changed = Signal(bool)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.parent = parent
        self.renderer = parent.renderer
        self.interactor = parent.interactor
        self._visible = False

        self.axes_actor = vtkAxesActor()

        self.marker_widget = vtkOrientationMarkerWidget()
        self.marker_widget.SetOrientationMarker(self.axes_actor)
        self.marker_widget.SetInteractor(self.interactor)
        self.marker_widget.SetViewport(0.0, 0.0, 0.2, 0.2)

        self.show()

    def show(self):
        if self._visible:
            return

        self.marker_widget.EnabledOn()
        self.marker_widget.InteractiveOff()

        self.interactor.Render()

        self._visible = True
        self.visibility_changed.emit(True)

    def hide(self):
        if not self._visible:
            return

        self.marker_widget.EnabledOff()
        self.interactor.Render()

        self._visible = False
        self.visibility_changed.emit(False)

    def is_visible(self):
        return self._visible

    def set_axis_length(self, x: float, y: float, z: float):
        self.axes_actor.SetTotalLength(x, y, z)
        if self._visible:
            self.interactor.Render()

    def show_labels(self, show=True):
        if show:
            self.axes_actor.AxisLabelsOn()
        else:
            self.axes_actor.AxisLabelsOff()

        if self._visible:
            self.interactor.Render()

    def set_viewport(self, xmin, ymin, xmax, ymax):
        self.marker_widget.SetViewport(xmin, ymin, xmax, ymax)
        if self._visible:
            self.interactor.Render()
