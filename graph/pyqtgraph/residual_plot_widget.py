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
        self._target_vars = None  # None = all variables
        self._drag_enabled = True
        self._auto_arrange = True

        # 증분 파싱 상태
        self._incr_offset: int = 0
        self._incr_data: dict = {'time': [], 'residuals': {}}
        self._incr_partial_time = None
        self._incr_partial_res: dict = {}

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
            'Ux':      dict(pen=pg.mkPen(color='r',                  width=2)),
            'Uy':      dict(pen=pg.mkPen(color='g',                  width=2)),
            'Uz':      dict(pen=pg.mkPen(color=(255, 128, 0),        width=2)),
            'p':       dict(pen=pg.mkPen(color='b',                  width=2)),
            'epsilon': dict(pen=pg.mkPen(color='m',                  width=2)),
            'k':       dict(pen=pg.mkPen(color='c',                  width=2)),
            'h':       dict(pen=pg.mkPen(color=(255, 200, 0),        width=2)),
            'rho':     dict(pen=pg.mkPen(color=(180, 100, 255),      width=2)),
        }
        # Fallback colors for unexpected variables not in curve_style
        self._fallback_colors = [
            (200, 200, 200), (100, 255, 150), (255, 100, 150),
            (100, 200, 255), (255, 180, 100),
        ]

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

    def reset_incremental(self):
        """증분 파싱 상태 초기화 (새 솔버 실행 시 호출)."""
        self._incr_offset = 0
        self._incr_data = {'time': [], 'residuals': {}}
        self._incr_partial_time = None
        self._incr_partial_res = {}

    def load_file_incremental(self, log_path: str, target_vars=None):
        """증분 파싱: 마지막 읽은 위치부터만 새로 파싱하여 성능 향상."""
        if not Path(log_path).is_file():
            return

        # 파일 경로나 target_vars가 바뀌면 전체 재파싱
        if log_path != self._current_log_path or target_vars != self._target_vars:
            self.reset_incremental()
            self._current_log_path = log_path
            self._target_vars = target_vars

        target_set = set(target_vars) if target_vars is not None else None
        time_re = re.compile(r"^Time = ([0-9.eE+-]+)")
        res_re  = re.compile(r"Solving for (\w+),.*?Final residual = ([0-9.eE+-]+)")

        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(self._incr_offset)
            for line in f:
                line_s = line.strip()

                m = time_re.match(line_s)
                if m:
                    # 이전 타임스텝 플러시
                    if self._incr_partial_time is not None and self._incr_partial_res:
                        self._incr_data['time'].append(self._incr_partial_time)
                        n = len(self._incr_data['time'])
                        for var, val in self._incr_partial_res.items():
                            self._incr_data['residuals'].setdefault(var, []).append(val)
                        for var in self._incr_data['residuals']:
                            while len(self._incr_data['residuals'][var]) < n:
                                self._incr_data['residuals'][var].append(None)
                    self._incr_partial_time = float(m.group(1))
                    self._incr_partial_res = {}
                    continue

                m = res_re.search(line_s)
                if m and self._incr_partial_time is not None:
                    var = m.group(1)
                    if target_set is None or var in target_set:
                        val = float(m.group(2))
                        self._incr_partial_res[var] = max(self._incr_partial_res.get(var, 0.0), val)

            self._incr_offset = f.tell()

        self.data = self._incr_data
        self.update_plot()

    def load_file(self, log_path: str, target_vars=None):
        if not Path(log_path).is_file():
            return
        self._current_log_path = log_path
        self._target_vars = target_vars
        self.data = self.parse_log_file(log_path, target_vars)
        self.update_plot()

    def reload(self):
        """Reload the current log file."""
        if self._current_log_path:
            self.load_file(self._current_log_path, self._target_vars)

    def _on_refresh(self):
        """Handle refresh button click."""
        if self._current_log_path:
            self.reload()
        self.refresh_requested.emit()

    def parse_log_file(self, path: str, target_vars=None):
        # time → {var: last_final_residual} per timestep
        # target_vars: set/list of variable names to collect, None = all
        time_values = []
        residuals = {}   # var -> [value per timestep]

        target_vars = set(target_vars) if target_vars is not None else None

        current_time = None
        current_res = {}  # var -> latest Final residual in this timestep

        time_re = re.compile(r"^Time = ([0-9.eE+-]+)")
        res_re  = re.compile(r"Solving for (\w+),.*?Final residual = ([0-9.eE+-]+)")

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()

                m = time_re.match(line)
                if m:
                    # Flush previous timestep
                    if current_time is not None:
                        time_values.append(current_time)
                        for var, val in current_res.items():
                            residuals.setdefault(var, []).append(val)
                        # Fill missing vars with None for this timestep
                        for var in residuals:
                            if len(residuals[var]) < len(time_values):
                                residuals[var].append(None)
                    current_time = float(m.group(1))
                    current_res = {}
                    continue

                m = res_re.search(line)
                if m and current_time is not None:
                    var = m.group(1)
                    if target_vars is None or var in target_vars:
                        val = float(m.group(2))
                        # Keep maximum across regions (CHTMultiRegionFoam reports same var per region)
                        current_res[var] = max(current_res.get(var, 0.0), val)

        # Flush last timestep
        if current_time is not None and current_res:
            time_values.append(current_time)
            for var, val in current_res.items():
                residuals.setdefault(var, []).append(val)
            for var in residuals:
                if len(residuals[var]) < len(time_values):
                    residuals[var].append(None)

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

        fallback_idx = 0
        for key, values in res.items():
            # Filter out None (missing timesteps) and align time axis
            pairs = [(t, v) for t, v in zip(time, values) if v is not None]
            if not pairs:
                continue
            t_arr, v_arr = zip(*pairs)

            style = self.curve_style.get(key)
            if style is None:
                color = self._fallback_colors[fallback_idx % len(self._fallback_colors)]
                fallback_idx += 1
                style = dict(pen=pg.mkPen(color=color, width=2))

            self.plot_widget.plot(list(t_arr), list(v_arr), name=key, **style)

        if self._auto_arrange:
            self.plot_widget.getViewBox().enableAutoRange()
