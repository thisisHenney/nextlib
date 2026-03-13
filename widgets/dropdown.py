import os

from PySide6.QtCore import Qt, QPropertyAnimation, QSize, QEasingCurve, QAbstractAnimation, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy,
                               QScrollArea, QPushButton, QSpacerItem, QFrame, QApplication)

from nextlib.widgets.icon import create_icon


ICON_PATH = os.path.dirname(__file__) + "/icons"

_BTN_OPEN = (
    "QPushButton {"
    "  background: #f0f0f0;"
    "  border: none;"
    "  border-top-left-radius: 5px;"
    "  border-top-right-radius: 5px;"
    "  border-bottom-left-radius: 0px;"
    "  border-bottom-right-radius: 0px;"
    "  border-bottom: 1px solid #9ab0c8;"
    "  padding: 2px 10px;"
    "  text-align: left;"
    "  font-size: 9pt;"
    "  font-weight: bold;"
    "  color: #1a3a6a;"
    "}"
    "QPushButton:hover { background: #e0e0e0; }"
)

_BTN_CLOSED = (
    "QPushButton {"
    "  background: #f0f0f0;"
    "  border: none;"
    "  border-radius: 5px;"
    "  padding: 2px 10px;"
    "  text-align: left;"
    "  font-size: 9pt;"
    "  font-weight: bold;"
    "  color: #1a3a6a;"
    "}"
    "QPushButton:hover { background: #e0e0e0; }"
)

_FRAME_STYLE = (
    "QFrame#groupFrame {"
    "  border: 1px solid #9ab0c8;"
    "  border-radius: 6px;"
    "  background: #ffffff;"
    "}"
)


class DropDownItemWidget(QWidget):
    def __init__(self, name='', sub_widget=None, animation_time=100, scroll_area=None):
        super().__init__()

        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self.button = None
        self.is_entered = False
        self.sub_widget = sub_widget
        self.sub_widget_height = 0
        self._scroll_area = scroll_area

        self.animation = None
        self.animation_time = animation_time

        self.is_opened = False
        self.icon_opened = create_icon(ICON_PATH + '/opened.png')
        self.icon_closed = create_icon(ICON_PATH + '/closed.png')

        self._initialize(name)

    def _initialize(self, name):
        if name == '_SeparateLine_':
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            line.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            self._outer_layout.addWidget(line)
            return

        # Group frame container (blue border + rounded corners)
        self._frame = QFrame()
        self._frame.setObjectName("groupFrame")
        self._frame.setStyleSheet(_FRAME_STYLE)
        self._frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame_layout.setSpacing(0)

        # Header button
        self.button = QPushButton(name)
        self.button.setStyleSheet(_BTN_CLOSED)
        self.button.setCheckable(True)
        self.button.setIcon(self.icon_closed)
        self.button.clicked.connect(self.toggled_button)

        self._frame_layout.addWidget(self.button)

        # Content wrapper (holds sub_widget with padding)
        if self.sub_widget:
            self._content_wrap = QWidget()
            self._content_wrap.setObjectName("contentWrap")
            self._content_wrap.setStyleSheet("#contentWrap { border: none; background: transparent; }")
            _wrap_layout = QVBoxLayout(self._content_wrap)
            _wrap_layout.setContentsMargins(10, 8, 10, 12)
            _wrap_layout.setSpacing(0)
            _wrap_layout.addWidget(self.sub_widget)

            self._frame_layout.addWidget(self._content_wrap)
            self._init_widget_animation()
        else:
            self._content_wrap = None

        self._outer_layout.addWidget(self._frame)

    def _init_widget_animation(self):
        app_font = QApplication.font()
        pt = app_font.pointSize()
        if pt > 1:
            small_font = QFont(app_font)
            small_font.setPointSize(pt - 1)
            self.sub_widget.setFont(small_font)

        if self.animation_time == 0:
            self._content_wrap.hide()
        else:
            self._content_wrap.setMaximumHeight(0)

        self.animation = QPropertyAnimation(self._content_wrap, b"maximumHeight")
        self.animation.setDuration(self.animation_time)
        self.animation.setStartValue(0)
        self.animation.setEndValue(300)
        self.animation.setEasingCurve(QEasingCurve.InCubic)

    def toggled_button(self, checked):
        if not self.button:
            return
        if checked:
            self.is_opened = True
            self._animate_open()
            if self._scroll_area:
                delay = self.animation_time + 20
                QTimer.singleShot(delay, self._auto_scroll)
        else:
            self.is_opened = False
            self._animate_close()

    def _auto_scroll(self):
        if not self._scroll_area:
            return
        sa = self._scroll_area
        sb = sa.verticalScrollBar()
        viewport_h = sa.viewport().height()
        item_y = self.y()
        current = sb.value()
        if item_y > current + viewport_h // 2:
            sb.setValue(item_y)

    def open_button(self):
        if self.button and not self.button.isChecked():
            self.is_opened = True
            self.button.setChecked(True)
            self._animate_open()

    def close_button(self):
        if self.button and self.button.isChecked():
            self.is_opened = False
            self.button.setChecked(False)
            self._animate_close()

    def _animate_open(self):
        self.button.setIcon(self.icon_opened)
        self.button.setStyleSheet(_BTN_OPEN)
        if not self.animation or not self._content_wrap:
            return

        h = self._content_wrap.sizeHint().height()
        if h > 0:
            self.sub_widget_height = h
            self.animation.setEndValue(h)

        if self.animation_time == 0:
            self._content_wrap.show()
        else:
            self.animation.setDirection(QAbstractAnimation.Forward)
            self.animation.start()

    def _animate_close(self):
        self.button.setIcon(self.icon_closed)
        self.button.setStyleSheet(_BTN_CLOSED)
        if not self.animation or not self._content_wrap:
            return

        if self.animation_time == 0:
            self._content_wrap.hide()
        else:
            self.animation.setDirection(QAbstractAnimation.Backward)
            self.animation.start()

    def set_animation_time(self, value=100):
        self.animation_time = value
        if value == 0 and self._content_wrap and self._content_wrap.maximumHeight() == 0:
            h = self.sub_widget_height or self._content_wrap.sizeHint().height() or 300
            self._content_wrap.setMaximumHeight(h)
            self._content_wrap.hide()


