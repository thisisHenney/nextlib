"""
Point Probe Tool - 선택된 객체의 위치를 확인하고 조작하는 도구

사용 예시:
    # VtkWidgetBase에서 사용
    widget.add_tool("point_probe")  # 툴바에 추가
    widget.show_tool("point_probe")  # 도구 표시
    widget.hide_tool("point_probe")  # 도구 숨김

    # 직접 사용
    probe = PointProbeTool(vtk_widget)
    probe.show()
    probe.center_moved.connect(lambda x, y, z: print(f"Center: {x}, {y}, {z}"))
"""
from typing import Optional, Dict, TYPE_CHECKING
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkInteractionWidgets import vtkBoxWidget2, vtkBoxRepresentation
from vtkmodules.vtkFiltersModeling import vtkOutlineFilter
from vtkmodules.vtkRenderingCore import vtkActor, vtkPolyDataMapper
from vtkmodules.vtkCommonTransforms import vtkTransform

if TYPE_CHECKING:
    from ..vtk_widget_base import VtkWidgetBase


class PointProbeTool(QObject):
    """
    선택된 객체의 중심점을 확인하고 조작하는 도구

    - vtkBoxWidget2를 사용하여 인터랙티브 박스 표시
    - 선택된 객체 하이라이트
    - 박스 이동 시 중심 좌표 시그널 발생
    """

    # 시그널
    center_moved = Signal(float, float, float)  # 박스 중심이 이동할 때 (x, y, z)
    visibility_changed = Signal(bool)  # 가시성이 변경될 때

    def __init__(self, vtk_widget: "VtkWidgetBase", parent: Optional[QObject] = None):
        super().__init__(parent)

        self._vtk_widget = vtk_widget
        self._renderer = vtk_widget.renderer
        self._interactor = vtk_widget.interactor

        # Box Widget 설정
        self._rep = vtkBoxRepresentation()
        self._rep.SetPlaceFactor(1.0)

        self._box_widget = vtkBoxWidget2()
        self._box_widget.SetRepresentation(self._rep)
        self._box_widget.SetInteractor(self._interactor)
        self._box_widget.Off()
        self._box_widget.AddObserver("InteractionEvent", self._on_interact)

        self._visible = False

        # 원본 상태 저장
        self._original_opacity: Dict[int, float] = {}
        self._original_color: Dict[int, tuple] = {}

        # 아웃라인 액터들
        self._outline_actors: Dict[int, vtkActor] = {}

        # 저장된 박스 상태 (None이면 초기 위치 사용)
        self._saved_bounds: Optional[list] = None
        self._saved_transform: Optional[vtkTransform] = None  # 저장된 변환 (회전 포함)
        self._saved_selection_ids: Optional[set] = None  # 저장된 위치에 해당하는 선택 객체
        self._box_size = 1.0  # 기본 박스 크기
        self._probe_scale = 1.4  # 프로브 크기 배율 (40% 확장)

        # 초기 박스 배치
        self._place_initial_box()

    @property
    def is_visible(self) -> bool:
        """현재 가시성 상태"""
        return self._visible

    def _place_initial_box(self):
        """초기 박스 위치 설정"""
        bounds = [0] * 6
        self._renderer.ComputeVisiblePropBounds(bounds)

        # 빈 씬인 경우 기본 bounds 사용
        if bounds == [0, 0, 0, 0, 0, 0] or all(b == 1.0 for b in bounds):
            bounds = [-1, 1, -1, 1, -1, 1]

        self._rep.PlaceWidget(bounds)

    def _on_interact(self, caller, event):
        """박스 인터랙션 이벤트 핸들러"""
        bounds = list(self._rep.GetBounds())
        xmin, xmax, ymin, ymax, zmin, zmax = bounds

        # 현재 위치와 변환, 선택 상태 저장
        self._saved_bounds = bounds
        self._saved_transform = vtkTransform()
        self._rep.GetTransform(self._saved_transform)
        manager = self._vtk_widget.obj_manager
        self._saved_selection_ids = manager.selected_ids.copy()

        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2

        self.center_moved.emit(round(cx, 4), round(cy, 4), round(cz, 4))

    def _create_outline(self, obj_id: int, actor: vtkActor):
        """객체에 아웃라인 추가"""
        mapper = actor.GetMapper()
        if not mapper:
            return

        input_data = mapper.GetInput()
        if not input_data:
            return

        outline = vtkOutlineFilter()
        outline.SetInputData(input_data)

        outline_mapper = vtkPolyDataMapper()
        outline_mapper.SetInputConnection(outline.GetOutputPort())

        outline_actor = vtkActor()
        outline_actor.SetMapper(outline_mapper)

        # 노란색 아웃라인
        outline_actor.GetProperty().SetColor(1.0, 1.0, 0.2)
        outline_actor.GetProperty().SetLineWidth(3)

        # 원본 액터의 변환 정보 복사
        outline_actor.SetPosition(actor.GetPosition())
        outline_actor.SetOrientation(actor.GetOrientation())
        outline_actor.SetScale(actor.GetScale())
        outline_actor.SetOrigin(actor.GetOrigin())
        if actor.GetUserMatrix():
            outline_actor.SetUserMatrix(actor.GetUserMatrix())

        self._renderer.AddActor(outline_actor)
        self._outline_actors[obj_id] = outline_actor

    def _remove_outlines(self):
        """모든 아웃라인 제거"""
        for outline_actor in self._outline_actors.values():
            self._renderer.RemoveActor(outline_actor)
        self._outline_actors.clear()

    def _apply_highlight(self):
        """선택된 객체 하이라이트 적용"""
        manager = self._vtk_widget.obj_manager
        selected_ids = manager.selected_ids

        if not selected_ids:
            return

        # 모든 객체 순회
        for obj_id, obj_data in manager._objects.items():
            if obj_data.removed:
                continue

            actor = obj_data.actor
            prop = actor.GetProperty()

            # 원본 상태 저장
            if obj_id not in self._original_opacity:
                self._original_opacity[obj_id] = prop.GetOpacity()
            if obj_id not in self._original_color:
                color = prop.GetColor()
                self._original_color[obj_id] = (color[0], color[1], color[2])

            if obj_id in selected_ids:
                # 선택된 객체: 투명하게 표시 (프로브 박스가 잘 보이도록)
                prop.SetOpacity(0.3)
                prop.SetColor(1.0, 1.0, 0.4)
                self._create_outline(obj_id, actor)
            else:
                # 비선택 객체: 더 투명하게
                prop.SetOpacity(0.1)

    def _restore_original(self):
        """원본 상태 복원"""
        manager = self._vtk_widget.obj_manager

        for obj_id, opacity in self._original_opacity.items():
            obj_data = manager.get(obj_id)
            if obj_data and not obj_data.removed:
                obj_data.actor.GetProperty().SetOpacity(opacity)

        for obj_id, color in self._original_color.items():
            obj_data = manager.get(obj_id)
            if obj_data and not obj_data.removed:
                obj_data.actor.GetProperty().SetColor(color)

        self._original_opacity.clear()
        self._original_color.clear()

        self._remove_outlines()

    def update_box_position(self):
        """선택된 객체에 맞게 박스 위치 업데이트"""
        manager = self._vtk_widget.obj_manager
        selected_ids = manager.selected_ids

        if not selected_ids:
            self._place_initial_box()
            return

        # 선택된 객체들의 bounds 계산
        bounds = [float('inf'), float('-inf'),
                  float('inf'), float('-inf'),
                  float('inf'), float('-inf')]

        for obj_id in selected_ids:
            obj_data = manager.get(obj_id)
            if obj_data and not obj_data.removed:
                obj_bounds = obj_data.actor.GetBounds()
                bounds[0] = min(bounds[0], obj_bounds[0])
                bounds[1] = max(bounds[1], obj_bounds[1])
                bounds[2] = min(bounds[2], obj_bounds[2])
                bounds[3] = max(bounds[3], obj_bounds[3])
                bounds[4] = min(bounds[4], obj_bounds[4])
                bounds[5] = max(bounds[5], obj_bounds[5])

        # bounds가 유효한 경우에만 적용
        if bounds[0] != float('inf'):
            self._rep.PlaceWidget(bounds)

    def show(self):
        """도구 표시"""
        if self._visible:
            return

        manager = self._vtk_widget.obj_manager
        current_selection = manager.selected_ids

        # 저장된 위치가 있고, 같은 객체가 선택된 경우에만 저장된 위치와 회전 사용
        if (self._saved_bounds and
            self._saved_transform and
            self._saved_selection_ids is not None and
            self._saved_selection_ids == current_selection):
            # 저장된 transform으로 위치/크기/회전 모두 복원
            self._rep.SetTransform(self._saved_transform)
        else:
            # 새로운 객체이거나 선택이 변경됨 -> 새 위치로 시작
            self._place_box_by_selection()

        self._apply_highlight()

        self._box_widget.On()
        self._visible = True
        self.visibility_changed.emit(True)

        self._renderer.GetRenderWindow().Render()

    def _place_box_by_selection(self):
        """선택 상태에 따라 박스 위치/크기 설정 (프로브 40% 확장)"""
        manager = self._vtk_widget.obj_manager
        selected_ids = manager.selected_ids

        if selected_ids:
            # 선택된 객체들의 bounds
            bounds = self._calculate_bounds(selected_ids)
        else:
            # 전체 객체들의 bounds
            all_ids = [obj_id for obj_id, obj in manager._objects.items() if not obj.removed]
            bounds = self._calculate_bounds(all_ids)

        if bounds:
            # 프로브 박스를 40% 확장
            expanded_bounds = self._expand_bounds(bounds, self._probe_scale)
            self._rep.PlaceWidget(expanded_bounds)
            self._saved_bounds = expanded_bounds
            self._saved_selection_ids = selected_ids.copy() if selected_ids else set()
            # 새 위치에서는 회전 초기화
            self._saved_transform = None

    def _expand_bounds(self, bounds: list, scale: float) -> list:
        """bounds를 중심 기준으로 확장

        Args:
            bounds: [xmin, xmax, ymin, ymax, zmin, zmax]
            scale: 확장 배율 (1.4 = 40% 확장)
        """
        cx = (bounds[0] + bounds[1]) / 2
        cy = (bounds[2] + bounds[3]) / 2
        cz = (bounds[4] + bounds[5]) / 2

        half_x = (bounds[1] - bounds[0]) / 2 * scale
        half_y = (bounds[3] - bounds[2]) / 2 * scale
        half_z = (bounds[5] - bounds[4]) / 2 * scale

        return [
            cx - half_x, cx + half_x,
            cy - half_y, cy + half_y,
            cz - half_z, cz + half_z
        ]

    def _calculate_bounds(self, obj_ids, padding: float = 0.0) -> list:
        """객체들의 bounds 계산

        Args:
            obj_ids: 객체 ID 목록
            padding: bounds 확장 비율 (0.4 = 40% 확장)
        """
        manager = self._vtk_widget.obj_manager

        bounds = [float('inf'), float('-inf'),
                  float('inf'), float('-inf'),
                  float('inf'), float('-inf')]

        for obj_id in obj_ids:
            obj_data = manager.get(obj_id)
            if obj_data and not obj_data.removed:
                obj_bounds = obj_data.actor.GetBounds()
                bounds[0] = min(bounds[0], obj_bounds[0])
                bounds[1] = max(bounds[1], obj_bounds[1])
                bounds[2] = min(bounds[2], obj_bounds[2])
                bounds[3] = max(bounds[3], obj_bounds[3])
                bounds[4] = min(bounds[4], obj_bounds[4])
                bounds[5] = max(bounds[5], obj_bounds[5])

        # 유효한 bounds인지 확인
        if bounds[0] == float('inf'):
            return [-1, 1, -1, 1, -1, 1]

        # padding 적용 (각 축에 대해 확장)
        if padding > 0:
            for i in range(3):
                size = bounds[i*2 + 1] - bounds[i*2]
                expand = size * padding / 2
                bounds[i*2] -= expand
                bounds[i*2 + 1] += expand

        return bounds

    def hide(self):
        """도구 숨김"""
        if not self._visible:
            return

        self._box_widget.Off()
        self._visible = False
        self.visibility_changed.emit(False)

        self._restore_original()

        self._renderer.GetRenderWindow().Render()

    def toggle(self):
        """가시성 토글"""
        if self._visible:
            self.hide()
        else:
            self.show()

    def reset_to_origin(self):
        """선택된 객체의 중심으로 프로브 리셋 (회전 초기화)

        - 객체 선택됨: 선택된 객체 중심으로 이동, 프로브 크기 40% 확장
        - 선택 없음: 전체 객체 중심으로 이동, 프로브 크기 40% 확장
        """
        manager = self._vtk_widget.obj_manager
        selected_ids = manager.selected_ids

        if selected_ids:
            # 선택된 객체들의 bounds 사용
            bounds = self._calculate_bounds(selected_ids)
        else:
            # 전체 객체들의 bounds 사용
            all_ids = [obj_id for obj_id, obj in manager._objects.items() if not obj.removed]
            bounds = self._calculate_bounds(all_ids)

        # 객체 중심 계산
        cx = (bounds[0] + bounds[1]) / 2
        cy = (bounds[2] + bounds[3]) / 2
        cz = (bounds[4] + bounds[5]) / 2

        # 프로브 크기 40% 확장
        expanded_bounds = self._expand_bounds(bounds, self._probe_scale)

        self._saved_bounds = expanded_bounds
        self._saved_transform = None  # 회전 초기화
        self._saved_selection_ids = selected_ids.copy() if selected_ids else set()
        self._rep.PlaceWidget(expanded_bounds)

        if self._visible:
            self._renderer.GetRenderWindow().Render()

        self.center_moved.emit(round(cx, 4), round(cy, 4), round(cz, 4))

    def set_center(self, x: float, y: float, z: float, size: float = None):
        """박스 중심 위치 설정

        Args:
            x, y, z: 중심 좌표
            size: 박스 크기 (기본값: 이전 크기 유지)
        """
        if size is not None:
            self._box_size = size

        half = self._box_size / 2
        bounds = [x - half, x + half, y - half, y + half, z - half, z + half]

        self._saved_bounds = bounds
        self._rep.PlaceWidget(bounds)

        if self._visible:
            self._renderer.GetRenderWindow().Render()

        self.center_moved.emit(round(x, 4), round(y, 4), round(z, 4))

    def get_center(self) -> tuple:
        """현재 박스 중심 좌표 반환

        Returns:
            (x, y, z) 튜플
        """
        bounds = self._rep.GetBounds()
        cx = (bounds[0] + bounds[1]) / 2
        cy = (bounds[2] + bounds[3]) / 2
        cz = (bounds[4] + bounds[5]) / 2
        return (round(cx, 4), round(cy, 4), round(cz, 4))

    def get_bounds(self) -> tuple:
        """현재 박스 bounds 반환

        Returns:
            (xmin, xmax, ymin, ymax, zmin, zmax) 튜플
        """
        return tuple(self._rep.GetBounds())

    def cleanup(self):
        """리소스 정리"""
        self.hide()
        self._box_widget.Off()
        self._box_widget.SetInteractor(None)
