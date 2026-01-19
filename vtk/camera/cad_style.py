"""
CAD 스타일 마우스 인터랙션

- 좌클릭: 회전
- 좌클릭 + Shift: 패닝
- 좌클릭 + Ctrl: 줌 (돌리)
- 중클릭: 패닝
- 휠: 줌
- 더블클릭: 클릭 위치로 포커스
"""
import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera


class CADInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, camera_controller=None, renderer=None):
        super().__init__()

        self.camera_controller = camera_controller
        if renderer is not None:
            self.SetDefaultRenderer(renderer)

        # 마우스 상태
        self._is_rotating = False
        self._is_panning = False
        self._shift_pressed = False
        self._ctrl_pressed = False

        # 이벤트 등록
        self.AddObserver("LeftButtonPressEvent", self._on_left_button_down)
        self.AddObserver("LeftButtonReleaseEvent", self._on_left_button_up)
        self.AddObserver("MiddleButtonPressEvent", self._on_middle_button_down)
        self.AddObserver("MiddleButtonReleaseEvent", self._on_middle_button_up)
        self.AddObserver("MouseMoveEvent", self._on_mouse_move)
        self.AddObserver("MouseWheelForwardEvent", self._on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self._on_wheel_backward)
        self.AddObserver("LeftButtonDoubleClickEvent", self._on_double_click)

    def _sync_camera(self):
        """카메라 동기화 (registry 사용 시)"""
        if self.camera_controller and hasattr(self.camera_controller, 'registry'):
            registry = self.camera_controller.registry
            if registry:
                registry.notify_camera_changed(self.camera_controller)

    def _on_left_button_down(self, obj, event):
        interactor = self.GetInteractor()
        self._shift_pressed = interactor.GetShiftKey()
        self._ctrl_pressed = interactor.GetControlKey()

        if self._shift_pressed:
            # Shift + 좌클릭 = 패닝
            self._is_panning = True
            self.OnMiddleButtonDown()
        elif self._ctrl_pressed:
            # Ctrl + 좌클릭 = 줌
            self.StartDolly()
        else:
            # 좌클릭 = 회전
            self._is_rotating = True
            self.OnLeftButtonDown()

    def _on_left_button_up(self, obj, event):
        if self._is_panning:
            self.OnMiddleButtonUp()
            self._is_panning = False
        elif self._is_rotating:
            self.OnLeftButtonUp()
            self._is_rotating = False
        else:
            self.EndDolly()

        self._sync_camera()

    def _on_middle_button_down(self, obj, event):
        self._is_panning = True
        self.OnMiddleButtonDown()

    def _on_middle_button_up(self, obj, event):
        self._is_panning = False
        self.OnMiddleButtonUp()
        self._sync_camera()

    def _on_mouse_move(self, obj, event):
        if self._is_rotating or self._is_panning or self._ctrl_pressed:
            self.OnMouseMove()
            self._sync_camera()

    def _on_wheel_forward(self, obj, event):
        renderer = self.GetDefaultRenderer()
        if renderer:
            camera = renderer.GetActiveCamera()
            camera.Dolly(1.1)
            renderer.ResetCameraClippingRange()
            self.GetInteractor().Render()
            self._sync_camera()

    def _on_wheel_backward(self, obj, event):
        renderer = self.GetDefaultRenderer()
        if renderer:
            camera = renderer.GetActiveCamera()
            camera.Dolly(0.9)
            renderer.ResetCameraClippingRange()
            self.GetInteractor().Render()
            self._sync_camera()

    def _on_double_click(self, obj, event):
        interactor = self.GetInteractor()
        renderer = self.GetDefaultRenderer()

        if not renderer:
            return

        click_pos = interactor.GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(click_pos[0], click_pos[1], 0, renderer)
        pos = picker.GetPickPosition()

        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(pos)
        interactor.Render()
        self._sync_camera()