class DropDown(QWidget):
    def __init__(self, layout):
        super().__init__()
        self._layout = QVBoxLayout(self)

        self.item_list = []

        self._initialize(layout)

    def _initialize(self, layout):
        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(6)

        if layout is not None:
            self._init_scroll_area(layout)

        self._spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addSpacerItem(self._spacer)

    def _init_scroll_area(self, layout):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QScrollArea.NoFrame)
        layout.addWidget(self.scroll_area)

    def set_defaults(self):
        for item in self.item_list:
            if item.sub_widget:
                item._frame_layout.removeWidget(item._content_wrap)
                item._content_wrap.layout().removeWidget(item.sub_widget)
                item.sub_widget.setParent(None)
            self._layout.removeWidget(item)
            item.deleteLater()
        self.item_list.clear()

    def add_item(self, title='', widget=None):
        sa = getattr(self, 'scroll_area', None)
        item = DropDownItemWidget(title, widget, scroll_area=sa)
        self.item_list.append(item)
        self._layout.insertWidget(self._layout.count() - 1, item)

    def insert_item(self, index, title='', widget=None):
        sa = getattr(self, 'scroll_area', None)
        item = DropDownItemWidget(title, widget, scroll_area=sa)
        self.item_list.insert(index, item)
        self._layout.insertWidget(index, item)

    def show_item(self, index):
        if 0 <= index < len(self.item_list):
            self.item_list[index].show()

    def hide_item(self, index):
        if 0 <= index < len(self.item_list):
            self.item_list[index].hide()

    def open_item(self, index):
        if 0 <= index < len(self.item_list):
            item = self.item_list[index]
            item.open_button()
            if hasattr(self, 'scroll_area'):
                delay = item.animation_time + 20
                QTimer.singleShot(delay, lambda: self.scroll_area.verticalScrollBar().setValue(item.y()))

    def close_item(self, index):
        if 0 <= index < len(self.item_list):
            self.item_list[index].close_button()
