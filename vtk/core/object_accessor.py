"""
체이닝 방식의 객체 접근자

사용 예시:
    widget.object(1).hide()
    widget.object("cube").color(255, 0, 0).opacity(0.5)
    widget.group("walls").show().style("wireframe")
"""
from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Union

if TYPE_CHECKING:
    from .object_manager import ObjectManager
    from .object_data import ObjectData


class ObjectAccessor:
    """단일 객체에 대한 체이닝 접근자"""

    def __init__(self, manager: "ObjectManager", obj: "ObjectData"):
        self._manager = manager
        self._obj = obj

    @property
    def data(self) -> "ObjectData":
        """원본 ObjectData 반환"""
        return self._obj

    @property
    def id(self) -> int:
        return self._obj.id

    @property
    def actor(self):
        return self._obj.actor

    # ===== 체이닝 메서드 =====

    def show(self) -> "ObjectAccessor":
        """객체 표시"""
        self._obj.visible = True
        self._obj.actor.SetVisibility(True)
        self._manager._render()
        return self

    def hide(self) -> "ObjectAccessor":
        """객체 숨김"""
        self._obj.visible = False
        self._obj.actor.SetVisibility(False)
        self._manager._render()
        return self

    def visible(self, value: bool) -> "ObjectAccessor":
        """가시성 설정"""
        return self.show() if value else self.hide()

    def opacity(self, value: float) -> "ObjectAccessor":
        """투명도 설정 (0.0 ~ 1.0)"""
        self._obj.opacity = value
        self._obj.actor.GetProperty().SetOpacity(value)
        self._manager._render()
        return self

    def color(self, r: int, g: int, b: int) -> "ObjectAccessor":
        """색상 설정 (RGB 0-255)"""
        self._obj.color = (r, g, b)
        prop = self._obj.actor.GetProperty()
        prop.SetColor(r / 255.0, g / 255.0, b / 255.0)
        self._manager._render()
        return self

    def style(self, style: str) -> "ObjectAccessor":
        """뷰 스타일 설정

        Args:
            style: "wireframe", "surface", "surface with edge", "transparent"
        """
        self._obj.view_style = style
        self._manager._apply_style(self._obj, style)
        self._manager._render()
        return self

    def name(self, value: str) -> "ObjectAccessor":
        """이름 설정"""
        self._obj.name = value
        return self

    def group(self, value: str) -> "ObjectAccessor":
        """그룹 설정"""
        self._obj.group = value
        return self

    def select(self) -> "ObjectAccessor":
        """객체 선택"""
        self._manager.select_single(self._obj.id)
        return self

    def focus(self) -> "ObjectAccessor":
        """객체에 포커스 (카메라 이동)"""
        self._manager.focus_on(self._obj.id)
        return self

    def remove(self) -> None:
        """객체 삭제"""
        self._manager.remove(self._obj.id)

    def highlight(self, enable: bool = True) -> "ObjectAccessor":
        """하이라이트 효과"""
        if enable:
            self._manager._effect_highlight(self._obj)
        else:
            # 기본 스타일로 복원
            self._manager._apply_style(self._obj, self._obj.view_style)
        self._manager._render()
        return self

    # ===== 정보 조회 (체이닝 아님) =====

    def get_bounds(self) -> Tuple[float, float, float, float, float, float]:
        """바운딩 박스 반환 (xmin, xmax, ymin, ymax, zmin, zmax)"""
        return self._obj.actor.GetBounds()

    def get_center(self) -> Tuple[float, float, float]:
        """중심점 반환"""
        b = self.get_bounds()
        return ((b[0]+b[1])/2, (b[2]+b[3])/2, (b[4]+b[5])/2)

    def is_visible(self) -> bool:
        return self._obj.visible

    def get_name(self) -> str:
        return self._obj.name

    def get_group(self) -> str:
        return self._obj.group


class GroupAccessor:
    """그룹 객체들에 대한 체이닝 접근자"""

    def __init__(self, manager: "ObjectManager", objects: List["ObjectData"]):
        self._manager = manager
        self._objects = objects

    @property
    def count(self) -> int:
        """그룹 내 객체 수"""
        return len(self._objects)

    @property
    def ids(self) -> List[int]:
        """그룹 내 모든 객체 ID"""
        return [obj.id for obj in self._objects]

    def each(self) -> List[ObjectAccessor]:
        """각 객체의 ObjectAccessor 리스트 반환"""
        return [ObjectAccessor(self._manager, obj) for obj in self._objects]

    # ===== 체이닝 메서드 (모든 객체에 적용) =====

    def show(self) -> "GroupAccessor":
        """모든 객체 표시"""
        for obj in self._objects:
            obj.visible = True
            obj.actor.SetVisibility(True)
        self._manager._render()
        return self

    def hide(self) -> "GroupAccessor":
        """모든 객체 숨김"""
        for obj in self._objects:
            obj.visible = False
            obj.actor.SetVisibility(False)
        self._manager._render()
        return self

    def visible(self, value: bool) -> "GroupAccessor":
        """가시성 설정"""
        return self.show() if value else self.hide()

    def opacity(self, value: float) -> "GroupAccessor":
        """투명도 설정"""
        for obj in self._objects:
            obj.opacity = value
            obj.actor.GetProperty().SetOpacity(value)
        self._manager._render()
        return self

    def color(self, r: int, g: int, b: int) -> "GroupAccessor":
        """색상 설정"""
        for obj in self._objects:
            obj.color = (r, g, b)
            obj.actor.GetProperty().SetColor(r / 255.0, g / 255.0, b / 255.0)
        self._manager._render()
        return self

    def style(self, style: str) -> "GroupAccessor":
        """뷰 스타일 설정"""
        for obj in self._objects:
            obj.view_style = style
            self._manager._apply_style(obj, style)
        self._manager._render()
        return self

    def select(self) -> "GroupAccessor":
        """모든 객체 선택"""
        self._manager.select_multiple([obj.id for obj in self._objects])
        return self

    def remove(self) -> None:
        """모든 객체 삭제"""
        for obj in self._objects:
            self._manager.remove(obj.id)
