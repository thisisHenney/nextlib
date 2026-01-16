from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera

class CADInteractorStyle(vtkInteractorStyleTrackballCamera):
    def __init__(self, viewer=None, renderer=None):
        super().__init__()
        if renderer is not None:
            self.SetDefaultRenderer(renderer)
        self.viewer = viewer

        self.AddObserver("LeftButtonPressEvent", self.on_left_button_down)
        self.AddObserver("LeftButtonReleaseEvent", self.on_left_button_up)
        self.AddObserver("MiddleButtonPressEvent", self.on_middle_button_down)
        self.AddObserver("MiddleButtonReleaseEvent", self.on_middle_button_up)
        self.AddObserver("MouseMoveEvent", self.on_mouse_move)
        self.AddObserver("MouseWheelForwardEvent", self.on_wheel_forward)
        self.AddObserver("MouseWheelBackwardEvent", self.on_wheel_backward)
        self.AddObserver("LeftButtonDoubleClickEvent", self.on_double_click)

        self.is_rotating = False
        self.is_panning = False
        self.shift_pressed = False
        self.ctrl_pressed = False

    def _sync_camera(self):
        if self.viewer is not None and self.viewer.registry:
            self.viewer.registry.notify_camera_changed(self.viewer)

    def on_left_button_down(self, obj, event):
        iren = self.GetInteractor()
        self.shift_pressed = iren.GetShiftKey()
        self.ctrl_pressed = iren.GetControlKey()

        if self.shift_pressed:
            self.is_panning = True
            self.OnMiddleButtonDown()
        elif self.ctrl_pressed:
            self.StartDolly()
        else:
            self.is_rotating = True
            self.OnLeftButtonDown()
        return

    def on_left_button_up(self, obj, event):
        if self.is_panning:
            self.OnMiddleButtonUp()
            self.is_panning = False
        elif self.is_rotating:
            self.OnLeftButtonUp()
            self.is_rotating = False
        else:
            self.EndDolly()

        self._sync_camera()
        return

    def on_middle_button_down(self, obj, event):
        self.is_panning = True
        self.OnMiddleButtonDown()
        return

    def on_middle_button_up(self, obj, event):
        self.is_panning = False
        self.OnMiddleButtonUp()
        self._sync_camera()
        return

    def on_mouse_move(self, obj, event):
        if self.is_rotating or self.is_panning or self.ctrl_pressed:
            self.OnMouseMove()
            self._sync_camera()
        return

    def on_wheel_forward(self, obj, event):
        camera = self.GetDefaultRenderer().GetActiveCamera()
        camera.Dolly(1.1)
        self.GetDefaultRenderer().ResetCameraClippingRange()
        self.GetInteractor().Render()

        self._sync_camera()
        return

    def on_wheel_backward(self, obj, event):
        camera = self.GetDefaultRenderer().GetActiveCamera()
        camera.Dolly(0.9)
        self.GetDefaultRenderer().ResetCameraClippingRange()
        self.GetInteractor().Render()

        self._sync_camera()
        return

    def on_double_click(self, obj, event):
        click_pos = self.GetInteractor().GetEventPosition()
        picker = vtk.vtkPropPicker()
        picker.Pick(click_pos[0], click_pos[1], 0, self.GetDefaultRenderer())
        pos = picker.GetPickPosition()
        camera = self.GetDefaultRenderer().GetActiveCamera()
        camera.SetFocalPoint(pos)
        self.GetInteractor().Render()
        self._sync_camera()