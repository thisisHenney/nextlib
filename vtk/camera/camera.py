"""
카메라 컨트롤러

- 초기 카메라 설정
- 6방향 뷰 전환 (front, back, left, right, top, bottom)
- 투영 방식 전환 (perspective / orthographic)
"""
from PySide6.QtCore import QObject, Signal
from .cad_style import CADInteractorStyle


class Camera(QObject):
    view_changed = Signal(str)  # 뷰 변경 시그널

    def __init__(self, widget):
        """
        Args:
            widget: VtkWidgetBase 인스턴스 (renderer, interactor, registry 속성 필요)
        """
        super().__init__(widget)

        self._widget = widget
        self._renderer = widget.renderer
        self._interactor = widget.interactor
        self._registry = getattr(widget, 'registry', None)

    @property
    def registry(self):
        return self._registry

    def init(self):
        """카메라 및 인터랙터 스타일 초기화"""
        # CAD 스타일 인터랙터 설정
        style = CADInteractorStyle(self, self._renderer)
        self._interactor.SetInteractorStyle(style)

        # 초기 카메라 설정
        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint(0.0, 0.0, 0.0)
        camera.SetPosition(0.0, -4.0, 2.5)
        camera.SetViewUp(0.0, 0.0, 1.0)
        camera.SetClippingRange(0.01, 1000)

        self._renderer.ResetCameraClippingRange()
        self._render()

    def set_view(self, view: str):
        """카메라 뷰 설정

        Args:
            view: "front", "back", "left", "right", "top", "bottom"
        """
        camera = self._renderer.GetActiveCamera()

        # 현재 씬의 바운딩 박스 계산
        bounds = [0] * 6
        self._renderer.ComputeVisiblePropBounds(bounds)
        x_min, x_max, y_min, y_max, z_min, z_max = bounds

        # 중심점 계산
        center = [
            (x_min + x_max) / 2.0,
            (y_min + y_max) / 2.0,
            (z_min + z_max) / 2.0,
        ]

        # 반지름 및 거리 계산
        dx, dy, dz = x_max - x_min, y_max - y_min, z_max - z_min
        radius = (dx**2 + dy**2 + dz**2) ** 0.5 / 2.0
        if radius <= 0:
            radius = 1.0

        padding_factor = 1.2
        distance_factor = 3.0
        distance = radius * distance_factor * padding_factor

        # 뷰별 카메라 위치 설정
        view = view.lower()
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
        self._renderer.ResetCameraClippingRange()
        self._render()

        self.view_changed.emit(view)

    def set_parallel_projection(self, enabled: bool):
        """평행 투영 설정

        Args:
            enabled: True면 평행 투영, False면 원근 투영
        """
        camera = self._renderer.GetActiveCamera()
        camera.SetParallelProjection(enabled)
        self._render()

    def toggle_projection(self):
        """투영 방식 토글"""
        camera = self._renderer.GetActiveCamera()
        camera.SetParallelProjection(not camera.GetParallelProjection())
        self._render()
        return camera.GetParallelProjection()

    def is_parallel_projection(self) -> bool:
        """현재 평행 투영 여부"""
        return bool(self._renderer.GetActiveCamera().GetParallelProjection())

    def fit(self):
        """씬에 맞춰 카메라 리셋"""
        self._renderer.ResetCamera()
        self._render()

    def get_vtk_camera(self):
        """VTK 카메라 객체 반환"""
        return self._renderer.GetActiveCamera()

    def _render(self):
        """렌더링"""
        try:
            rw = self._renderer.GetRenderWindow()
            if rw:
                rw.Render()
        except:
            pass
