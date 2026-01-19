"""
씬 상태 관리 클래스

현재 씬의 상태 정보를 한 곳에서 조회:
- 선택된 객체
- 뷰 스타일
- 객체 수
- 바운딩 박스 등

사용 예시:
    state = widget.state

    # 선택 정보
    state.selected_count          # 선택된 객체 수
    state.selected_ids            # 선택된 ID 리스트
    state.selected_names          # 선택된 이름 리스트
    state.has_selection           # 선택 여부

    # 객체 정보
    state.object_count            # 전체 객체 수
    state.objects                 # 모든 객체 정보 리스트
    state.groups                  # 그룹 목록

    # 뷰 정보
    state.view_style              # 현재 뷰 스타일
    state.is_parallel_projection  # 평행 투영 여부
    state.axes_visible            # 축 표시 여부
    state.ruler_visible           # 눈금자 표시 여부

    # 바운딩 박스
    state.bounds                  # 전체 씬 바운딩 박스
    state.center                  # 씬 중심점
"""
from typing import TYPE_CHECKING, List, Dict, Set, Tuple, Optional
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..vtk_widget_base import VtkWidgetBase


@dataclass
class ObjectInfo:
    """개별 객체 정보"""
    id: int
    name: str
    group: str
    visible: bool
    opacity: float
    color: Tuple[int, int, int]
    view_style: str
    selected: bool
    bounds: Tuple[float, float, float, float, float, float]


