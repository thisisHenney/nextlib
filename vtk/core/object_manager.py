"""
VTK 객체 관리자

사용 예시:
    manager = ObjectManager(renderer)

    # 객체 추가
    obj_id = manager.add(actor, name="cube1", group="geometry")

    # 개별 접근 (ID 또는 이름)
    manager.object(0).hide()
    manager.object("cube1").color(255, 0, 0).opacity(0.5)

    # 그룹 접근
    manager.group("geometry").show().style("wireframe")

    # 전체 접근
    manager.all().opacity(0.8)

    # 배치 모드 (여러 객체 추가 시 성능 최적화)
    with manager.batch():
        for i in range(100):
            manager.add(actor, name=f"obj_{i}")
"""
from typing import Dict, List, Optional, Union, Set
from contextlib import contextmanager
from PySide6.QtCore import Signal, QObject
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkActor, vtkPolyDataMapper
from vtkmodules.vtkFiltersSources import vtkCubeSource
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter

from .object_data import ObjectData
from .object_accessor import ObjectAccessor, GroupAccessor


class ObjectManager(QObject):
    """VTK 객체 생명주기 관리자"""

    # 시그널
    selection_changed = Signal(dict)
    object_added = Signal(int, str)      # id, name
    object_removed = Signal(int, str)    # id, name

    def __init__(self, renderer: vtkRenderer):
        super().__init__()

        self.renderer = renderer
        self._objects: Dict[int, ObjectData] = {}
        self._next_id = 0

        # 선택 관련
        self._selected_ids: Set[int] = set()
        self._outline_actors: Dict[int, vtkActor] = {}
        self._bbox_actor: Optional[vtkActor] = None

        # 선택 시각화 옵션
        self._show_individual_outlines = True  # 개별 객체 outline 표시 여부

        # 피커
        self._picker = None

        # 배치 모드
        self._batch_mode = False
        self._pending_render = False

    # ===== 속성 =====

    @property
    def selected_ids(self) -> Set[int]:
        """선택된 객체 ID 집합"""
        return self._selected_ids.copy()

    @property
    def show_individual_outlines(self) -> bool:
        """개별 객체 outline 표시 여부"""
        return self._show_individual_outlines

    @show_individual_outlines.setter
    def show_individual_outlines(self, value: bool):
        """개별 객체 outline 표시 여부 설정"""
        self._show_individual_outlines = value
        # 현재 선택이 있으면 시각화 업데이트
        if self._selected_ids:
            self._update_selection_visual()

    # ===== 배치 모드 =====

    @contextmanager
    def batch(self):
        """배치 모드: 여러 객체 추가 시 렌더링을 마지막에 한번만 수행

        Example:
            with manager.batch():
                for file in files:
                    manager.add(load_stl(file))
            # 여기서 한번만 렌더링됨
        """
        self._batch_mode = True
        self._pending_render = False
        try:
            yield
        finally:
            self._batch_mode = False
            if self._pending_render:
                self._render()
            self._pending_render = False

    # ===== 체이닝 접근 API =====

    def object(self, identifier: Union[int, str]) -> Optional[ObjectAccessor]:
        """ID 또는 이름으로 단일 객체 접근

        Args:
            identifier: 객체 ID(int) 또는 이름(str)

        Returns:
            ObjectAccessor 또는 None
        """
        obj = self._find_object(identifier)
        if obj:
            return ObjectAccessor(self, obj)
        return None

    def group(self, group_name: str) -> GroupAccessor:
        """그룹 이름으로 복수 객체 접근

        Args:
            group_name: 그룹 이름

        Returns:
            GroupAccessor (빈 그룹이어도 반환)
        """
        objects = [o for o in self._objects.values()
                   if o.group == group_name and not o.removed]
        return GroupAccessor(self, objects)

    def all(self) -> GroupAccessor:
        """모든 객체 접근"""
        objects = [o for o in self._objects.values() if not o.removed]
        return GroupAccessor(self, objects)

    def selected(self) -> GroupAccessor:
        """선택된 객체들 접근"""
        objects = [self._objects[id] for id in self._selected_ids
                   if id in self._objects and not self._objects[id].removed]
        return GroupAccessor(self, objects)

    # ===== 기본 CRUD =====

    def add(self, actor: vtkActor, name: str = "", group: str = "default") -> int:
        """객체 추가

        Args:
            actor: VTK Actor
            name: 객체 이름 (비어있으면 자동 생성)
            group: 그룹 이름

        Returns:
            객체 ID
        """
        if actor is None:
            return -1

        obj_id = self._next_id
        self._next_id += 1

        if not name:
            name = f"object_{obj_id}"

        obj = ObjectData(
            id=obj_id,
            actor=actor,
            name=name,
            group=group
        )
        self._objects[obj_id] = obj

        # 기본 스타일 적용
        prop = actor.GetProperty()
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()

        self.renderer.AddActor(actor)

        # 첫 번째 객체면 카메라 리셋
        active_count = sum(1 for o in self._objects.values() if not o.removed)
        if active_count == 1:
            self.renderer.ResetCamera()

        self.object_added.emit(obj_id, name)
        return obj_id

    def get(self, obj_id: int) -> Optional[ObjectData]:
        """ID로 ObjectData 직접 조회"""
        obj = self._objects.get(obj_id)
        if obj and not obj.removed:
            return obj
        return None

    def remove(self, obj_id: int) -> bool:
        """객체 삭제 (soft delete)"""
        obj = self.get(obj_id)
        if not obj:
            return False

        obj.removed = True
        self.renderer.RemoveActor(obj.actor)

        # 관련 시각 효과 제거
        self._remove_outline(obj_id)
        self._selected_ids.discard(obj_id)

        self._render()
        self.object_removed.emit(obj_id, obj.name)
        return True

    def get_all(self, include_removed: bool = False) -> List[ObjectData]:
        """모든 객체 조회"""
        if include_removed:
            return list(self._objects.values())
        return [o for o in self._objects.values() if not o.removed]

    # ===== 검색 =====

    def _find_object(self, identifier: Union[int, str]) -> Optional[ObjectData]:
        """ID 또는 이름으로 객체 찾기"""
        if isinstance(identifier, int):
            return self.get(identifier)
        else:
            # 이름으로 검색
            for obj in self._objects.values():
                if obj.name == identifier and not obj.removed:
                    return obj
            return None

    def find_by_name(self, name: str) -> Optional[ObjectData]:
        """이름으로 객체 검색"""
        for obj in self._objects.values():
            if obj.name == name and not obj.removed:
                return obj
        return None

    def find_by_group(self, group: str) -> List[ObjectData]:
        """그룹으로 객체 검색"""
        return [o for o in self._objects.values()
                if o.group == group and not o.removed]

    # ===== 선택 =====

    def select_single(self, obj_id: int):
        """단일 선택"""
        self._selected_ids = {obj_id}
        self._update_selection_visual()

    def select_multiple(self, obj_ids: List[int]):
        """복수 선택"""
        self._selected_ids = set(obj_ids)
        self._update_selection_visual()

    def add_selection(self, obj_id: int):
        """선택에 추가"""
        self._selected_ids.add(obj_id)
        self._update_selection_visual()

    def toggle_selection(self, obj_id: int):
        """선택 토글"""
        if obj_id in self._selected_ids:
            self._selected_ids.discard(obj_id)
        else:
            self._selected_ids.add(obj_id)
        self._update_selection_visual()

    def clear_selection(self):
        """선택 해제"""
        self._selected_ids.clear()
        self._update_selection_visual()

    def get_selected_ids(self) -> List[int]:
        """선택된 ID 목록"""
        return list(self._selected_ids)

    # ===== 카메라/포커스 =====

    def focus_on(self, obj_id: int):
        """객체에 카메라 포커스"""
        obj = self.get(obj_id)
        if not obj:
            return

        camera = self.renderer.GetActiveCamera()
        bounds = obj.actor.GetBounds()

        cx = (bounds[0] + bounds[1]) / 2
        cy = (bounds[2] + bounds[3]) / 2
        cz = (bounds[4] + bounds[5]) / 2

        size = max(bounds[1]-bounds[0], bounds[3]-bounds[2], bounds[5]-bounds[4])
        dist = size * 2.5

        camera.SetFocalPoint(cx, cy, cz)
        camera.SetPosition(cx, cy - dist, cz)
        self.renderer.ResetCameraClippingRange()
        self._render()

    # ===== 피킹 =====

    def set_picking_callback(self, interactor):
        """마우스 피킹 콜백 설정"""
        import vtkmodules.vtkRenderingCore as vrc
        self._picker = vrc.vtkPropPicker()

        def on_click(obj, evt):
            ctrl = interactor.GetControlKey()
            shift = interactor.GetShiftKey()

            # Ctrl 또는 Shift가 눌렸을 때만 선택 처리
            if not (ctrl or shift):
                return

            x, y = interactor.GetEventPosition()
            self._picker.Pick(x, y, 0, self.renderer)
            picked = self._picker.GetActor()

            picked_id = None
            if picked:
                for o in self._objects.values():
                    if o.actor == picked and not o.removed:
                        picked_id = o.id
                        break

            if picked_id is not None:
                if ctrl:
                    self.toggle_selection(picked_id)
                elif shift:
                    self.add_selection(picked_id)
            else:
                # 빈 공간 Ctrl/Shift 클릭: 선택 해제
                self.clear_selection()

        def on_double_click(obj, evt):
            x, y = interactor.GetEventPosition()
            self._picker.Pick(x, y, 0, self.renderer)
            picked = self._picker.GetActor()

            picked_id = None
            if picked:
                for o in self._objects.values():
                    if o.actor == picked and not o.removed:
                        picked_id = o.id
                        break

            if picked_id is not None:
                # 더블클릭: 단일 선택 (포커스 없음)
                self.select_single(picked_id)
            else:
                # 빈 공간 더블클릭: 선택 해제
                self.clear_selection()

        def on_key(obj, evt):
            key = interactor.GetKeySym()
            if key == "Delete":
                for sid in list(self._selected_ids):
                    self.remove(sid)
                self.clear_selection()

        interactor.AddObserver("LeftButtonPressEvent", on_click)
        # 더블클릭은 CADInteractorStyle에서 처리
        interactor.AddObserver("KeyPressEvent", on_key)

    # ===== 스타일 적용 =====

    def _apply_style(self, obj: ObjectData, style: str):
        """객체에 뷰 스타일 적용"""
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

        elif style in ("transparent", "transparent surface"):
            prop.SetRepresentationToSurface()
            prop.EdgeVisibilityOff()
            prop.SetOpacity(0.4)

    def _effect_highlight(self, obj: ObjectData):
        """하이라이트 효과"""
        prop = obj.actor.GetProperty()
        prop.EdgeVisibilityOn()
        prop.SetEdgeColor(1, 1, 0)
        prop.SetLineWidth(2.5)

    # ===== 선택 시각화 =====

    def _update_selection_visual(self):
        """선택 상태 시각화 업데이트"""
        # 기존 아웃라인 제거
        for actor in list(self._outline_actors.values()):
            try:
                self.renderer.RemoveActor(actor)
            except:
                pass
        self._outline_actors.clear()

        # bbox 제거
        if self._bbox_actor:
            try:
                self.renderer.RemoveActor(self._bbox_actor)
            except:
                pass
            self._bbox_actor = None

        # 선택된 것이 있을 때만 투명도 조절
        if self._selected_ids:
            for obj in self._objects.values():
                if obj.removed:
                    continue

                prop = obj.actor.GetProperty()
                if obj.id in self._selected_ids:
                    prop.SetOpacity(1.0)
                    # 개별 outline 표시 옵션이 켜져 있을 때만 추가
                    if self._show_individual_outlines:
                        self._add_outline(obj)
                else:
                    prop.SetOpacity(0.25)

            # 선택된 객체들의 bbox 표시
            self._add_selection_bbox()
        else:
            # 선택이 없으면 모든 객체 원래 투명도로 복원
            for obj in self._objects.values():
                if obj.removed:
                    continue
                prop = obj.actor.GetProperty()
                prop.SetOpacity(obj.opacity)

        # 시그널 발신
        info = {
            "selected_ids": list(self._selected_ids),
            "selected_objects": [
                {"id": o.id, "name": o.name, "group": o.group}
                for o in self._objects.values()
                if o.id in self._selected_ids
            ]
        }
        self.selection_changed.emit(info)
        self._render()

    def _add_outline(self, obj: ObjectData):
        """객체에 아웃라인 추가"""
        try:
            mapper = obj.actor.GetMapper()
            if mapper is None:
                return

            input_data = mapper.GetInput()
            if input_data is None:
                return

            outline = vtkOutlineFilter()
            outline.SetInputData(input_data)
            outline.Update()

            o_mapper = vtkPolyDataMapper()
            o_mapper.SetInputConnection(outline.GetOutputPort())

            o_actor = vtkActor()
            o_actor.SetMapper(o_mapper)
            o_actor.GetProperty().SetColor(1.0, 0.0, 0.0)
            o_actor.GetProperty().SetLineWidth(2.0)

            # 원본 객체의 변환 정보 복사
            o_actor.SetPosition(obj.actor.GetPosition())
            o_actor.SetOrientation(obj.actor.GetOrientation())
            o_actor.SetScale(obj.actor.GetScale())
            o_actor.SetOrigin(obj.actor.GetOrigin())
            if obj.actor.GetUserMatrix():
                o_actor.SetUserMatrix(obj.actor.GetUserMatrix())

            self.renderer.AddActor(o_actor)
            self._outline_actors[obj.id] = o_actor
        except Exception:
            pass

    def _remove_outline(self, obj_id: int):
        """아웃라인 제거"""
        if obj_id in self._outline_actors:
            try:
                self.renderer.RemoveActor(self._outline_actors[obj_id])
            except:
                pass
            del self._outline_actors[obj_id]

    def _add_selection_bbox(self):
        """선택된 객체들의 바운딩 박스 추가"""
        min_x, min_y, min_z = float("inf"), float("inf"), float("inf")
        max_x, max_y, max_z = float("-inf"), float("-inf"), float("-inf")

        for sid in self._selected_ids:
            obj = self.get(sid)
            if not obj:
                continue

            try:
                bounds = obj.actor.GetBounds()
                min_x = min(min_x, bounds[0])
                max_x = max(max_x, bounds[1])
                min_y = min(min_y, bounds[2])
                max_y = max(max_y, bounds[3])
                min_z = min(min_z, bounds[4])
                max_z = max(max_z, bounds[5])
            except:
                continue

        # 유효한 bounds인지 확인
        if min_x >= max_x or min_y >= max_y or min_z >= max_z:
            return

        # 최소 크기 보장
        for vals in [(min_x, max_x), (min_y, max_y), (min_z, max_z)]:
            if vals[1] - vals[0] < 1e-6:
                mid = (vals[0] + vals[1]) / 2
                vals = (mid - 0.01, mid + 0.01)

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
        self._bbox_actor = bbox_actor

    def _render(self):
        """렌더링 요청 (배치 모드면 지연)"""
        if self._batch_mode:
            self._pending_render = True
            return

        try:
            rw = self.renderer.GetRenderWindow()
            if rw:
                rw.Render()
        except:
            pass
