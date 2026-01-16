import sys
import numpy as np
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure


class GraphManager:
    def __init__(self, axes):
        self.axes = axes
        self.lines = {}
        self.groups = {}

    def add_line(self, name: str, x_data, y_data, group=None, **style):
        if name in self.lines:
            raise ValueError(f"Line '{name}' already exists.")

        line, = self.axes.plot(x_data, y_data, label=name, **style)
        self.lines[name] = line

        if group:
            self.groups.setdefault(group, []).append(name)

        return line

    def remove_line(self, name: str):
        if name not in self.lines:
            return

        line = self.lines.pop(name)
        line.remove()

        for g, members in list(self.groups.items()):
            if name in members:
                members.remove(name)
                if not members:
                    self.groups.pop(g)

    def clear(self):
        for line in self.lines.values():
            line.remove()
        self.lines.clear()
        self.groups.clear()

    def set_style(self, name: str, **style):
        if name not in self.lines:
            return
        line = self.lines[name]
        self._apply_style(line, style)

    def set_group_style(self, group: str, **style):
        if group not in self.groups:
            return
        for line_name in self.groups[group]:
            self.set_style(line_name, **style)

    @staticmethod
    def _apply_style(line, style: dict):
        for key, val in style.items():
            setter = f"set_{key}"
            if hasattr(line, setter):
                getattr(line, setter)(val)
            else:
                line.set(**{key: val})


class ResidualPlotWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.fig = Figure(figsize=(5, 4), tight_layout=True)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.axes = self.fig.add_subplot(111)

        self.graph_manager = GraphManager(self.axes)

        layout.addWidget(self.canvas)

        self._setup_plot()

        self.dragging = False
        self.drag_start_xdata = None
        self.drag_start_xlim = None

        self.canvas.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas.mpl_connect("button_release_event", self.on_mouse_release)
        self.canvas.mpl_connect("motion_notify_event", self.on_mouse_move)

    def on_mouse_press(self, event):
        if event.button == 1 and event.inaxes == self.axes:  # 왼쪽 버튼
            self.dragging = True
            self.drag_start_xdata = event.xdata
            self.drag_start_xlim = self.axes.get_xlim()

    def on_mouse_release(self, event):
        if event.button == 1:
            self.dragging = False

    def on_mouse_move(self, event):
        if not self.dragging or event.inaxes != self.axes:
            return

        if self.drag_start_xdata is None:
            return

        x_now = event.xdata
        dx = x_now - self.drag_start_xdata

        x0, x1 = self.drag_start_xlim

        new_xlim = (x0 - dx, x1 - dx)

        self.axes.set_xlim(new_xlim)
        self.canvas.draw_idle()

    def _setup_plot(self):
        self.axes.set_title("OpenFOAM Residuals")
        self.axes.set_xlabel("Iteration")
        self.axes.set_ylabel("Residual Value")
        self.axes.grid(True)

    def refresh(self):
        self.axes.legend()
        self.canvas.draw_idle()

    def add_residual(self, name, x, y, group=None, **style):
        self.graph_manager.add_line(name, x, y, group=group, **style)
        self.refresh()

    def remove_residual(self, name):
        self.graph_manager.remove_line(name)
        self.refresh()

    def clear(self):
        self.graph_manager.clear()
        self.refresh()

    def set_style(self, name, **style):
        self.graph_manager.set_style(name, **style)
        self.refresh()

    def set_group_style(self, group, **style):
        self.graph_manager.set_group_style(group, **style)
        self.refresh()


def demo():
    app = QApplication(sys.argv)

    widget = ResidualPlotWidget()
    widget.show()

    widget.axes.set_yscale("log")

    times = np.linspace(0, 1000, 500)  # 0~5초 사이 50개 지점
    ux_res = 1e-1 * np.exp(-times * 1.2)
    uy_res = 2e-1 * np.exp(-times * 0.9)
    p_res  = 3e-1 * np.exp(-times * 1.5)

    widget.add_residual(
        "Ux", times, ux_res,
        group="velocity", color="blue", linestyle="-", alpha=0.9
    )
    widget.add_residual(
        "Uy", times, uy_res,
        group="velocity", color="green", linestyle="--", alpha=0.9
    )
    widget.add_residual(
        "p", times, p_res,
        group="pressure", color="red", linestyle="-.", alpha=0.9
    )

    widget.axes.set_xlabel("Time [s]")

    sys.exit(app.exec())


if __name__ == "__main__":
    demo()