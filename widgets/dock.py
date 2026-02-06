import os
from dataclasses import dataclass
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout
from PySide6QtAds import CDockManager, CDockWidget, DockWidgetArea
from PySide6.QtCore import QObject, Signal

@dataclass
class DockInfo:
    dock: CDockWidget
    title: str
    show_state: bool
    position: DockWidgetArea

AREA_ENUM = {
    "center": None,
    "right": DockWidgetArea.RightDockWidgetArea,
    "left": DockWidgetArea.LeftDockWidgetArea,
    "top": DockWidgetArea.TopDockWidgetArea,
    "bottom": DockWidgetArea.BottomDockWidgetArea
}

def convert_to_dock_area(position):
    if isinstance(position, str):
        key = position.lower()
        return AREA_ENUM.get(key, DockWidgetArea.RightDockWidgetArea)
    elif isinstance(position, DockWidgetArea):
        return position
    else:
        return DockWidgetArea.RightDockWidgetArea


class DockWidget(QObject):
    count = 1
    visibility_changed = Signal(int, bool)   # number, show_state

    def __init__(self, parent=None, centralwidget=None, layout_file=None):
        super().__init__(parent)

        self.parent = parent
        if centralwidget is None:
            centralwidget = self.parent.ui.centralwidget
        self.docks_layout_file = layout_file

        self.docks = {}
        self.dock_container = QWidget(centralwidget)
        self.dock_layout = QVBoxLayout(self.dock_container)
        self.dock_layout.setContentsMargins(0, 0, 0, 0)

        if not self.parent.ui.centralwidget.layout():
            self.parent.ui.centralwidget.setLayout(QVBoxLayout())
        self.parent.ui.centralwidget.layout().addWidget(self.dock_container)

        self.dock_manager = CDockManager(self.dock_container)
        self.dock_layout.addWidget(self.dock_manager)

        # 독 탭 스타일 적용
        self._apply_tab_style()

        self.visibility_changed.emit(0, False)

    def _apply_tab_style(self):
        """독 탭바 스타일 적용 - 비활성 탭 가독성 향상."""
        self.dock_manager.setStyleSheet("""
            ads--CDockAreaTitleBar {
                background: palette(window);
                border-bottom: 1px solid palette(mid);
                padding: 0px;
            }

            ads--CDockWidgetTab {
                background: palette(window);
                border-top: 2px solid transparent;
                border-right: 1px solid palette(mid);
                padding: 2px 10px;
                min-width: 60px;
            }

            ads--CDockWidgetTab QLabel {
                color: palette(text);
                font-size: 10pt;
            }

            ads--CDockWidgetTab:hover {
                background: palette(midlight);
            }

            ads--CDockWidgetTab[activeTab="true"] {
                background: palette(base);
                border-top: 2px solid #3574C4;
            }

            ads--CDockWidgetTab[activeTab="true"] QLabel {
                color: palette(text);
                font-weight: bold;
            }

            /* Close button: hidden by default */
            ads--CDockWidgetTab #tabCloseButton {
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                max-width: 0px;
                max-height: 0px;
                icon-size: 0px;
            }

            /* Close button: visible on tab hover */
            ads--CDockWidgetTab:hover #tabCloseButton {
                max-width: 16px;
                max-height: 16px;
                icon-size: 12px;
                padding: 0px 2px;
            }

            ads--CDockWidgetTab:hover #tabCloseButton:hover {
                background: palette(mid);
                border-radius: 3px;
            }
        """)

    def add_center_dock(self, widget: QWidget, title = "Center Dock"):
        center_dock = CDockWidget(self.dock_manager, title, self.parent)

        if isinstance(widget, QMainWindow):
            widget.setStatusBar(None)
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, stretch=1)
            center_dock.setWidget(container)
        else:
            center_dock.setWidget(widget)

        self.dock_manager.setCentralWidget(center_dock)

        self.docks[0] = DockInfo(center_dock, title, True, "center")

    def add_side_dock(self, widget: QWidget, title = "Side Dock", area="right", is_tab = False):
        side_dock = CDockWidget(self.dock_manager, title, self.parent)

        if isinstance(widget, QMainWindow):
            widget.setStatusBar(None)
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(widget, stretch=1)
            side_dock.setWidget(container)
        else:
            side_dock.setWidget(widget)

        dock_area = convert_to_dock_area(area)
        if is_tab:
            self.dock_manager.addDockWidgetTab(dock_area, side_dock)
        else:
            self.dock_manager.addDockWidget(dock_area, side_dock)

        side_dock.visibilityChanged.connect(lambda visible, num=DockWidget.count: self.on_side_dock_visibility_changed(num, visible))

        self.docks[DockWidget.count] = DockInfo(side_dock, title, True, area)
        DockWidget.count += 1

    def on_side_dock_visibility_changed(self, number: int, visible: bool):
        if number > 0 and number in self.docks.keys():
            self.docks[number].show_state = visible
            self.visibility_changed.emit(number, self.docks[number].show_state)

    def change_dock_tab(self, number: int):
        if number > 0 and number in self.docks.keys():
            area = self.docks[number].dock.dockAreaWidget()
            if area:
                area.setCurrentDockWidget(self.docks[number].dock)

    def show_dock(self, number: int):
        dock_info = self.docks.get(number)
        if dock_info and not dock_info.dock.isVisible():
            self.dock_manager.addDockWidget(dock_info.position, dock_info.dock)
            dock_info.dock.show()
            dock_info.show_state = True

    def hide_dock(self, number: int):
        dock_info = self.docks.get(number)
        if dock_info and dock_info.dock.isVisible():
            self.dock_manager.removeDockWidget(dock_info.dock)
            dock_info.dock.hide()
            dock_info.show_state = False

    def toggle_dock(self, number: int):
        dock_info = self.docks.get(number)
        if dock_info and dock_info.dock.isVisible():
            self.hide_dock(self, number)
        else:
            self.show_dock(self, number)

    def set_tabify(self, number_src: int, number_sub: int):
        self.tabifyDockWidget


    def save_layout(self, filepath=None):
        if filepath is None:
            filepath = self.docks_layout_file
        if not filepath:
            return False
        try:
            state = self.dock_manager.saveState()
            with open(filepath, 'wb') as f:
                f.write(bytes(state))
            return True
        except Exception as e:
            print(f"Failed to save dock layout: {e}")
            return False

    def restore_layout(self, filepath=None):
        if filepath is None:
            filepath = self.docks_layout_file
        if not filepath or not os.path.exists(filepath):
            return False
        try:
            with open(filepath, 'rb') as f:
                state = f.read()
            return self.dock_manager.restoreState(state)
        except Exception as e:
            print(f"Failed to restore dock layout: {e}")
            return False


