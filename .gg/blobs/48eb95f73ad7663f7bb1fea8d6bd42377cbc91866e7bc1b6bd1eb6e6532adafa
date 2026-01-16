import sys
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
import pyqtgraph as pg


class GraphManager:
    def __init__(self, plot_widget: pg.PlotWidget, auto_scale_callback=None):
        self.plot_widget = plot_widget
        self.graphs = {}
        self.groups = {}
        self.auto_scale_callback = auto_scale_callback

    def add_graph(self, id: int, name: str, data, group: int = 0, pen=None):
        if id in self.graphs:
            self.remove_graph(id)

        if isinstance(data, (list, tuple)) and len(data) == 2:
            x, y = data
        else:
            y = list(data)
            x = list(range(len(y)))

        if pen is None:
            pen = pg.mkPen(width=2)

        plot_item = self.plot_widget.plot(x, y, pen=pen, name=name)

        self.graphs[id] = {'plot': plot_item, 'name': name, 'group': group}
        self.groups.setdefault(group, []).append(id)

        self._reorder_graphs()

        if callable(self.auto_scale_callback):
            self.auto_scale_callback()

    def remove_graph(self, id: int):
        if id not in self.graphs:
            return
        graph = self.graphs.pop(id)
        try:
            self.plot_widget.removeItem(graph['plot'])
        except Exception:
            pass
        grp = graph['group']
        if grp in self.groups:
            if id in self.groups[grp]:
                self.groups[grp].remove(id)
            if not self.groups[grp]:
                del self.groups[grp]

    def _reorder_graphs(self):
        sorted_ids = sorted(self.graphs.keys())
        base = 1000
        for idx, gid in enumerate(sorted_ids):
            z = base - idx
            item = self.graphs[gid]['plot']
            try:
                item.setZValue(z)
            except Exception:
                pass

    def set_group_visible(self, group: int, visible: bool):
        for gid in self.groups.get(group, []):
            self.graphs[gid]['plot'].setVisible(visible)

    def clear(self):
        for gid in list(self.graphs.keys()):
            self.remove_graph(gid)


class QtGraphWidget(QWidget):
    def __init__(self, parent=None, allow_vertical_pan: bool = True):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLogMode(x=False, y=True)
        self.plot_widget.showGrid(x=True, y=True)
        self.plot_widget.addLegend()

        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setClipToView(True)
        self.plot_widget.getAxis('bottom').setTickSpacing(major=1.0, minor=None)
        self.plot_widget.getAxis('left').setTickSpacing(major=None, minor=None)

        vb = self.plot_widget.getViewBox()
        vb.setMouseEnabled(x=True, y=allow_vertical_pan)
        vb.setMouseMode(pg.ViewBox.PanMode)

        layout.addWidget(self.plot_widget)

        self.graph_manager = GraphManager(
            self.plot_widget,
            auto_scale_callback=self.update_auto_scale
        )

        self.auto_scale_x = True
        self.auto_scale_y = True
        self._init_range_done = False

    def add_graph(self, id: int, name: str, data, group: int = 0, pen=None):
        self.graph_manager.add_graph(id, name, data, group, pen)
        # self.add_graph(0, "Ux residual", (time, ux_res))
        # self.add_graph(1, "Uy residual", (time, uy_res))

    def remove_graph(self, id: int):
        self.graph_manager.remove_graph(id)

    def set_group_visible(self, group: int, visible: bool):
        self.graph_manager.set_group_visible(group, visible)

    def clear(self):
        self.graph_manager.clear()

    def set_axis_labels(self, xlabel: str = "", ylabel: str = ""):
        self.plot_widget.setLabel('bottom', xlabel)
        self.plot_widget.setLabel('left', ylabel)

    def update_auto_scale(self):
        vb = self.plot_widget.getViewBox()

        if not self.graph_manager.graphs:
            return

        all_x, all_y = [], []
        for g in self.graph_manager.graphs.values():
            data = g['plot'].getData()
            if data is not None and len(data) == 2:
                x, y = data
                all_x.extend(x)
                all_y.extend(y)

        if not all_x or not all_y:
            return

        import numpy as np
        x_min, x_max = np.min(all_x), np.max(all_x)
        y_min, y_max = np.min(all_y), np.max(all_y)

        if y_min <= 0:
            y_min = 1e-8

        if not self._init_range_done:
            vb.setXRange(x_min, x_max, padding=0.05)
            vb.setYRange(y_min, y_max, padding=0.2)
            self._init_range_done = True
        else:
            current_x_min, current_x_max = vb.viewRange()[0]
            current_y_min, current_y_max = vb.viewRange()[1]

            if self.auto_scale_x and x_max > current_x_max:
                vb.setXRange(current_x_min, x_max, padding=0.05)
            if self.auto_scale_y:
                vb.setYRange(min(y_min, current_y_min),
                             max(y_max, current_y_max),
                             padding=0.2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = QtGraphWidget()
    win.resize(800, 500)
    win.set_axis_labels("Time", "Residual (log)")

    time = np.arange(0, 1001, 10)
    residual_ux = np.exp(-time / 300) * 1e-1 + np.random.rand(len(time)) * 1e-4
    residual_uy = np.exp(-time / 250) * 5e-2 + np.random.rand(len(time)) * 1e-4
    residual_p = np.exp(-time / 200) * 1e-1 + np.random.rand(len(time)) * 1e-4

    win.add_graph(0, "Ux", (time, residual_ux), pen=pg.mkPen('r', width=2))
    win.add_graph(1, "Uy", (time, residual_uy), pen=pg.mkPen('g', width=2))
    win.add_graph(2, "p", (time, residual_p), pen=pg.mkPen('b', width=2))

    win.show()
    sys.exit(app.exec())