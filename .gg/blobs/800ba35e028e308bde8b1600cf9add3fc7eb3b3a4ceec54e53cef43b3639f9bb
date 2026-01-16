from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkInteractionWidgets import vtkBoxWidget2, vtkBoxRepresentation
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper


class PointProbeTool(QObject):
    center_moved = Signal(float, float, float)
    visibility_changed = Signal(bool)

    def __init__(self, parent=None, vtk_widget=None):
        super().__init__(parent)

        self.parent = parent
        self.vtk = vtk_widget
        self.renderer = vtk_widget.renderer
        self.interactor = vtk_widget.interactor

        self.rep = vtkBoxRepresentation()
        self.rep.SetPlaceFactor(1.0)

        self.box_widget = vtkBoxWidget2()
        self.box_widget.SetRepresentation(self.rep)
        self.box_widget.SetInteractor(self.interactor)
        self.box_widget.Off()
        self.box_widget.AddObserver("InteractionEvent", self._on_interact)

        self._visible = False
        self.selected_ids = self.vtk.obj_manager.selected_ids

        self._original_opacity = {}
        self._original_color = {}

        self._outline_actors = {}

        self._place_initial_box()

    def _place_initial_box(self):
        bounds = [0] * 6
        self.renderer.ComputeVisiblePropBounds(bounds)

        if bounds == [0, 0, 0, 0, 0, 0]:
            bounds = [-1, 1, -1, 1, -1, 1]

        self.rep.PlaceWidget(bounds)

    def _on_interact(self, caller, event):
        xmin, xmax, ymin, ymax, zmin, zmax = self.rep.GetBounds()
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2

        self.center_moved.emit(round(cx, 4), round(cy, 4), round(cz, 4))

    def _create_outline(self, actor):
        outline = vtkOutlineFilter()
        outline.SetInputData(actor.GetMapper().GetInput())

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(outline.GetOutputPort())

        outline_actor = vtkActor()
        outline_actor.SetMapper(mapper)

        outline_actor.GetProperty().SetColor(1.0, 1.0, 0.2)
        outline_actor.GetProperty().SetLineWidth(3)

        self.renderer.AddActor(outline_actor)
        self._outline_actors[id(actor)] = outline_actor

    def _remove_outline(self):
        for outline_actor in self._outline_actors.values():
            self.renderer.RemoveActor(outline_actor)
        self._outline_actors.clear()

    def _apply_highlight(self):
        if not self.selected_ids:
            return

        actors = list(self.renderer.GetActors())

        for actor in actors:
            aid = id(actor)
            prop = actor.GetProperty()

            if actor not in self._original_opacity:
                self._original_opacity[actor] = prop.GetOpacity()
            if actor not in self._original_color:
                self._original_color[actor] = prop.GetColor()

            if aid in self.selected_ids:
                prop.SetOpacity(1.0)
                prop.SetColor(1.0, 1.0, 0.4)

                self._create_outline(actor)
            else:
                prop.SetOpacity(0.15)

    def _restore_original(self):
        for actor, opacity in self._original_opacity.items():
            actor.GetProperty().SetOpacity(opacity)

        for actor, color in self._original_color.items():
            actor.GetProperty().SetColor(color)

        self._original_opacity.clear()
        self._original_color.clear()

        self._remove_outline()

    def show(self):
        if self._visible:
            return

        self._apply_highlight()

        self.box_widget.On()
        self._visible = True
        self.visibility_changed.emit(True)

        self.renderer.GetRenderWindow().Render()

    def hide(self):
        if not self._visible:
            return

        self.box_widget.Off()
        self._visible = False
        self.visibility_changed.emit(False)

        self._restore_original()

        self.renderer.GetRenderWindow().Render()

    def is_visible(self):
        return self.box_widget.GetEnabled() == 1
