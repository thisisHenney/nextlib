from PySide6.QtCore import Qt, Signal, QObject, QEvent
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QComboBox,
    QCheckBox,
)


class TreeWidget(QObject):
    itemSelectedWithPos = Signal(list, int)
    itemDoubleClickedWithPos = Signal(list, int)

    def __init__(self, parent=None, widget: QTreeWidget = None):
        super().__init__(parent)

        self.widget = widget if widget is not None else QTreeWidget()

        self._not_editable_columns = set()
        self._not_editable_items = set()
        self._editing = False

        self._setup_style()
        self._connect_signals()

        self.widget.installEventFilter(self)

    def _setup_style(self):
        w = self.widget

        w.setAlternatingRowColors(True)
        w.setSelectionMode(QTreeWidget.ExtendedSelection)
        w.setSelectionBehavior(QTreeWidget.SelectRows)
        w.setVerticalScrollMode(QTreeWidget.ScrollPerItem)
        w.setIndentation(16)
        w.setRootIsDecorated(True)
        w.setUniformRowHeights(True)
        w.setAnimated(True)
        w.header().setVisible(True)
        w.header().setStretchLastSection(True)
        w.header().setDefaultSectionSize(160)
        w.header().setMinimumSectionSize(60)

        w.setStyleSheet("""
            QTreeWidget {
                show-decoration-selected: 1;
            }
            QTreeWidget::item {
                height: 24px;
                border-right: 1px dotted palette(mid);
            }
            QTreeWidget::item:hover {
                background-color: palette(midlight);
                border-radius: 3px;
            }
            QTreeWidget::item:selected {
                background-color: palette(highlight);
                border-radius: 3px;
            }
        """)

    def _connect_signals(self):
        w = self.widget
        w.itemSelectionChanged.connect(self._on_selection_changed)
        w.itemDoubleClicked.connect(self._on_double_click)

    def eventFilter(self, obj, event):
        if obj is not self.widget:
            return False

        et = event.type()
        if et == QEvent.MouseButtonDblClick:
            return self._on_mouse_double_click(event)
        elif et == QEvent.KeyPress:
            return self._on_key_press(event)

        return False

    def _on_mouse_double_click(self, event):
        w = self.widget
        pos = event.position().toPoint()
        item = w.itemAt(pos)
        if not item:
            return False

        col = w.columnAt(pos.x())
        if col == 0:
            return True
        if w.itemWidget(item, col):
            return True
        if item in self._not_editable_items or col in self._not_editable_columns:
            return True
        return False

    def _on_double_click(self, item, col):
        w = self.widget
        if not item or col == 0 or w.itemWidget(item, col):
            self._editing = False
            return

        if item in self._not_editable_items or col in self._not_editable_columns:
            self._editing = False
            return

        item.setFlags(item.flags() | Qt.ItemIsEditable)
        w.editItem(item, col)
        self._editing = True

        pos = self._get_item_pos(item)
        self.itemDoubleClickedWithPos.emit(pos, col)

    def _on_key_press(self, event):
        w = self.widget
        item = w.currentItem()
        col = w.currentColumn()
        key = event.key()

        if not item:
            return False

        if key in (Qt.Key_F2, Qt.Key_Return, Qt.Key_Enter):
            if col == 0:
                return True
            if w.itemWidget(item, col):
                return True
            if item in self._not_editable_items or col in self._not_editable_columns:
                return True

            item.setFlags(item.flags() | Qt.ItemIsEditable)
            w.editItem(item, col)
            self._editing = True
            return True

        if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
            self._editing = False
            return False

        if key == Qt.Key_Escape:
            self._editing = False
            return True

        return False

    def _on_selection_changed(self):
        w = self.widget
        selected = w.selectedItems()
        if not selected:
            return

        item = selected[0]
        col = w.currentColumn()
        pos = self._get_item_pos(item)

        self.itemSelectedWithPos.emit(pos, col)

    def _get_item_pos(self, item):
        pos = []
        w = self.widget
        while item:
            parent = item.parent()
            if parent:
                pos.insert(0, parent.indexOfChild(item))
            else:
                pos.insert(0, w.indexOfTopLevelItem(item))
            item = parent
        return pos

    def insert(self, pos: list, text: str, checkable=False):
        w = self.widget
        item = QTreeWidgetItem([text])
        item.setFlags(item.flags() | Qt.ItemIsEditable)

        if checkable:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Unchecked)

        depth = len(pos)

        if depth == 0:
            w.addTopLevelItem(item)
            return item

        if depth == 1:
            index = pos[0]
            if index >= w.topLevelItemCount():
                w.addTopLevelItem(item)
            else:
                w.insertTopLevelItem(index, item)
            return item

        parent = self.get_item(pos[:-1])
        if not parent:
            return None

        insert_index = pos[-1]
        if insert_index >= parent.childCount():
            parent.addChild(item)
        else:
            parent.insertChild(insert_index, item)

        return item

    def set_editable(self, pos: list = None, column=None, editable=True):
        w = self.widget

        if pos is None:
            if editable:
                self._not_editable_columns.discard(column)
            else:
                self._not_editable_columns.add(column)
            return

        item = self.get_item(pos)
        if not item:
            return

        if editable:
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self._not_editable_items.discard(item)
        else:
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self._not_editable_items.add(item)

    def get_item(self, pos: list):
        if not pos:
            return None
        w = self.widget
        item = w.topLevelItem(pos[0])
        for i in pos[1:]:
            if not item:
                return None
            item = item.child(i)
        return item

    def get_text(self, pos: list, column=0):
        item = self.get_item(pos)
        if item is None:
            return None

        w = self.widget
        widget = w.itemWidget(item, column)

        if widget:
            if isinstance(widget, QComboBox):
                return widget.currentText()
            if isinstance(widget, QCheckBox):
                return widget.isChecked()
            return getattr(widget, "text", lambda: None)()

        return item.text(column)

    def get_current_pos(self):
        item = self.widget.currentItem()
        if not item:
            return None
        return self._get_item_pos(item)

    def set_text(self, pos: list, column: int = 0, text: str = ""):
        item = self.get_item(pos)
        if not item:
            return False

        w = self.widget
        widget = w.itemWidget(item, column)

        if widget:
            if isinstance(widget, QComboBox):
                idx = widget.findText(text)
                if idx >= 0:
                    widget.setCurrentIndex(idx)
                else:
                    widget.addItem(text)
                    widget.setCurrentIndex(widget.count() - 1)
            else:
                widget.setText(text)
        else:
            item.setText(column, text)

        return True

    def set_cell_combo(self, pos: list, column: int, items: list, current_index=0):
        if column == 0:
            raise ValueError("첫 번째 컬럼에는 ComboBox 사용 불가")

        item = self.get_item(pos)
        if not item:
            return None

        combo = QComboBox(self.widget)
        combo.addItems(items)
        combo.setCurrentIndex(current_index)

        self.widget.setItemWidget(item, column, combo)
        return combo

    def set_cell_checkbox(self, pos: list, column: int, checked=False, text=""):
        if column == 0:
            raise ValueError("첫 번째 컬럼에는 CheckBox 사용 불가")

        item = self.get_item(pos)
        if not item:
            return None

        checkbox = QCheckBox(text, self.widget)
        checkbox.setChecked(checked)

        self.widget.setItemWidget(item, column, checkbox)
        return checkbox

    def get_cell_widget(self, pos: list, column: int):
        item = self.get_item(pos)
        return self.widget.itemWidget(item, column) if item else None

    def clear_all(self):
        self.widget.clear()
        self._editing = False

    def remove_item(self, pos: list):
        if not pos:
            return False

        w = self.widget

        if len(pos) == 1:
            index = pos[0]
            item = w.topLevelItem(index)
            if not item:
                return False
            w.takeTopLevelItem(index)
            self._editing = False
            return True

        parent = self.get_item(pos[:-1])
        if not parent:
            return False

        index = pos[-1]
        if index < 0 or index >= parent.childCount():
            return False

        parent.takeChild(index)
        self._editing = False
        return True
