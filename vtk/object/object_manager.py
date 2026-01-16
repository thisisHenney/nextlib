import os
from pathlib import Path
from typing import Dict, List, Optional
from vtkmodules.vtkRenderingCore import (
    vtkRenderer, vtkActor, vtkPolyDataMapper
)
from vtkmodules.vtkFiltersSources import vtkCubeSource
from PySide6.QtCore import Signal, QObject
from nextlib.vtk.object.object_data import ObjectData


class ObjectManager(QObject):
    selection_changed = Signal(dict)

    def __init__(self, renderer: vtkRenderer):
        super().__init__()

        self.renderer = renderer
        self.objects: Dict[int, ObjectData] = {}
        self.next_id = 0

        self.selected_ids = set()
        self.outline_actors = {}

        self.bbox_actor = None
        self.bbox_actors = {}

        self.picker = None

    def add(self, actor: vtkActor, group: int = 0, name: str="") -> int:
        if actor is None:
            return -1

        obj_id = self.next_id
        self.next_id += 1

        if not name:
            name = f"object_{obj_id}"

        obj = ObjectData(
            id=obj_id,
            actor=actor,
            group=group,
            name=name
        )
        self.objects[obj_id] = obj

        prop = actor.GetProperty()
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()

        self.renderer.AddActor(actor)
        if len(self.objects) == 1:
            self.renderer.ResetCamera()

        return obj_id

    def get(self, obj_id: int) -> Optional[ObjectData]:
        if not (0 <= obj_id < self.next_id):
            return None

        obj = self.objects.get(obj_id)
        if obj and not obj.removed:
            return obj

        return None

    def get_id_by_name(self, name: str) -> Optional[int]:
        for obj in self.objects.values():
            if obj.removed:
                continue
            if obj.name == name:
                return obj.id
        return None

    def get_all_objects(self, include_removed=False):
        if include_removed:
            return list(self.objects.values())
        return [o for o in self.objects.values() if not o.removed]

    def remove(self, obj_id: int):
        obj = self.get(obj_id)
        if not obj:
            return

        obj.removed = True

        self.renderer.RemoveActor(obj.actor)

        if obj.id in self.outline_actors:
            try:
                self.renderer.RemoveActor(self.outline_actors[obj.id])
            except Exception:
                pass
            self.outline_actors.pop(obj.id, None)

        if obj.id in self.bbox_actors:
            try:
                self.renderer.RemoveActor(self.bbox_actors[obj.id])
            except Exception:
                pass
            self.bbox_actors.pop(obj.id, None)

        if obj.id in self.selected_ids:
            self.selected_ids.discard(obj.id)

        if hasattr(self, "bbox_actor") and self.bbox_actor:
            try:
                self.renderer.RemoveActor(self.bbox_actor)
            except Exception:
                pass
            self.bbox_actor = None

        self.renderer.GetRenderWindow().Render()

    def set_group(self, obj_id: int, group: int):
        obj = self.get(obj_id)
        if obj is None:
            obj.group = group

    def set_name(self, obj_id: int, name: str):
        obj = self.get(obj_id)
        if obj is None:
            obj.name = name

    def set_path(self, obj_id: int, path: str):
        obj = self.get(obj_id)
        if obj is None:
            obj.path = path

    def apply(self, key: str, value=None, obj_id=None, group=None):
        target_ids = set()

        if obj_id is not None:
            if isinstance(obj_id, int):
                target_ids.add(obj_id)
            else:
                target_ids.update(obj_id)

        if group is not None:
            if isinstance(group, int):
                group = [group]
            for g in group:
                for o in self.objects.values():
                    if o.group == g and not o.removed:
                        target_ids.add(o.id)

        for oid in target_ids:
            obj = self.get(oid)
            if not obj or obj.removed:
                continue

            prop = obj.actor.GetProperty()

            if key == "visible":
                obj.actor.SetVisibility(bool(value))

            elif key == "opacity":
                prop.SetOpacity(float(value))

            elif key == "color":
                r, g, b = value[0] / 255.0, value[1] / 255.0, value[2] / 255.0
                prop.SetColor(r, g, b)

            elif key == "style":
                self._apply_style(obj, value)

            elif key == "highlight":
                self._effect_highlight(obj)

            elif key == "outline":
                self._effect_outline(obj)

            elif key == "bbox":
                self._effect_bbox(obj)

            elif key == "duplicate":
                self._effect_duplicate(obj)

            elif key == "remove":
                self._effect_remove(obj)

        self.renderer.GetRenderWindow().Render()

    def _apply_style(self, obj, style):
        style = style.lower()
        prop = obj.actor.GetProperty()

        if style == "wireframe":
            prop.SetRepresentationToWireframe()
            prop.EdgeVisibilityOff()

        elif style == "surface":
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetOpacity(1.0)

        elif style == "surface with edge":
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOn()
            prop.SetLineWidth(1.2)

        elif style == "transparent surface":
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetOpacity(0.4)

    def clear_selection(self):
        self.selected_ids.clear()
        self.update_selection_visual()

    def select_single(self, obj_id):
        self.selected_ids = {obj_id}
        self.update_selection_visual()

    def add_selection(self, obj_id):
        self.selected_ids.add(obj_id)
        self.update_selection_visual()

    def toggle_selection(self, obj_id):
        if obj_id in self.selected_ids:
            self.selected_ids.remove(obj_id)
        else:
            self.selected_ids.add(obj_id)
        self.update_selection_visual()

    def update_selection_visual(self):
        if hasattr(self, "bbox_actors"):
            for a in list(self.bbox_actors.values()):
                try:
                    self.renderer.RemoveActor(a)
                except:
                    pass
            self.bbox_actors.clear()

        for a in list(self.outline_actors.values()):
            try:
                self.renderer.RemoveActor(a)
            except:
                pass
        self.outline_actors.clear()

        for obj in self.objects.values():
            if obj.removed:
                continue

            prop = obj.actor.GetProperty()

            if obj.id in self.selected_ids:
                prop.SetOpacity(1.0)
                self._add_outline(obj)
            else:
                prop.SetOpacity(0.25)

        if self.selected_ids:
            sid = next(iter(self.selected_ids))
            self.active_id = sid
            self.active_object = self.get(sid)
        else:
            self.active_id = None
            self.active_object = None

        if hasattr(self, "bbox_actor") and self.bbox_actor:
            try:
                self.renderer.RemoveActor(self.bbox_actor)
            except:
                pass
            self.bbox_actor = None

        if not self.selected_ids:
            info = {
                "selected_ids": [],
                "selected_objects": []
            }
            self.selection_changed.emit(info)
            self.renderer.GetRenderWindow().Render()
            return

        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")

        for sid in self.selected_ids:
            obj = self.get(sid)
            if not obj:
                continue

            try:
                mapper = obj.actor.GetMapper()
                poly = mapper.GetInput()
                bx = poly.GetBounds()
            except Exception:
                continue

            min_x = min(min_x, bx[0])
            max_x = max(max_x, bx[1])
            min_y = min(min_y, bx[2])
            max_y = max(max_y, bx[3])
            min_z = min(min_z, bx[4])
            max_z = max(max_z, bx[5])

        if not all(map(lambda v: v < float("inf") and v > float("-inf"),
                       [min_x, max_x, min_y, max_y, min_z, max_z])):
            # print("[!!] BBox bounds invalid — skipping BBox")
            return

        if max_x - min_x < 1e-6:
            max_x += 0.01
            min_x -= 0.01
        if max_y - min_y < 1e-6:
            max_y += 0.01
            min_y -= 0.01
        if max_z - min_z < 1e-6:
            max_z += 0.01
            min_z -= 0.01

        cube = vtkCubeSource()
        cube.SetBounds(min_x, max_x, min_y, max_y, min_z, max_z)
        cube.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())

        bbox_actor = vtkActor()
        bbox_actor.SetMapper(mapper)
        bbox_actor.GetProperty().SetColor(1, 0, 0)
        bbox_actor.GetProperty().SetOpacity(0.25)
        bbox_actor.GetProperty().SetRepresentationToWireframe()
        bbox_actor.GetProperty().SetLineWidth(2)

        self.renderer.AddActor(bbox_actor)
        self.bbox_actor = bbox_actor

        info = {
            "selected_ids": list(self.selected_ids),
            "selected_objects": [
                {
                    "id": o.id,
                    "name": o.name,
                    "group": o.group,
                    "path": o.path
                }
                for o in self.objects.values()
                if o.id in self.selected_ids
            ]
        }

        self.selection_changed.emit(info)

        try:
            self.renderer.GetRenderWindow().Render()
        except:
            pass

    def _add_outline(self, obj):
        try:
            if obj.id in self.outline_actors:
                old = self.outline_actors.pop(obj.id)
                try:
                    self.renderer.RemoveActor(old)
                except Exception:
                    pass
        except Exception:
            pass

        mapper = None
        try:
            mapper = obj.actor.GetMapper()
        except Exception:
            mapper = None

        if mapper is None:
            return

        input_data = None
        input_conn = None
        try:
            input_data = mapper.GetInput()
        except Exception:
            input_data = None

        if input_data is None:
            try:
                input_conn = mapper.GetInputConnection(0, 0)
            except Exception:
                input_conn = None

        if input_data is None and input_conn is None:
            return

        from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        outline = vtkOutlineFilter()
        if input_data is not None:
            try:
                outline.SetInputData(input_data)
            except Exception:
                if input_conn is not None:
                    outline.SetInputConnection(input_conn)
        else:
            outline.SetInputConnection(input_conn)

        outline.Update()

        o_mapper = vtkPolyDataMapper()
        o_mapper.SetInputConnection(outline.GetOutputPort())

        o_actor = vtkActor()
        o_actor.SetMapper(o_mapper)

        o_actor.GetProperty().SetColor(1.0, 0.0, 0.0)
        o_actor.GetProperty().SetLineWidth(2.0)
        o_actor.GetProperty().SetRepresentationToWireframe()
        o_actor.GetProperty().SetOpacity(1.0)

        try:
            self.renderer.AddActor(o_actor)
            self.outline_actors[obj.id] = o_actor
        except Exception:
            pass

    def _effect_highlight(self, obj):
        prop = obj.actor.GetProperty()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(1, 1, 0)
        prop.SetLineWidth(2.5)

    def _effect_outline(self, obj):
        from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        poly = obj.actor.GetMapper().GetInput()
        outline = vtkOutlineFilter()
        outline.SetInputData(poly)
        outline.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(outline.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)
        actor.GetProperty().SetLineWidth(2.2)

        self.renderer.AddActor(actor)
        self.outline_actors[obj.id] = actor

    def _effect_bbox(self, obj):
        from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor

        bounds = obj.actor.GetBounds()
        cube = vtkCubeAxesActor()
        cube.SetBounds(bounds)
        cube.GetProperty().SetColor(0, 1, 0)

        self.renderer.AddActor(cube)
        self.bbox_actors[obj.id] = cube

    def _effect_remove(self, obj):
        obj.removed = True
        self.renderer.RemoveActor(obj.actor)

        if obj.id in self.outline_actors:
            self.renderer.RemoveActor(self.outline_actors[obj.id])

        if obj.id in self.bbox_actors:
            self.renderer.RemoveActor(self.bbox_actors[obj.id])

    def _effect_duplicate(self, obj):
        from vtkmodules.vtkCommonDataModel import vtkPolyData
        from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor

        poly_orig = obj.actor.GetMapper().GetInput()
        poly_new = vtkPolyData()
        poly_new.DeepCopy(poly_orig)

        mapper = vtkPolyDataMapper()
        mapper.SetInputData(poly_new)

        actor = vtkActor()
        actor.SetMapper(mapper)

        x, y, z = obj.actor.GetPosition()
        actor.SetPosition(x + 5, y, z)

        new_id = self.add(actor, group=obj.group)

    def set_picking_callback(self, interactor):
        import vtkmodules.vtkRenderingCore as vrc
        self.picker = vrc.vtkPropPicker()

        def on_click(obj, evt):
            ctrl = interactor.GetControlKey()
            shift = interactor.GetShiftKey()
            x, y = interactor.GetEventPosition()

            self.picker.Pick(x, y, 0, self.renderer)
            picked = self.picker.GetActor()

            picked_id = None
            if picked:
                for o in self.objects.values():
                    if o.actor == picked:
                        picked_id = o.id
                        break

            if picked_id is not None:
                if ctrl:
                    self.toggle_selection(picked_id)
                elif shift:
                    self.add_selection(picked_id)
                else:
                    pass
            else:
                if ctrl or shift:
                    self.clear_selection()

        def on_double_click(obj, evt):
            if self.selected_ids:
                sid = next(iter(self.selected_ids))
                self.focus_on(sid)

        def on_key(obj, evt):
            key = interactor.GetKeySym()
            if key == "Remove":
                for sid in list(self.selected_ids):
                    self.apply("remove", obj_id=sid)
                self.clear_selection()

        interactor.AddObserver("LeftButtonPressEvent", on_click)
        interactor.AddObserver("LeftButtonDoubleClickEvent", on_double_click)
        interactor.AddObserver("KeyPressEvent", on_key)

    def focus_on(self, obj_id):
        obj = self.get(obj_id)
        if not obj:
            return

        cam = self.renderer.GetActiveCamera()
        b = obj.actor.GetBounds()

        cx = (b[0]+b[1])/2
        cy = (b[2]+b[3])/2
        cz = (b[4]+b[5])/2

        size = max(b[1]-b[0], b[3]-b[2], b[5]-b[4])
        dist = size * 2.5

        cam.SetFocalPoint(cx, cy, cz)
        cam.SetPosition(cx, cy - dist, cz)
        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()
