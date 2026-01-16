import os
import re
import time
import numpy as np
from collections import defaultdict, deque
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout
import pyqtgraph as pg


class FoamWatcherThread(QThread):
    parsed_data = Signal(dict)

    file_waiting = Signal()
    file_detected = Signal(str)
    started_plotting = Signal()
    stalled = Signal()
    stopped = Signal()

    def __init__(self, case_path: str, interval_ms: int = 200,
                 max_points: int = 2000, stall_timeout: float = 5.0, parent=None):
        super().__init__(parent)
        self.case_path = case_path
        self.interval = interval_ms / 1000.0
        self.max_points = max_points
        self.stall_timeout = stall_timeout
        self.running = False

        self.last_log_pos = 0
        self.fields = defaultdict(lambda: deque(maxlen=max_points))
        self.time_list = deque(maxlen=max_points)

        self.detected_log = None
        self.last_update_time = None
        self.plot_started_emitted = False

    def _wait_for_log_file(self):
        while self.running:
            candidates = [f for f in os.listdir(self.case_path) if f.startswith("log.")]
            if candidates:
                self.detected_log = os.path.join(self.case_path, candidates[0])
                self.file_detected.emit(self.detected_log)
                return

            self.file_waiting.emit()
            time.sleep(0.5)

    def _parse_log_line(self, line):
        res_match = re.search(r"Solving for (\w+),.*Initial residual = ([\d\.Ee+-]+)", line)
        cr_match = re.search(r"Courant Number:\s*([\d\.Ee+-]+)", line)
        results = {}

        if res_match:
            field = res_match.group(1)
            results[field] = float(res_match.group(2))
        if cr_match:
            results["Co"] = float(cr_match.group(1))

        return results

    def _tail_log_file(self):
        if not self.detected_log or not os.path.exists(self.detected_log):
            return {}

        results = {}
        with open(self.detected_log, "r") as f:
            f.seek(self.last_log_pos)
            lines = f.readlines()
            self.last_log_pos = f.tell()

        for line in lines:
            parsed = self._parse_log_line(line)
            if parsed:
                results.update(parsed)

        return results

    def run(self):
        self.running = True

        self._wait_for_log_file()

        current_time = 0.0
        self.last_update_time = time.time()

        while self.running:
            parsed = self._tail_log_file()

            if parsed:
                current_time += 1.0
                self.time_list.append(current_time)

                for key, val in parsed.items():
                    self.fields[key].append(val)

                self.parsed_data.emit({
                    "time": list(self.time_list),
                    "fields": {k: list(v) for k, v in self.fields.items()}
                })

                self.last_update_time = time.time()

                if not self.plot_started_emitted:
                    self.started_plotting.emit()
                    self.plot_started_emitted = True

            if time.time() - self.last_update_time > self.stall_timeout:
                self.stalled.emit()
                self.last_update_time = time.time()

            time.sleep(self.interval)

        self.stopped.emit()

    def stop(self):
        self.running = False
        self.wait(1000)


class FoamLivePlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        pg.setConfigOptions(antialias=True, foreground="w", background="k")

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.addLegend()
        self.plot_widget.setLabel("bottom", "Iteration")
        self.plot_widget.setLabel("left", "Residual")
        self.plot_widget.setBackground('w')

        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.setTitle("Residual")
        self.plot_item.setLogMode(x=False, y=True)
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)

        left_axis = self.plot_item.getAxis('left')
        left_axis.setGrid(False)
        left_axis.enableAutoSIPrefix(True)
        left_axis.setPen('k')
        left_axis.setTextPen('k')
        left_axis.setStyle(tickLength=-5)

        bottom_axis = self.plot_item.getAxis('bottom')
        bottom_axis.setGrid(False)
        bottom_axis.enableAutoSIPrefix(True)
        bottom_axis.setPen('k')
        bottom_axis.setTextPen('k')
        bottom_axis.setStyle(tickLength=-5)

        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_widget)

        self.case_path = ""
        self.thread = None
        self.curves = {}

        self.use_log_scale = False
        self.apply_log_scale(False)

        self.colors = [
            "#FF0000", "#00FF00", "#00BFFF", "#FFFF00",
            "#FF00FF", "#00FFFF", "#FFA500", "#FFFFFF",
        ]

        self.styles = [
            pg.QtCore.Qt.SolidLine,
            pg.QtCore.Qt.DashLine,
            pg.QtCore.Qt.DotLine,
            pg.QtCore.Qt.DashDotLine,
        ]

    def apply_log_scale(self, enabled: bool):
        self.use_log_scale = enabled
        self.plot_widget.setLogMode(y=enabled)

    def set_case_path(self, path: str):
        self.case_path = path

    def start(self, interval_ms: int = 200, max_points: int = 2000):
        if not self.case_path:
            print("Case path not set.")
            return

        if self.thread:
            self.stop()

        self.thread = FoamWatcherThread(
            case_path=self.case_path,
            interval_ms=interval_ms,
            max_points=max_points
        )

        self.thread.file_waiting.connect(self._on_file_waiting)
        self.thread.file_detected.connect(self._on_file_detected)
        self.thread.started_plotting.connect(self._on_started_plotting)
        self.thread.stalled.connect(self._on_stalled)
        self.thread.stopped.connect(self._on_stopped)

        self.thread.parsed_data.connect(self.update_graph)
        self.thread.start()

    def stop(self):
        if self.thread:
            self.thread.stop()
            self.thread = None

    def reset(self):
        self.stop()
        self.plot_widget.clear()
        self.plot_widget.addLegend()
        self.curves.clear()

    def _generate_pen(self, index: int):
        color = self.colors[index % len(self.colors)]
        style = self.styles[(index // len(self.colors)) % len(self.styles)]
        return pg.mkPen(color=color, width=2, style=style)

    # def _on_file_waiting(self):
    #     print("[Info] Waiting for log file...")
    #
    # def _on_file_detected(self, path):
    #     print(f"[Info] Log file detected: {path}")
    #
    # def _on_started_plotting(self):
    #     print("[Info] Live plotting started.")
    #
    # def _on_stalled(self):
    #     print("[Warning] Plot stalled (no updates).")
    #
    # def _on_stopped(self):
    #     print("[Info] Watcher stopped.")

    def update_graph(self, data: dict):
        time_list = data["time"]
        fields = data["fields"]

        for idx, (key, values) in enumerate(fields.items()):
            if key not in self.curves:
                pen = self._generate_pen(idx)
                curve = self.plot_widget.plot(
                    time_list, values,
                    pen=pen,
                    name=key
                )
                self.curves[key] = curve
            else:
                self.curves[key].setData(time_list, values)
