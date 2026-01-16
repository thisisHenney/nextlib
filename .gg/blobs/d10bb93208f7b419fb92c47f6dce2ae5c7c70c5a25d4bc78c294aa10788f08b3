from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QWidget
from PySide6QtAds import CDockManager, CDockWidget, DockWidgetArea


class DockWidget(CDockWidget):
    _count = 0

    def __init__(self, widget, title):
        super().__init__(title)
        self.widget = widget
        self.title = title

        self._number = DockWidget._count
        DockWidget._count += 1


class DockManager(QObject):
    added = Signal(int)
    closed = Signal(int)
    shown = Signal(int)
    hidden = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._manager = CDockManager(parent)
        self._docks = [None]    # 0:Cental dock, 1~:Side Docks

        self._bind_events()

    def _bind_events(self):
        self.added.connect(self._on_added)
        self.closed.connect(self._on_closed)
        self.shown.connect(self._on_shown)
        self.hidden.connect(self._on_hidden)

    def _on_added(self, number):
        self.on_added_task(number)

    def on_added_task(self, number):
        ...

    def _on_closed(self, number):
        self.on_closed_task(number)

    def on_closed_task(self, number):
        ...

    def _on_shown(self, number):
        self.on_shown_task(number)

    def on_shown_task(self, number):
        ...

    def _on_hidden(self, number):
        self.on_hidden_task(number)

    def on_hidden_task(self, number):
        ...

    def set_central_dock(self, widget, title='Main'):
        dock = DockWidget(widget, title)
        dock.setWidget(widget)

        self._manager.setCentralWidget(dock)
        self._central_dock = dock
        return dock

    def add(self, widget, title='Dock', position='Right'):
        dock = DockWidget(widget, title)
        dock.closed.connect(lambda dw=dock_widget: self.close(dw.number))
        dock.setWidget(widget)
        dock.setFeature(CDockWidget.DockWidgetDeleteOnClose, True)

        area = self.set_position(posiiton)
        self._manager.addDockWidget(area, dock)
        self._docks.append(dock)

        self.added.emit(dock.number)
        return dock_widget

    def set_position(self, position='Right'):
        if position == 'Left':
            area = DockWidgetArea.LeftDockWidgetArea
        elif position == 'Bottom':
            area = DockWidgetArea.BottomDockWidgetArea
        elif position == 'Top':
            area = DockWidgetArea.TopDockWidgetArea
        else:   # position == 'Right': # Default
            area = DockWidgetArea.RightDockWidgetArea
        return area

    def set_margins(self, number, margins=(0, 0, 0, 0)):   # (left, top, right, bottom)
        self._docks[number].setContentsMargins(*margins)

    def get_title(self, number):
        return self._docks[number].title

    def get_widget(self, number):
        return self._docks[number].widget

    def show(self, number):
        dock_widget = self._docks[number]
        # dock_widget.toggleView(True)
        self.shown.emit(number)

    def hide(self, number):
        dock_widget = self._dock_widgets[number]
        # dock_widget.setVisible(False)
        self.hidden.emit(number)

    def close(self, dock):
        dock_widget = self._dock_widgets[dock]
        # dock_widget.deleteDockWidget()
        dock_widget.toggleView(False)
        self.closed.emit(dock)

