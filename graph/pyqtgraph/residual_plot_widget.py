import re
from pathlib import Path
from PySide6.QtWidgets import QMainWindow, QVBoxLayout, QToolBar, QFrame
from PySide6.QtGui import QAction
from PySide6.QtCore import Signal
import pyqtgraph as pg


class ResidualPlotWidget(QMainWindow):
    # Signal emitted when refresh button is clicked
    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = None
        self._current_log_path = None
        self._drag_enabled = True
        self._auto_arrange = True

        self._setup_ui()
        self._build_toolbar()

    def _setup_ui(self):
        """UI layout setup (QMainWindow-based)."""
        # Toolbar (floatable, movable)
        self.toolbar = QToolBar("Residual Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)

        # Plot frame (Styled Panel)
        self.plot_frame = QFrame(self)
        self.plot_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.plot_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.plot_frame.setLineWidth(1)

        frame_layout = QVBoxLayout(self.plot_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        self.plot_widget = pg.PlotWidget(background='w')
        frame_layout.addWidget(self.plot_widget)

        self.setCentralWidget(self.plot_frame)

        # Plot configuration
        self.plot_widget.setLogMode(y=True)
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('bottom', 'Time')
        self.plot_widget.setLabel('left', 'Residual')

        # Curve styles
        self.curve_style = {
            'Ux': dict(pen=pg.mkPen(color='r', width=2)),
            'Uy': dict(pen=pg.mkPen(color='g', width=2)),
            'p': dict(pen=pg.mkPen(color='b', width=2)),
            'epsilon': dict(pen=pg.mkPen(color='m', width=2)),
            'k': dict(pen=pg.mkPen(color='c', width=2)),
        }

    def _build_toolbar(self):
        """Build toolbar with actions."""
        # Refresh
        self._refresh_action = QAction("\u21BB", self)
        self._refresh_action.setToolTip("Refresh")
        self._refresh_action.triggered.connect(self._on_refresh)
        self.toolbar.addAction(self._refresh_action)

        self.toolbar.addSeparator()

        # Drag/Pan toggle
        self._drag_action = QAction("\u2726", self)
        self._drag_action.setToolTip("Drag/Pan: On")
        self._drag_action.setCheckable(True)
        self._drag_action.setChecked(True)
        self._drag_action.triggered.connect(self._on_drag_toggled)
        self.toolbar.addAction(self._drag_action)

        # Auto Arrange toggle
        self._auto_action = QAction("\u2922", self)
        self._auto_action.setToolTip("Auto Arrange: On")
        self._auto_action.setCheckable(True)
        self._auto_action.setChecked(True)
        self._auto_action.triggered.connect(self._on_auto_arrange_toggled)
        self.toolbar.addAction(self._auto_action)

    def _on_drag_toggled(self, checked):
        """Toggle mouse drag/pan on the plot."""
        self._drag_enabled = checked
        vb = self.plot_widget.getViewBox()
        vb.setMouseEnabled(x=checked, y=checked)
        self._drag_action.setToolTip("Drag/Pan: On" if checked else "Drag/Pan: Off")

    def _on_auto_arrange_toggled(self, checked):
        """Toggle auto-range on the plot."""
        self._auto_arrange = checked
        vb = self.plot_widget.getViewBox()
        if checked:
            vb.enableAutoRange()
        else:
            vb.disableAutoRange()
        self._auto_action.setToolTip("Auto Arrange: On" if checked else "Auto Arrange: Off")

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

        self.legend = self.plot_widget.addLegend()

        for key in res.keys():
            if len(res[key]) == len(time):
                self.plot_widget.plot(
                    time,
                    res[key],
                    name=key,
                    **self.curve_style[key]
                )

        if self._auto_arrange:
            self.plot_widget.getViewBox().enableAutoRange()
