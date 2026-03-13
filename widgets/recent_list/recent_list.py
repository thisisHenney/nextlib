from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtWidgets import QLabel, QPushButton, QListWidget, QListWidgetItem
from PySide6.QtCore import Signal

from nextlib.utils.ui import load_ui
from nextlib.tools.json_tool import JsonTool
from nextlib.widgets.recent_list.view.recent_list_ui import Ui_RecentListForm
from nextlib.widgets.messagebox import messagebox_warning


class RecentItemWidget(QWidget):
    removing = Signal(QWidget)

    def __init__(self, item, name, path):
        super().__init__()

        self.item = item
        self.name = name
        self.path = path

        self._is_removed = False
        self.func_clicked_item = None

        self._initialize(name, path)

    def _initialize(self, name, path):
        self.base_layout = QHBoxLayout()
        self.base_layout.setContentsMargins(5, 5, 10, 5)

        namepath_layout = QVBoxLayout()

        name_label = QLabel(name)
        name_label.setStyleSheet('border: none; font-weight: bold; background: transparent;')

        path_label = QLabel(path)
        path_label.setStyleSheet('border: none; color: gray; background: transparent;')

        namepath_layout.addWidget(name_label)
        namepath_layout.addWidget(path_label)
        self.base_layout.addLayout(namepath_layout)

        self.pushButton_remove = QPushButton('✕')
        self.pushButton_remove.setStyleSheet("""
        QPushButton {
            text-align: center;
            background-color: darkorange;
            color: white;
            border-radius: 3px;
            padding: 0px;
            font-size: 9pt;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #FCBE4C;
        }
        QPushButton:pressed {
            background: #DBB239;
        }
        """)
        self.pushButton_remove.clicked.connect(self.remove_current_item)
        self.pushButton_remove.setFixedSize(18, 18)
        self.pushButton_remove.setVisible(False)
        self.base_layout.addWidget(self.pushButton_remove)

        self.setLayout(self.base_layout)

    def enterEvent(self, event):
        self.pushButton_remove.setVisible(True)
        self.base_layout.setContentsMargins(7, 5, 10, 5)

    def leaveEvent(self, event):
        self.pushButton_remove.setVisible(False)
        self.base_layout.setContentsMargins(5, 5, 10, 5)

    def get_removed(self):
        return self._is_removed

    def remove_current_item(self, question=True):
        if question:
            result = messagebox_warning(self, "Remove item", f"Remove '{self.name}' from recent project list?")
            if not result:
                return
        self._is_removed = True
        self.removing.emit(self)


class RecentList(QWidget):
    def __init__(self):
        super().__init__()

        self._ui = load_ui(self, Ui_RecentListForm)

        self.name_list = []
        self.path_list = []
        self.item_list = []    # list of RecentItemWidget
        self.widget_list = []  # list of QListWidgetItem

        self.selected_index = -1
        self.selected_name = ''
        self.selected_path = ''
        self.selected_item = None
        self.selected_widget = None

        self.func_clicked_item = None

        self.list_info = JsonTool()

        self._initialize()

    def _initialize(self):
        self._ui.lineEdit_search.textChanged.connect(self._reload_list)
        self._ui.listWidget.itemClicked.connect(self._clicked_list_item)

    def _clicked_list_item(self, item):
        for i, widget_item in enumerate(self.widget_list):
            if widget_item is item:
                self.selected_index = i
                self.selected_name = self.name_list[i]
                self.selected_path = self.path_list[i]
                self.selected_item = self.item_list[i]
                self.selected_widget = self.widget_list[i]
                self._run_func_clicked_item()
                break

    def set_func_clicked_item(self, func=None):
        self.func_clicked_item = func

    def _run_func_clicked_item(self):
        if self.func_clicked_item is not None:
            self.func_clicked_item()

    def _reload_list(self, text):
        if not text:
            for item in self.widget_list:
                item.setHidden(False)
            return

        text = text.lower()
        for i, item in enumerate(self.widget_list):
            visible = text in self.name_list[i].lower() or text in self.path_list[i].lower()
            item.setHidden(not visible)

    def get_ui(self):
        return self._ui

    def set_file_name(self, path=''):
        if not self.list_info.read(path):
            self.list_info.create(path)

    def set_layout(self, layout):
        layout.addWidget(self)

    def set_defaults(self):
        data = self.list_info._buffer
        if data:
            for name in reversed(list(data.keys())):
                path = self.list_info.get(f'{name}.path')
                self._add_item_ui_only(name, path)

    def find_item(self, name, path):
        for i in range(min(len(self.name_list), len(self.path_list))):
            if self.name_list[i] == name and self.path_list[i] == path:
                return i
        return -1

    def _add_item_ui_only(self, name, path):
        """Add item to UI without touching JSON (used during loading)."""
        index = self.find_item(name, path)
        if index >= 0:
            self._remove_item_ui_only(index)

        item = QListWidgetItem()
        item_widget = RecentItemWidget(item, name, path)
        item_widget.removing.connect(self._on_item_removing)
        item.setSizeHint(item_widget.sizeHint())

        self._ui.listWidget.addItem(item)
        self._ui.listWidget.setItemWidget(item, item_widget)

        self.name_list.append(name)
        self.path_list.append(path)
        self.item_list.append(item_widget)
        self.widget_list.append(item)

    def add_item(self, name, path):
        self._add_item_ui_only(name, path)
        self.list_info.add(name, {'path': path})
        self.list_info.save()

    def _on_item_removing(self, item_widget):
        for i, d in enumerate(self.item_list):
            if d is item_widget:
                self.selected_index = i
                self.selected_name = self.name_list[i]
                self.selected_path = self.path_list[i]
                self.selected_item = self.item_list[i]
                self.selected_widget = self.widget_list[i]
                self.remove_item(i)
                break

    def _remove_item_ui_only(self, index):
        if 0 <= index < len(self.widget_list):
            row = self._ui.listWidget.row(self.widget_list[index])
            self._ui.listWidget.takeItem(row)
            del self.name_list[index]
            del self.path_list[index]
            del self.item_list[index]
            del self.widget_list[index]

    def remove_item(self, index=-1):
        if 0 <= index < len(self.widget_list):
            self.list_info.remove(self.name_list[index])
            self.list_info.save()
            self._remove_item_ui_only(index)

    def remove_current_item(self):
        if 0 <= self.selected_index < len(self.widget_list):
            self.selected_item.remove_current_item(question=False)

    def show_item(self, index=0):
        if 0 <= index < len(self.widget_list):
            self.widget_list[index].setHidden(False)

    def hide_item(self, index=0):
        if 0 <= index < len(self.widget_list):
            self.widget_list[index].setHidden(True)
