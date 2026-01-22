"""
카메라 컨트롤러

- 초기 카메라 설정
- 6방향 뷰 전환 (front, back, left, right, top, bottom)
- 투영 방식 전환 (perspective / orthographic)
- 줌 인/아웃
- 홈 뷰 (초기 뷰로 리셋)
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

    def init(self, obj_manager=None):
        """카메라 및 인터랙터 스타일 초기화

        Args:
            obj_manager: ObjectManager 인스턴스 (더블클릭 선택용)
        """
        # CAD 스타일 인터랙터 설정
        style = CADInteractorStyle(self, self._renderer, obj_manager)
        self._interactor.SetInteractorStyle(style)
        self._style = style  # 나중에 obj_manager 설정을 위해 저장

        # 초기 카메라 설정 및 저장
        camera = self._renderer.GetActiveCamera()
        camera.SetFocalPoint(0.0, 0.0, 0.0)
        camera.SetPosition(0.0, -4.0, 2.5)
        camera.SetViewUp(0.0, 0.0, 1.0)
        camera.SetClippingRange(0.01, 1000)

        # 홈 뷰를 위한 초기 상태 저장
        self._home_position = (0.0, -4.0, 2.5)
        self._home_focal_point = (0.0, 0.0, 0.0)
        self._home_view_up = (0.0, 0.0, 1.0)

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

    def home(self):
        """홈 뷰로 리셋 (초기 카메라 방향 + 씬에 맞춤)"""
        camera = self._renderer.GetActiveCamera()
        camera.SetPosition(*self._home_position)
        camera.SetFocalPoint(*self._home_focal_point)
        camera.SetViewUp(*self._home_view_up)
        # 씬에 맞춰 카메라 거리 조정
        self._renderer.ResetCamera()
        self._render()
        self.view_changed.emit("home")

    def zoom_in(self, factor: float = 1.2):
        """줌 인

        Args:
            factor: 줌 배율 (기본 1.2 = 20% 확대)
        """
        camera = self._renderer.GetActiveCamera()
        camera.Dolly(factor)
        self._renderer.ResetCameraClippingRange()
        self._render()

    def zoom_out(self, factor: float = 1.2):
        """줌 아웃

        Args:
            factor: 줌 배율 (기본 1.2 = 20% 축소)
        """
        camera = self._renderer.GetActiveCamera()
        camera.Dolly(1.0 / factor)
        self._renderer.ResetCameraClippingRange()
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
