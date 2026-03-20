"""
VTK Scene Tree Widget

CAD 스타일의 객체 트리 패널 - VTK 씬에 로드된 객체들을 그룹별로 표시하고
사용자가 직접 가시성을 제어할 수 있게 함.

사용 예시:
    vtk_widget.enable_scene_tree()  # 씬 트리 활성화
    vtk_widget.disable_scene_tree()  # 씬 트리 비활성화
"""
from typing import Dict, Optional, Set

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QFrame, QSplitter, QSizePolicy, QToolButton, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon


class SceneTreeWidget(QFrame):
    """VTK 씬 객체 트리 위젯

    Signals:
        visibility_changed: (obj_id: int, visible: bool) - 객체 가시성 변경 시
        group_visibility_changed: (group_name: str, visible: bool) - 그룹 가시성 변경 시
        selection_changed: (obj_ids: list) - 트리에서 선택 변경 시
    """

    visibility_changed = Signal(int, bool)
    group_visibility_changed = Signal(str, bool)
    selection_changed = Signal(list)

    ICON_VISIBLE = "\U0001F441"
    ICON_HIDDEN = "\u25CB"

    def __init__(self, parent=None):
        super().__init__(parent)

        self._obj_manager = None
        self._group_items: Dict[str, QTreeWidgetItem] = {}
        self._obj_items: Dict[int, QTreeWidgetItem] = {}
        self._group_visibility: Dict[str, bool] = {}
        self._collapsed = False
        self._sync_selection_lock = False

        self._setup_ui()

    def _setup_ui(self):
        """UI 설정"""
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(28)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(4, 2, 4, 2)
        header_layout.setSpacing(4)

        self._toggle_btn = QToolButton()
        self._toggle_btn.setText("\u25C0")
        self._toggle_btn.setFixedSize(20, 20)
        self._toggle_btn.clicked.connect(self._on_toggle_clicked)
        header_layout.addWidget(self._toggle_btn)

        self._title_label = QPushButton("Scene")
        self._title_label.setFlat(True)
        self._title_label.clicked.connect(self._on_toggle_clicked)
        header_layout.addWidget(self._title_label, stretch=1)

        self._show_all_btn = QToolButton()
        self._show_all_btn.setText(self.ICON_VISIBLE)
        self._show_all_btn.setToolTip("Show All")
        self._show_all_btn.setFixedSize(24, 20)
        self._show_all_btn.clicked.connect(self._on_show_all)
        header_layout.addWidget(self._show_all_btn)

        self._hide_all_btn = QToolButton()
        self._hide_all_btn.setText(self.ICON_HIDDEN)
        self._hide_all_btn.setToolTip("Hide All")
        self._hide_all_btn.setFixedSize(24, 20)
        self._hide_all_btn.clicked.connect(self._on_hide_all)
        header_layout.addWidget(self._hide_all_btn)

        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setColumnCount(2)
        self._tree.setIndentation(16)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self._tree.setRootIsDecorated(True)
        self._tree.itemSelectionChanged.connect(self._on_tree_selection_changed)
        self._tree.itemClicked.connect(self._on_item_clicked)

        tree_header = self._tree.header()
        tree_header.setStretchLastSection(False)
        tree_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tree_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._tree.setColumnWidth(1, 30)

        layout.addWidget(self._tree)

        self.setMinimumWidth(150)
        self.setMaximumWidth(300)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def set_object_manager(self, obj_manager):
        """ObjectManager 연결

        Args:
            obj_manager: VTK ObjectManager 인스턴스
        """
        if self._obj_manager:
            try:
                self._obj_manager.object_added.disconnect(self._on_object_added)
                self._obj_manager.object_removed.disconnect(self._on_object_removed)
                self._obj_manager.selection_changed.disconnect(self._on_vtk_selection_changed)
            except Exception:
                pass

        self._obj_manager = obj_manager

        if obj_manager:
            obj_manager.object_added.connect(self._on_object_added)
            obj_manager.object_removed.connect(self._on_object_removed)
            obj_manager.selection_changed.connect(self._on_vtk_selection_changed)

            self._load_existing_objects()

    def _load_existing_objects(self):
        """기존 ObjectManager 객체들을 트리에 추가"""
        if not self._obj_manager:
            return

        self._tree.clear()
        self._group_items.clear()
        self._obj_items.clear()
        self._group_visibility.clear()

        for obj in self._obj_manager.get_all():
            self._add_object_to_tree(obj.id, obj.name, obj.group, obj.actor.GetVisibility())

    def _add_object_to_tree(self, obj_id: int, name: str, group: str, visible: bool = True):
        """트리에 객체 추가"""
        if group not in self._group_items:
            group_item = QTreeWidgetItem(self._tree)
            group_item.setText(0, group.capitalize())
            group_item.setText(1, self.ICON_VISIBLE)
            group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "name": group})
            group_item.setExpanded(True)
            self._group_items[group] = group_item
            self._group_visibility[group] = True

        group_item = self._group_items[group]

        obj_item = QTreeWidgetItem(group_item)
        obj_item.setText(0, name)
        obj_item.setText(1, self.ICON_VISIBLE if visible else self.ICON_HIDDEN)
        obj_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "object", "id": obj_id, "visible": visible})

        self._obj_items[obj_id] = obj_item

    def _remove_object_from_tree(self, obj_id: int):
        """트리에서 객체 제거"""
        if obj_id not in self._obj_items:
            return

        obj_item = self._obj_items.pop(obj_id)
        parent = obj_item.parent()

        if parent:
            parent.removeChild(obj_item)

            if parent.childCount() == 0:
                data = parent.data(0, Qt.ItemDataRole.UserRole)
                if data and data.get("type") == "group":
                    group_name = data.get("name")
                    if group_name in self._group_items:
                        del self._group_items[group_name]
                    if group_name in self._group_visibility:
                        del self._group_visibility[group_name]
                index = self._tree.indexOfTopLevelItem(parent)
                if index >= 0:
                    self._tree.takeTopLevelItem(index)

    def _on_object_added(self, obj_id: int, name: str):
        """ObjectManager에서 객체 추가됨"""
        if not self._obj_manager:
            return

        obj = self._obj_manager.get(obj_id)
        if obj:
            self._add_object_to_tree(obj_id, name, obj.group, obj.actor.GetVisibility())

    def _on_object_removed(self, obj_id: int, name: str):
        """ObjectManager에서 객체 제거됨"""
        self._remove_object_from_tree(obj_id)

    def _on_vtk_selection_changed(self, info: dict):
        """VTK 선택 변경됨 - 트리 동기화"""
        if self._sync_selection_lock:
            return

        self._sync_selection_lock = True

        selected_ids = info.get("selected_ids", [])

        self._tree.blockSignals(True)
        self._tree.clearSelection()

        for obj_id in selected_ids:
            if obj_id in self._obj_items:
                self._obj_items[obj_id].setSelected(True)

        self._tree.blockSignals(False)
        self._sync_selection_lock = False

    def _on_tree_selection_changed(self):
        """트리 선택 변경됨 - VTK 동기화"""
        if self._sync_selection_lock or not self._obj_manager:
            return

        self._sync_selection_lock = True

        selected_ids = []
        for item in self._tree.selectedItems():
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "object":
                selected_ids.append(data["id"])

        self._obj_manager.blockSignals(True)
        if selected_ids:
            self._obj_manager.select_multiple(selected_ids)
        else:
            self._obj_manager.clear_selection()
        self._obj_manager.blockSignals(False)

        self._sync_selection_lock = False

        self.selection_changed.emit(selected_ids)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """아이템 클릭 - 가시성 컬럼이면 토글"""
        if column != 1:
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        item_type = data.get("type")

        if item_type == "group":
            group_name = data.get("name")
            current_visible = self._group_visibility.get(group_name, True)
            new_visible = not current_visible

            self._set_group_visibility(group_name, new_visible)

        elif item_type == "object":
            obj_id = data.get("id")
            current_visible = data.get("visible", True)
            new_visible = not current_visible

            self._set_object_visibility(obj_id, new_visible)

    def _set_object_visibility(self, obj_id: int, visible: bool):
        """객체 가시성 설정"""
        if obj_id not in self._obj_items:
            return

        item = self._obj_items[obj_id]
        data = item.data(0, Qt.ItemDataRole.UserRole)
        data["visible"] = visible
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        item.setText(1, self.ICON_VISIBLE if visible else self.ICON_HIDDEN)

        if self._obj_manager:
            obj = self._obj_manager.get(obj_id)
            if obj:
                obj.actor.SetVisibility(visible)
                self._obj_manager._render()

        self.visibility_changed.emit(obj_id, visible)

    def _set_group_visibility(self, group_name: str, visible: bool):
        """그룹 가시성 설정"""
        if group_name not in self._group_items:
            return

        self._group_visibility[group_name] = visible

        group_item = self._group_items[group_name]
        group_item.setText(1, self.ICON_VISIBLE if visible else self.ICON_HIDDEN)

        for i in range(group_item.childCount()):
            child = group_item.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("type") == "object":
                obj_id = data.get("id")
                data["visible"] = visible
                child.setData(0, Qt.ItemDataRole.UserRole, data)
                child.setText(1, self.ICON_VISIBLE if visible else self.ICON_HIDDEN)

                if self._obj_manager:
                    obj = self._obj_manager.get(obj_id)
                    if obj:
                        obj.actor.SetVisibility(visible)

        if self._obj_manager:
            self._obj_manager._render()

        self.group_visibility_changed.emit(group_name, visible)

    def _on_toggle_clicked(self):
        """접기/펼치기 토글"""
        self._collapsed = not self._collapsed

        if self._collapsed:
            self._toggle_btn.setText("\u25B6")
            self._tree.hide()
            self._show_all_btn.hide()
            self._hide_all_btn.hide()
            self.setMaximumWidth(30)
            self.setMinimumWidth(30)
        else:
            self._toggle_btn.setText("\u25C0")
            self._tree.show()
            self._show_all_btn.show()
            self._hide_all_btn.show()
            self.setMaximumWidth(300)
            self.setMinimumWidth(150)

    def _on_show_all(self):
        """모든 객체 보이기"""
        for group_name in self._group_items:
            self._set_group_visibility(group_name, True)

    def _on_hide_all(self):
        """모든 객체 숨기기"""
        for group_name in self._group_items:
            self._set_group_visibility(group_name, False)

    def set_group_visible(self, group_name: str, visible: bool):
        """외부에서 그룹 가시성 설정

        Args:
            group_name: 그룹 이름
            visible: 가시성
        """
        self._set_group_visibility(group_name, visible)

    def set_object_visible(self, obj_id: int, visible: bool):
        """외부에서 객체 가시성 설정

        Args:
            obj_id: 객체 ID
            visible: 가시성
        """
        self._set_object_visibility(obj_id, visible)

    def get_group_visibility(self, group_name: str) -> bool:
        """그룹 가시성 조회"""
        return self._group_visibility.get(group_name, True)

    def get_object_visibility(self, obj_id: int) -> bool:
        """객체 가시성 조회"""
        if obj_id in self._obj_items:
            data = self._obj_items[obj_id].data(0, Qt.ItemDataRole.UserRole)
            if data:
                return data.get("visible", True)
        return True

    def refresh(self):
        """트리 새로고침 (ObjectManager와 동기화)"""
        self._load_existing_objects()

    def collapse(self):
        """패널 접기"""
        if not self._collapsed:
            self._on_toggle_clicked()

    def expand(self):
        """패널 펼치기"""
        if self._collapsed:
            self._on_toggle_clicked()
