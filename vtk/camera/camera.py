from PySide6.QtCore import QObject, Signal
from nextlib.vtk.camera.cad_style import CADInteractorStyle

class Camera(QObject):
    visibility_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.parent = parent
        self.registry = parent.registry
        self.renderer = parent.renderer
        self.interactor = parent.interactor

    def init(self):
        style = CADInteractorStyle(self, self.renderer)
        self.interactor.SetInteractorStyle(style)

        camera = self.renderer.GetActiveCamera()

        camera.SetFocalPoint(0.0, 0.0, 0.0)
        camera.SetPosition(0.0, -4.0, 2.5)
        camera.SetViewUp(0.0, 0.0, 1.0)
        camera.SetClippingRange(0.01, 1000)

        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()

    def setup_camera_sync(self):    # 뭔가 이벤트가 자주 발생하여 느림
        # self._cam_observer_id = self.renderer.AddObserver(
        #     "ModifiedEvent", self._on_camera_modified)
        ...

    def _on_camera_modified(self, caller, event):
        if self.parent.camera_sync_lock:
            return

        # if self.registry:
        #     self.registry.notify_camera_changed(self)

    def set_camera_view(self, view):
        camera = self.renderer.GetActiveCamera()
        bounds = [0] * 6
        self.renderer.ComputeVisiblePropBounds(bounds)
        x_min, x_max, y_min, y_max, z_min, z_max = bounds
        center = [
            (x_min + x_max) / 2.0,
            (y_min + y_max) / 2.0,
            (z_min + z_max) / 2.0,
        ]
        dx, dy, dz = x_max - x_min, y_max - y_min, z_max - z_min
        radius = (dx**2 + dy**2 + dz**2) ** 0.5 / 2.0
        if radius <= 0:
            radius = 1.0

        padding_factor = 1.2
        distance_factor = 3.0
        distance = radius * distance_factor * padding_factor

        if view == "front":
            camera.SetPosition(center[0], center[1] - distance, center[2])
            camera.SetViewUp(0, 0, 1)
        elif view == "back":
            camera.SetPosition(center[0], center[1] + distance, center[2])
            camera.SetViewUp(0, 0, 1)
        elif view == "left":
            camera.SetPosition(center[0] - distance, center[1], center[2])
            camera.SetViewUp(0, 0, 1)
        elif view == "right":
            camera.SetPosition(center[0] + distance, center[1], center[2])
            camera.SetViewUp(0, 0, 1)
        elif view == "top":
            camera.SetPosition(center[0], center[1], center[2] + distance)
            camera.SetViewUp(0, 1, 0)
        elif view == "bottom":
            camera.SetPosition(center[0], center[1], center[2] - distance)
            camera.SetViewUp(0, -1, 0)

        camera.SetFocalPoint(center)
        camera.SetClippingRange(0.001, distance * 10)
        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()
