import re
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QToolBar, QFrame
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
import pyqtgraph as pg


class ResidualPlotWidget(QWidget):
    # Signal emitted when refresh button is clicked
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = None
        self._current_log_path = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Toolbar
        self.toolbar = QToolBar(self)
        self._refresh_action = QAction("Refresh", self)
        self._refresh_action.setToolTip("Reload residual log file")
        self._refresh_action.triggered.connect(self._on_refresh)
        self.toolbar.addAction(self._refresh_action)
        layout.addWidget(self.toolbar)

        # 그래프 위젯을 감싸는 프레임 (Styled Panel)
        self.plot_frame = QFrame(self)
        self.plot_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.plot_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.plot_frame.setLineWidth(1)

        # 프레임 내부 레이아웃
        frame_layout = QVBoxLayout(self.plot_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        # 그래프 위젯 생성 (초기에는 빈 화면)
        self.plot_widget = pg.PlotWidget(background='#1e1e1e')
        frame_layout.addWidget(self.plot_widget)

        layout.addWidget(self.plot_frame, stretch=1)

        # Axis text color for dark theme
        axis_pen = pg.mkPen(color='#cccccc')
        for axis_name in ('bottom', 'left'):
            axis = self.plot_widget.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(axis_pen)

        # y축 로그 스케일
        self.plot_widget.setLogMode(y=True)

        # 그리드
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        # 축 라벨만 미리 지정해둠
        self.plot_widget.setLabel('bottom', 'Time', color='#cccccc')
        self.plot_widget.setLabel('left', 'Residual', color='#cccccc')

        # 색상/스타일
        self.curve_style = {
            'Ux': dict(pen=pg.mkPen(color='r', width=2)),
            'Uy': dict(pen=pg.mkPen(color='g', width=2)),
            'p': dict(pen=pg.mkPen(color='b', width=2)),
            'epsilon': dict(pen=pg.mkPen(color='m', width=2)),
            'k': dict(pen=pg.mkPen(color='c', width=2)),
        }

    def load_file(self, log_path: str):
        if not Path(log_path).is_file():
            return
        self._current_log_path = log_path
        self.data = self.parse_log_file(log_path)
        self.update_plot()

    def reload(self):
        """Reload the current log file."""
        if self._current_log_path:
            self.load_file(self._current_log_path)

    def _on_refresh(self):
        """Handle refresh button click."""
        if self._current_log_path:
            self.reload()
        self.refresh_requested.emit()

    def parse_log_file(self, path: str):
        time_values = []
        residuals = {
            'Ux': [],
            'Uy': [],
            'p': [],
            'epsilon': [],
            'k': []
        }

        current_time = None

        time_re = re.compile(r"^Time = (\d+)")
        res_re = re.compile(r"Solving for (\w+), .*Final residual = ([0-9.eE+-]+)")

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()

                # Time
                m = time_re.match(line)
                if m:
                    current_time = int(m.group(1))
                    time_values.append(current_time)
                    continue

                # Residual
                m = res_re.search(line)
                if m and current_time is not None:
                    var = m.group(1)
                    val = float(m.group(2))
                    if var in residuals:
                        residuals[var].append(val)

        return {
            'time': time_values,
            'residuals': residuals
        }

    def update_plot(self):
        self.plot_widget.clear()

        if self.data is None:
            return

        time = self.data['time']
        res = self.data['residuals']

        # 새로운 범례 추가
        self.legend = self.plot_widget.addLegend()

        # 각 변수별 residual plot
        for key in res.keys():
            if len(res[key]) == len(time):
                self.plot_widget.plot(
                    time,
                    res[key],
                    name=key,
                    **self.curve_style[key]
                )
