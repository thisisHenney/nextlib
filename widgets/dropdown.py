import os

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QSizePolicy,
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
    "  padding: 2px 10px 2px 5px;"
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
    "  padding: 2px 10px 2px 5px;"
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

        self._frame = QFrame()
        self._frame.setObjectName("groupFrame")
        self._frame.setStyleSheet(_FRAME_STYLE)
        self._frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        self._frame_layout = QVBoxLayout(self._frame)
        self._frame_layout.setContentsMargins(0, 0, 0, 0)
        self._frame_layout.setSpacing(0)

        self.button = QPushButton(name)
        self.button.setStyleSheet(_BTN_CLOSED)
        self.button.setCheckable(True)
        self.button.setIcon(self.icon_closed)
        self.button.clicked.connect(self.toggled_button)

        self._frame_layout.addWidget(self.button)

        if self.sub_widget:
            self._content_wrap = QWidget()
            self._content_wrap.setObjectName("contentWrap")
            self._content_wrap.setStyleSheet("#contentWrap { border: none; background: transparent; }")
            _wrap_layout = QVBoxLayout(self._content_wrap)
            _wrap_layout.setContentsMargins(4, 6, 4, 8)
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
        """헤더 버튼 클릭 처리. 클릭 즉시 열고/닫는다(지연 없음).
        (더블클릭 시 아주 짧게 열렸다 닫히는 깜빡임이 있을 수 있지만, 매 클릭마다
        더블클릭 판정 시간만큼 지연시키는 쪽이 체감상 훨씬 느리고 불편해서 되돌림)"""
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
        if not self.button:
            return
        # 버튼 체크 상태가 아니라 논리 상태(is_opened)를 기준으로 판단한다.
        # 헤더 클릭 직후(버튼은 이미 체크, 토글은 대기 중)에 불려도 어긋나지 않게 버튼을 맞춘다.
        self.button.setChecked(True)
        if not self.is_opened:
            self.is_opened = True
            self._animate_open()

    def close_button(self):
        if not self.button:
            return
        self.button.setChecked(False)
        if self.is_opened:
            self.is_opened = False
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

        # 스크롤 영역 맨 아래에 뷰포트 높이만큼 여백을 둬서, 아래쪽에 남은 콘텐츠가
        # 부족해도 어떤 항목이든 맨 위까지 스크롤할 수 있게 한다 (open_item에서 크기 갱신)
        self._bottom_pad = QWidget()
        self._bottom_pad.setFixedHeight(0)
        self._layout.addWidget(self._bottom_pad)

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
        self._layout.insertWidget(len(self.item_list) - 1, item)

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

    def show_only(self, indices):
        """열림/닫힘 상태는 그대로 두고, indices에 해당하는 항목만 보이게 하고 나머지는 숨긴다"""
        keep = set(indices)
        for i in range(len(self.item_list)):
            if i in keep:
                self.show_item(i)
            else:
                self.hide_item(i)

    def show_all(self):
        for i in range(len(self.item_list)):
            self.show_item(i)

    def open_item(self, index):
        if 0 <= index < len(self.item_list):
            item = self.item_list[index]
            item.open_button()
            delay = item.animation_time + 20
            self._scroll_item_to_top(index, delay)

    def close_item(self, index):
        if 0 <= index < len(self.item_list):
            self.item_list[index].close_button()

    def scroll_to_item(self, index):
        """열림/닫힘 상태는 건드리지 않고, 해당 항목을 뷰포트 맨 위로 이동만 시킨다.
        직전에 show_all()/show_only()로 다른 항목들의 visible 상태가 바뀌었을 수 있는데,
        그 레이아웃 재계산이 끝나기 전에 item.y()를 읽으면 옛 위치로 스크롤돼버린다
        (특히 대상 항목이 이미 펼쳐진 상태일 때 두드러짐). open_item()과 마찬가지로
        약간 지연시켜 레이아웃이 안정된 뒤 위치를 읽는다."""
        self._scroll_item_to_top(index, 20)

    def _scroll_item_to_top(self, index, delay):
        if not (0 <= index < len(self.item_list)):
            return
        item = self.item_list[index]
        if not hasattr(self, 'scroll_area'):
            return
        sa = self.scroll_area
        if hasattr(self, '_bottom_pad'):
            self._bottom_pad.setFixedHeight(sa.viewport().height())
        QTimer.singleShot(delay, lambda: sa.verticalScrollBar().setValue(item.y()))

    def is_item_open(self, index):
        if 0 <= index < len(self.item_list):
            return self.item_list[index].is_opened
        return False
