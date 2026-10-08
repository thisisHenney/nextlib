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
import vtkmodules.all as vtk
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

        self._recenter_pivot()
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
        self._recenter_pivot()
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

    def _recenter_pivot(self):
        """회전/이동/확대 중심(카메라 초점)을 지금 화면 중심에 보이는 형상으로 옮긴다.

        VTK 는 초점을 중심으로 회전한다. 그런데 패닝하거나 커서 쪽으로 확대하고 나면 초점이
        형상에서 떨어진 허공에 남는다(떨어진 만큼 화면이 크게 휘돈다). 마우스 조작을 시작하는
        순간 화면 중심 아래의 형상 깊이로 초점을 다시 잡는다.

        카메라 위치와 보는 방향은 그대로 두고 초점만 같은 시선 위에서 앞뒤로 옮기므로,
        화면은 조금도 바뀌지 않는다.
        """
        renderer = self.GetDefaultRenderer()
        if not renderer:
            return
        camera = renderer.GetActiveCamera()
        width, height = renderer.GetSize()
        if width <= 0 or height <= 0:
            return

        target = self._zoom_target(renderer, camera, width // 2, height // 2)
        if target is None:
            return

        # 대상은 화면 중심의 시선 위에 있어야 한다. 깊이 버퍼의 오차로 벗어난 만큼은 버리고
        # 시선 위로 정사영해서, 카메라 방향이 틀어지지 않게 한다.
        pos = camera.GetPosition()
        direction = camera.GetDirectionOfProjection()
        along = sum((t - p) * d for t, p, d in zip(target, pos, direction))
        if along <= 1e-6:
            return      # 카메라 뒤쪽은 의미 없다
        camera.SetFocalPoint(*[p + d * along for p, d in zip(pos, direction)])
        renderer.ResetCameraClippingRange()

    @staticmethod
    def _display_to_world(renderer, x, y, z):
        """화면 좌표 (x, y) + 깊이 z -> 월드 좌표."""
        renderer.SetDisplayPoint(x, y, z)
        renderer.DisplayToWorld()
        w = renderer.GetWorldPoint()
        if w[3] == 0.0:
            return None
        return (w[0] / w[3], w[1] / w[3], w[2] / w[3])

    def _depth_of(self, renderer, point):
        """월드 좌표의 화면 깊이값(0~1)."""
        renderer.SetWorldPoint(point[0], point[1], point[2], 1.0)
        renderer.WorldToDisplay()
        return renderer.GetDisplayPoint()[2]

    def _zoom_target(self, renderer, camera, x, y):
        """확대의 기준점: 커서 아래에 실제로 그려진 형상 위의 점.

        깊이 버퍼를 한 픽셀만 읽어서 구한다(픽커보다 훨씬 싸다).

        커서 아래가 빈 배경이면 '화면에 보이는 형상 전체의 가운데'와 같은 깊이에서
        잡는다. 초점 깊이를 쓰면 안 된다 - 회전한 뒤 패닝하면 초점이 형상에서 멀리
        떨어진 허공에 남는데, 그 깊이를 기준으로 삼으면 계속 허공을 향해 당기게 된다.
        """
        window = renderer.GetRenderWindow()
        if window is not None:
            try:
                z = window.GetZbufferDataAtPoint(int(x), int(y))
            except (AttributeError, TypeError):
                z = None
            # 1.0 = 아무것도 안 그려진 배경(먼 평면). 0.0 은 가까운 평면인데 실제 형상이
            # 거기 닿을 일은 없고, 깊이를 못 읽었을 때 돌아오는 값이라 같이 거른다(받아들이면
            # 카메라 코앞을 기준으로 확대해서 확대가 거의 안 된다).
            if z is not None and 0.0 < z < 0.999999:
                point = self._display_to_world(renderer, x, y, z)
                if point is not None:
                    return point

        bounds = renderer.ComputeVisiblePropBounds()
        if bounds[0] <= bounds[1]:
            center = ((bounds[0] + bounds[1]) / 2.0,
                      (bounds[2] + bounds[3]) / 2.0,
                      (bounds[4] + bounds[5]) / 2.0)
        else:
            center = camera.GetFocalPoint()
        return self._display_to_world(renderer, x, y, self._depth_of(renderer, center))

    def _zoom(self, factor):
        """커서가 가리키는 형상 위의 점을 향해 확대/축소한다.

        초점(화면 중심)만 향해 당기면 두 가지가 어긋난다.
        - 보고 싶은 것을 패닝으로 가장자리에 옮겨 둔 상태에서는, 확대할수록 그게
          화면 밖으로 밀려나 오히려 더 못 보게 된다.
        - 화면을 회전한 뒤 패닝하면 초점이 형상에서 멀리 떨어진 허공에 남는다.
          그러면 카메라는 그 허공을 향해 다가가므로 형상은 거의 커지지 않고,
          계속 당기면 형상을 뚫고 지나가 버린다.

        그래서 기준점을 커서 아래의 실제 형상으로 잡고, 카메라 위치와 초점을 그
        점을 중심으로 1/factor 배 끌어당긴다. 기준점은 화면에서 제자리에 남고,
        초점도 형상 쪽으로 따라와서 몇 번을 확대해도 같은 비율로 계속 커진다.
        """
        renderer = self.GetDefaultRenderer()
        if not renderer:
            return
        camera = renderer.GetActiveCamera()
        interactor = self.GetInteractor()

        target = None
        if interactor is not None:
            x, y = interactor.GetEventPosition()
            target = self._zoom_target(renderer, camera, x, y)

        if target is None:
            # 기준점을 못 구하면 예전처럼 초점을 향해 당긴다.
            if camera.GetParallelProjection():
                camera.SetParallelScale(camera.GetParallelScale() / factor)
            else:
                camera.Dolly(factor)
        else:
            def pull(p):
                return [t + (v - t) / factor for v, t in zip(p, target)]

            camera.SetPosition(*pull(camera.GetPosition()))
            camera.SetFocalPoint(*pull(camera.GetFocalPoint()))
            if camera.GetParallelProjection():
                camera.SetParallelScale(camera.GetParallelScale() / factor)

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