class SceneState:
    """씬 상태 조회 클래스 (읽기 전용)"""

    def __init__(self, widget: "VtkWidgetBase"):
        self._widget = widget

    # ===== 선택 정보 =====

    @property
    def selected_count(self) -> int:
        """선택된 객체 수"""
        return len(self._widget.obj_manager._selected_ids)

    @property
    def selected_ids(self) -> List[int]:
        """선택된 객체 ID 리스트"""
        return list(self._widget.obj_manager._selected_ids)

    @property
    def selected_names(self) -> List[str]:
        """선택된 객체 이름 리스트"""
        names = []
        for obj_id in self._widget.obj_manager._selected_ids:
            obj = self._widget.obj_manager.get(obj_id)
            if obj:
                names.append(obj.name)
        return names

    @property
    def selected_objects(self) -> List[ObjectInfo]:
        """선택된 객체 정보 리스트"""
        return [self._get_object_info(obj_id) for obj_id in self._widget.obj_manager._selected_ids
                if self._widget.obj_manager.get(obj_id)]

    @property
    def has_selection(self) -> bool:
        """선택된 객체가 있는지"""
        return len(self._widget.obj_manager._selected_ids) > 0

    @property
    def first_selected(self) -> Optional[ObjectInfo]:
        """첫 번째 선택된 객체 (없으면 None)"""
        if self._widget.obj_manager._selected_ids:
            obj_id = next(iter(self._widget.obj_manager._selected_ids))
            return self._get_object_info(obj_id)
        return None

    # ===== 객체 정보 =====

    @property
    def object_count(self) -> int:
        """전체 객체 수 (삭제된 것 제외)"""
        return len(self._widget.obj_manager.get_all())

    @property
    def object_ids(self) -> List[int]:
        """모든 객체 ID 리스트"""
        return [obj.id for obj in self._widget.obj_manager.get_all()]

    @property
    def object_names(self) -> List[str]:
        """모든 객체 이름 리스트"""
        return [obj.name for obj in self._widget.obj_manager.get_all()]

    @property
    def objects(self) -> List[ObjectInfo]:
        """모든 객체 정보 리스트"""
        return [self._get_object_info(obj.id) for obj in self._widget.obj_manager.get_all()]

    @property
    def groups(self) -> List[str]:
        """사용 중인 그룹 이름 목록 (중복 제거)"""
        groups = set()
        for obj in self._widget.obj_manager.get_all():
            groups.add(obj.group)
        return sorted(list(groups))

    @property
    def group_counts(self) -> Dict[str, int]:
        """그룹별 객체 수"""
        counts = {}
        for obj in self._widget.obj_manager.get_all():
            counts[obj.group] = counts.get(obj.group, 0) + 1
        return counts

    def objects_in_group(self, group: str) -> List[ObjectInfo]:
        """특정 그룹의 객체 정보 리스트"""
        return [self._get_object_info(obj.id)
                for obj in self._widget.obj_manager.get_all()
                if obj.group == group]

    # ===== 뷰 정보 =====

    @property
    def view_style(self) -> str:
        """현재 뷰 스타일 (콤보박스 값)"""
        if hasattr(self._widget, '_view_combo'):
            return self._widget._view_combo.currentText()
        return "surface"

    @property
    def is_parallel_projection(self) -> bool:
        """평행 투영 여부"""
        return self._widget.camera.is_parallel_projection()

    @property
    def projection_mode(self) -> str:
        """투영 모드 ("perspective" 또는 "parallel")"""
        return "parallel" if self.is_parallel_projection else "perspective"

    @property
    def axes_visible(self) -> bool:
        """축 표시 여부"""
        return self._widget.axes.is_visible()

    @property
    def ruler_visible(self) -> bool:
        """눈금자 표시 여부"""
        return self._widget.ruler.is_visible()

    # ===== 씬 바운딩 박스 =====

    @property
    def bounds(self) -> Tuple[float, float, float, float, float, float]:
        """전체 씬 바운딩 박스 (xmin, xmax, ymin, ymax, zmin, zmax)"""
        bounds = [0.0] * 6
        self._widget.renderer.ComputeVisiblePropBounds(bounds)
        return tuple(bounds)

    @property
    def center(self) -> Tuple[float, float, float]:
        """씬 중심점"""
        b = self.bounds
        return ((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2)

    @property
    def size(self) -> Tuple[float, float, float]:
        """씬 크기 (dx, dy, dz)"""
        b = self.bounds
        return (b[1]-b[0], b[3]-b[2], b[5]-b[4])

    @property
    def diagonal(self) -> float:
        """씬 대각선 길이"""
        s = self.size
        return (s[0]**2 + s[1]**2 + s[2]**2) ** 0.5

    # ===== 카메라 정보 =====

    @property
    def camera_position(self) -> Tuple[float, float, float]:
        """카메라 위치"""
        return self._widget.renderer.GetActiveCamera().GetPosition()

    @property
    def camera_focal_point(self) -> Tuple[float, float, float]:
        """카메라 초점"""
        return self._widget.renderer.GetActiveCamera().GetFocalPoint()

    @property
    def camera_view_up(self) -> Tuple[float, float, float]:
        """카메라 상향 벡터"""
        return self._widget.renderer.GetActiveCamera().GetViewUp()

    # ===== 요약 정보 =====

    def summary(self) -> Dict:
        """전체 상태 요약 딕셔너리"""
        return {
            "object_count": self.object_count,
            "selected_count": self.selected_count,
            "selected_ids": self.selected_ids,
            "selected_names": self.selected_names,
            "groups": self.groups,
            "group_counts": self.group_counts,
            "view_style": self.view_style,
            "projection_mode": self.projection_mode,
            "axes_visible": self.axes_visible,
            "ruler_visible": self.ruler_visible,
            "bounds": self.bounds,
            "center": self.center,
        }

    def __repr__(self) -> str:
        return (
            f"SceneState("
            f"objects={self.object_count}, "
            f"selected={self.selected_count}, "
            f"style='{self.view_style}', "
            f"projection='{self.projection_mode}')"
        )

    # ===== 헬퍼 =====

    def _get_object_info(self, obj_id: int) -> Optional[ObjectInfo]:
        """ObjectData를 ObjectInfo로 변환"""
        obj = self._widget.obj_manager.get(obj_id)
        if not obj:
            return None

        # Actor에서 현재 색상 가져오기
        prop = obj.actor.GetProperty()
        color = prop.GetColor()
        color_rgb = (int(color[0]*255), int(color[1]*255), int(color[2]*255))

        return ObjectInfo(
            id=obj.id,
            name=obj.name,
            group=obj.group,
            visible=obj.visible,
            opacity=obj.opacity,
            color=color_rgb,
            view_style=obj.view_style,
            selected=obj.id in self._widget.obj_manager._selected_ids,
            bounds=obj.actor.GetBounds()
        )
