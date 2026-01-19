"""
Undo/Redo 시스템 (Command Pattern)

사용 예시:
    from nextlib.vtk.core import CommandHistory, UndoableManager

    # ObjectManager를 래핑
    undoable = UndoableManager(widget.obj_manager)

    # Undo 가능한 객체 추가
    obj_id = undoable.add(actor, name="cube1")

    # Undo 가능한 속성 변경
    undoable.set_visible(obj_id, False)
    undoable.set_opacity(obj_id, 0.5)
    undoable.set_color(obj_id, (255, 0, 0))

    # Undo/Redo
    undoable.undo()  # 마지막 작업 취소
    undoable.redo()  # 다시 실행

    # 단축키 연결
    if undoable.can_undo():
        undoable.undo()
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .object_manager import ObjectManager


# ===== Command 인터페이스 =====

class Command(ABC):
    """명령 인터페이스"""

    @abstractmethod
    def execute(self) -> Any:
        """명령 실행"""
        pass

    @abstractmethod
    def undo(self):
        """명령 취소"""
        pass

    @property
    def description(self) -> str:
        """명령 설명 (디버깅/UI용)"""
        return self.__class__.__name__


# ===== 구체적인 Command 클래스들 =====

class AddObjectCommand(Command):
    """객체 추가 명령"""

    def __init__(self, manager: "ObjectManager", actor, name: str, group: str):
        self._manager = manager
        self._actor = actor
        self._name = name
        self._group = group
        self._obj_id: Optional[int] = None

    def execute(self) -> int:
        self._obj_id = self._manager.add(self._actor, name=self._name, group=self._group)
        return self._obj_id

    def undo(self):
        if self._obj_id is not None:
            self._manager.remove(self._obj_id)

    @property
    def description(self) -> str:
        return f"Add '{self._name}'"


class RemoveObjectCommand(Command):
    """객체 제거 명령"""

    def __init__(self, manager: "ObjectManager", obj_id: int):
        self._manager = manager
        self._obj_id = obj_id
        self._obj_data = None

    def execute(self):
        # 제거 전 데이터 백업
        self._obj_data = self._manager.get(self._obj_id)
        if self._obj_data:
            self._manager.remove(self._obj_id)

    def undo(self):
        if self._obj_data:
            # 객체 복원
            self._obj_data.removed = False
            self._manager.renderer.AddActor(self._obj_data.actor)
            self._manager._objects[self._obj_id] = self._obj_data
            self._manager._render()

    @property
    def description(self) -> str:
        name = self._obj_data.name if self._obj_data else str(self._obj_id)
        return f"Remove '{name}'"


class ChangeVisibleCommand(Command):
    """가시성 변경 명령"""

    def __init__(self, manager: "ObjectManager", obj_id: int, visible: bool):
        self._manager = manager
        self._obj_id = obj_id
        self._new_value = visible
        self._old_value: Optional[bool] = None

    def execute(self):
        obj = self._manager.get(self._obj_id)
        if obj:
            self._old_value = obj.visible
            obj.visible = self._new_value
            obj.actor.SetVisibility(self._new_value)
            self._manager._render()

    def undo(self):
        if self._old_value is not None:
            obj = self._manager.get(self._obj_id)
            if obj:
                obj.visible = self._old_value
                obj.actor.SetVisibility(self._old_value)
                self._manager._render()

    @property
    def description(self) -> str:
        return f"Set visible={self._new_value}"


class ChangeOpacityCommand(Command):
    """투명도 변경 명령"""

    def __init__(self, manager: "ObjectManager", obj_id: int, opacity: float):
        self._manager = manager
        self._obj_id = obj_id
        self._new_value = opacity
        self._old_value: Optional[float] = None

    def execute(self):
        obj = self._manager.get(self._obj_id)
        if obj:
            self._old_value = obj.opacity
            obj.opacity = self._new_value
            obj.actor.GetProperty().SetOpacity(self._new_value)
            self._manager._render()

    def undo(self):
        if self._old_value is not None:
            obj = self._manager.get(self._obj_id)
            if obj:
                obj.opacity = self._old_value
                obj.actor.GetProperty().SetOpacity(self._old_value)
                self._manager._render()

    @property
    def description(self) -> str:
        return f"Set opacity={self._new_value}"


class ChangeColorCommand(Command):
    """색상 변경 명령"""

    def __init__(self, manager: "ObjectManager", obj_id: int, color: tuple):
        self._manager = manager
        self._obj_id = obj_id
        self._new_value = color  # RGB 0-255
        self._old_value: Optional[tuple] = None

    def execute(self):
        obj = self._manager.get(self._obj_id)
        if obj:
            prop = obj.actor.GetProperty()
            old_color = prop.GetColor()
            self._old_value = (int(old_color[0]*255), int(old_color[1]*255), int(old_color[2]*255))
            obj.color = self._new_value
            prop.SetColor(self._new_value[0]/255, self._new_value[1]/255, self._new_value[2]/255)
            self._manager._render()

    def undo(self):
        if self._old_value is not None:
            obj = self._manager.get(self._obj_id)
            if obj:
                obj.color = self._old_value
                prop = obj.actor.GetProperty()
                prop.SetColor(self._old_value[0]/255, self._old_value[1]/255, self._old_value[2]/255)
                self._manager._render()

    @property
    def description(self) -> str:
        return f"Set color={self._new_value}"


# ===== Command History =====

class CommandHistory:
    """명령 히스토리 관리자"""

    def __init__(self, max_history: int = 100):
        self._max_history = max_history
        self._commands: List[Command] = []
        self._current_index = -1

    def execute(self, command: Command) -> Any:
        """명령 실행 및 히스토리 추가"""
        # 현재 위치 이후의 명령들 삭제 (새로운 분기)
        if self._current_index < len(self._commands) - 1:
            self._commands = self._commands[:self._current_index + 1]

        # 명령 실행
        result = command.execute()

        # 히스토리 추가
        self._commands.append(command)
        self._current_index += 1

        # 최대 히스토리 제한
        if len(self._commands) > self._max_history:
            self._commands.pop(0)
            self._current_index -= 1

        return result

    def undo(self) -> bool:
        """실행 취소"""
        if not self.can_undo():
            return False

        command = self._commands[self._current_index]
        command.undo()
        self._current_index -= 1
        return True

    def redo(self) -> bool:
        """다시 실행"""
        if not self.can_redo():
            return False

        self._current_index += 1
        command = self._commands[self._current_index]
        command.execute()
        return True

    def can_undo(self) -> bool:
        """Undo 가능 여부"""
        return self._current_index >= 0

    def can_redo(self) -> bool:
        """Redo 가능 여부"""
        return self._current_index < len(self._commands) - 1

    def clear(self):
        """히스토리 초기화"""
        self._commands.clear()
        self._current_index = -1

    @property
    def undo_description(self) -> Optional[str]:
        """Undo할 명령 설명"""
        if self.can_undo():
            return self._commands[self._current_index].description
        return None

    @property
    def redo_description(self) -> Optional[str]:
        """Redo할 명령 설명"""
        if self.can_redo():
            return self._commands[self._current_index + 1].description
        return None

    @property
    def history_count(self) -> int:
        """히스토리 개수"""
        return len(self._commands)


# ===== UndoableManager =====

class UndoableManager:
    """Undo/Redo를 지원하는 ObjectManager 래퍼"""

    def __init__(self, obj_manager: "ObjectManager", max_history: int = 100):
        self._manager = obj_manager
        self._history = CommandHistory(max_history)

    @property
    def history(self) -> CommandHistory:
        """히스토리 객체 접근"""
        return self._history

    # ===== Undo 가능한 작업들 =====

    def add(self, actor, name: str = "", group: str = "default") -> int:
        """객체 추가 (Undo 가능)"""
        cmd = AddObjectCommand(self._manager, actor, name, group)
        return self._history.execute(cmd)

    def remove(self, obj_id: int):
        """객체 제거 (Undo 가능)"""
        cmd = RemoveObjectCommand(self._manager, obj_id)
        self._history.execute(cmd)

    def set_visible(self, obj_id: int, visible: bool):
        """가시성 변경 (Undo 가능)"""
        cmd = ChangeVisibleCommand(self._manager, obj_id, visible)
        self._history.execute(cmd)

    def set_opacity(self, obj_id: int, opacity: float):
        """투명도 변경 (Undo 가능)"""
        cmd = ChangeOpacityCommand(self._manager, obj_id, opacity)
        self._history.execute(cmd)

    def set_color(self, obj_id: int, color: tuple):
        """색상 변경 (Undo 가능)"""
        cmd = ChangeColorCommand(self._manager, obj_id, color)
        self._history.execute(cmd)

    # ===== Undo/Redo =====

    def undo(self) -> bool:
        """실행 취소"""
        return self._history.undo()

    def redo(self) -> bool:
        """다시 실행"""
        return self._history.redo()

    def can_undo(self) -> bool:
        return self._history.can_undo()

    def can_redo(self) -> bool:
        return self._history.can_redo()

    # ===== 기존 ObjectManager 메서드 전달 =====

    def __getattr__(self, name):
        """래핑된 ObjectManager의 메서드/속성 접근"""
        return getattr(self._manager, name)
