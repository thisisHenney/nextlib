"""
CAD 스타일 마우스 인터랙션

- 좌클릭: 회전
- 좌클릭 + Shift: 패닝
- 좌클릭 + Ctrl: 줌 (돌리)
- 중클릭: 패닝
- 휠: 줌
- 더블클릭: 객체 선택 / 빈 공간 클릭 시 선택 해제
"""
import time
import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt


class CADInteractorStyle(vtkInteractorStyleTrackballCamera):
    DOUBLE_CLICK_TIME = 0.4
    DOUBLE_CLICK_DIST = 10

    def __init__(self, camera_controller=None, renderer=None, obj_manager=None):
        super().__init__()

        self.camera_controller = camera_controller
        self.obj_manager = obj_manager
        if renderer is not None:
            self.SetDefaultRenderer(renderer)

        self._is_rotating = False
        self._is_panning = False
        self._shift_pressed = False
        self._ctrl_pressed = False

        self._last_click_time = 0
        self._last_click_pos = (0, 0)

        self.AddObserver("LeftButtonPressEvent", self._on_left_button_down)
        self.AddObserver("LeftButtonReleaseEvent", self._on_left_button_up)
        self.AddObserver("MiddleButtonPressEvent", self._on_middle_button_down)
        self.AddObserver("MiddleButtonReleaseEvent", self._on_middle_button_up)
        self.AddObserver("MouseMoveEvent", self._on_mouse_move)
        self.AddObserver("MouseWheelForwardEvent", self._on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self._on_wheel_backward)

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

        current_time = time.time()
        current_pos = interactor.GetEventPosition()

        time_diff = current_time - self._last_click_time
        dx = current_pos[0] - self._last_click_pos[0]
        dy = current_pos[1] - self._last_click_pos[1]
        dist = (dx * dx + dy * dy) ** 0.5

        is_double_click = (time_diff < self.DOUBLE_CLICK_TIME and
                           dist < self.DOUBLE_CLICK_DIST)

        self._last_click_time = current_time
        self._last_click_pos = current_pos

        if is_double_click and not self._shift_pressed and not self._ctrl_pressed:
            self._handle_double_click()
            return

        if self._shift_pressed:
            self._is_panning = True
            self.OnMiddleButtonDown()
        elif self._ctrl_pressed:
            self.StartDolly()
        else:
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
        buttons = QApplication.mouseButtons()
        no_button = not bool(buttons & (Qt.MouseButton.LeftButton | Qt.MouseButton.MiddleButton | Qt.MouseButton.RightButton))
        if no_button and (self._is_rotating or self._is_panning or self._ctrl_pressed):
            self.reset_state()
            return

        if self._is_rotating or self._is_panning or self._ctrl_pressed:
            self.OnMouseMove()
            self._sync_camera()

    def _zoom(self, factor):
        renderer = self.GetDefaultRenderer()
        if not renderer:
            return
        camera = renderer.GetActiveCamera()
        if camera.GetParallelProjection():
            camera.SetParallelScale(camera.GetParallelScale() / factor)
        else:
            camera.Dolly(factor)
        renderer.ResetCameraClippingRange()
        self.GetInteractor().Render()
        self._sync_camera()

    def _on_wheel_forward(self, obj, event):
        self._zoom(1.1)

    def _on_wheel_backward(self, obj, event):
        self._zoom(0.9)

    def reset_state(self):
        """마우스가 위젯을 벗어나거나 포커스를 잃을 때 Python 플래그만 리셋
        (VTK C++ 메서드 직접 호출 금지 — segfault 방지)"""
        self._is_rotating = False
        self._is_panning = False
        self._shift_pressed = False
        self._ctrl_pressed = False

    def _handle_double_click(self):
        """더블클릭 처리: 객체 선택/해제 토글 또는 빈 공간 클릭 시 전체 해제"""
        interactor = self.GetInteractor()
        renderer = self.GetDefaultRenderer()

        if not renderer:
            return

        click_pos = interactor.GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(click_pos[0], click_pos[1], 0, renderer)
        picked_actor = picker.GetActor()

        if self.obj_manager:
            picked_id = None
            if picked_actor:
                for o in self.obj_manager._objects.values():
                    if o.actor == picked_actor and not o.removed:
                        picked_id = o.id
                        break

            if picked_id is not None:
                if picked_id in self.obj_manager.selected_ids:
                    self.obj_manager.toggle_selection(picked_id)
                else:
                    self.obj_manager.select_single(picked_id)
            else:
                self.obj_manager.clear_selection()
