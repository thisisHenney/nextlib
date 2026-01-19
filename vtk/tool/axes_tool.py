"""
3D 축 표시 도구

화면 모서리에 X, Y, Z 축을 표시하여 현재 방향을 나타냄
"""
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor


class AxesTool(QObject):
    visibility_changed = Signal(bool)

    def __init__(self, widget):
        """
        Args:
            widget: VtkWidgetBase 인스턴스 (renderer, interactor 속성 필요)
        """
        super().__init__(widget)

        self._widget = widget
        self._renderer = widget.renderer
        self._interactor = widget.interactor
        self._visible = False

        # Axes Actor 생성
        self._axes_actor = vtkAxesActor()

        # Orientation Marker Widget 설정
        self._marker_widget = vtkOrientationMarkerWidget()
        self._marker_widget.SetOrientationMarker(self._axes_actor)
        self._marker_widget.SetInteractor(self._interactor)
        self._marker_widget.SetViewport(0.0, 0.0, 0.2, 0.2)  # 좌하단 20%

        # 기본적으로 표시
        self.show()

    def show(self):
        """축 표시"""
        if self._visible:
            return

        self._marker_widget.EnabledOn()
        self._marker_widget.InteractiveOff()
        self._interactor.Render()

        self._visible = True
        self.visibility_changed.emit(True)

    def hide(self):
        """축 숨김"""
        if not self._visible:
            return

        self._marker_widget.EnabledOff()
        self._interactor.Render()

        self._visible = False
        self.visibility_changed.emit(False)

    def toggle(self) -> bool:
        """토글 (반환: 현재 상태)"""
        if self._visible:
            self.hide()
        else:
            self.show()
        return self._visible

    def is_visible(self) -> bool:
        """현재 가시성"""
        return self._visible

    def set_viewport(self, xmin: float, ymin: float, xmax: float, ymax: float):
        """뷰포트 영역 설정 (0.0 ~ 1.0)"""
        self._marker_widget.SetViewport(xmin, ymin, xmax, ymax)
        if self._visible:
            self._interactor.Render()

    def set_axis_length(self, x: float, y: float, z: float):
        """축 길이 설정"""
        self._axes_actor.SetTotalLength(x, y, z)
        if self._visible:
            self._interactor.Render()

    def show_labels(self, show: bool = True):
        """축 라벨 표시 여부"""
        if show:
            self._axes_actor.AxisLabelsOn()
        else:
            self._axes_actor.AxisLabelsOff()

        if self._visible:
            self._interactor.Render()
