# -*- coding: utf-8 -*-
import sys
import numpy as np
from collections import defaultdict, deque
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
import pyqtgraph as pg

# ---------------------------
# CustomViewBox: middle-button pan only, wheel zoom
# ---------------------------
class CustomViewBox(pg.ViewBox):
    """
    - 마우스 휠: 줌 (기본)
    - 중간(휠) 버튼 누른 상태로 드래그하면 pan (좌우/위아래)
      위아래 pan 허용 여부는 parent의 allow_vertical_pan 속성 참조
    """
    def __init__(self, parent_widget=None, allow_vertical_pan=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent_widget = parent_widget
        self.allow_vertical_pan = allow_vertical_pan
        self.setMouseMode(self.PanMode)  # ViewBox 내부 동작은 PanMode로 사용
        # 기본 드래그 동작을 막고 mouseDragEvent로 제어
        # self.setInteractive(True)

    def mouseDragEvent(self, ev, axis=None):
        # 중간 버튼(버튼 2)으로만 패닝 허용
        if ev.button() == Qt.MiddleButton or (ev.button() == Qt.MouseButton and ev.buttons() & Qt.MiddleButton):
            # 만약 vertical pan을 비허용하면 y축은 고정
            if not self.allow_vertical_pan:
                # translate only in x
                if ev.isStart():
                    self._startPos = ev.pos()
                if ev.isFinish():
                    ev.accept()
                    return
                # compute dx in pixel and translate only x
                dx = ev.pos().x() - getattr(self, "_startPos", ev.pos()).x()
                # map pixel dx to data coords
                vbRect = self.viewRect()
                if vbRect is None:
                    ev.ignore()
                    return
                scale_x = vbRect.width() / float(self.width())
                # shift in data coords
                dx_data = -dx * scale_x
                self.translateBy(x=dx_data, y=0)
                self._startPos = ev.pos()
                ev.accept()
            else:
                # full pan (x,y)
                super().mouseDragEvent(ev, axis=axis)
        else:
            # 다른 버튼(왼쪽 등)은 기본 동작(예: 선택 등)
            ev.ignore()

    # keep wheelEvent default (zoom)
    # no change for wheelEvent (inherited behavior)


# ---------------------------
# GraphManager: add/remove/manage groups
# ---------------------------
class GraphManager:
    def __init__(self, plot_widget: pg.PlotWidget, autoscale_callback=None):
        self.plot_widget = plot_widget
        self.graphs = {}            # id -> dict({'item': PlotDataItem, 'name': str, 'group': int})
        self.groups = defaultdict(list)
        self.autoscale_callback = autoscale_callback

    def add_graph(self, id: int, name: str, data, group: int = 0, pen=None):
        """data: (x, y) or y-list (x auto -> range(len(y)))"""
        if id in self.graphs:
            self.remove_graph(id)

        if isinstance(data, (list, tuple)) and len(data) == 2:
            x, y = data
        else:
            y = np.asarray(data)
            x = np.arange(len(y))

        # ensure numpy arrays
        x = np.asarray(x)
        y = np.asarray(y)

        if pen is None:
            pen = pg.mkPen(width=1.5)

        # plot returns PlotDataItem
        # autoDownsample 옵션으로 과도한 데이터 렌더링 부담을 줄임
        item = self.plot_widget.plot(x, y, pen=pen, name=name, autoDownsample=True, antialias=False)
        item.setZValue(1000 - id)  # id 작을수록 위에 보이게
        # store raw data buffer for append efficient updates
        # use deque to limit memory if desired (here unlimited)
        self.graphs[id] = {'item': item, 'name': name, 'group': group, 'x': deque(x.tolist()), 'y': deque(y.tolist())}
        self.groups[group].append(id)

        # call autoscale via callback but defer with singleShot to avoid recursion
        if callable(self.autoscale_callback):
            QtCore.QTimer.singleShot(0, self.autoscale_callback)

    def remove_graph(self, id: int):
        if id not in self.graphs:
            return
        g = self.graphs.pop(id)
        try:
            self.plot_widget.removeItem(g['item'])
        except Exception:
            pass
        grp = g['group']
        if id in self.groups.get(grp, []):
            self.groups[grp].remove(id)
            if not self.groups[grp]:
                del self.groups[grp]

        # autoscale update
        if callable(self.autoscale_callback):
            QtCore.QTimer.singleShot(0, self.autoscale_callback)

    def set_group_visible(self, group: int, visible: bool):
        for gid in self.groups.get(group, []):
            self.graphs[gid]['item'].setVisible(visible)

    def clear(self):
        for gid in list(self.graphs.keys()):
            self.remove_graph(gid)

    def append_to_graph(self, id: int, x_new, y_new, call_autoscale=True):
        """효율적으로 데이터 추가 (append). x_new,y_new scalars or arrays"""
        if id not in self.graphs:
            raise KeyError(f"Graph id {id} not found")
        g = self.graphs[id]
        x_arr = np.atleast_1d(x_new)
        y_arr = np.atleast_1d(y_new)
        if x_arr.shape != y_arr.shape:
            raise ValueError("x_new and y_new must have same shape")

        # append to buffers
        for xi, yi in zip(x_arr.tolist(), y_arr.tolist()):
            g['x'].append(xi)
            g['y'].append(yi)

        # convert to numpy for setData; use autoDownsample to help performance
        x_np = np.asarray(g['x'])
        y_np = np.asarray(g['y'])
        # setData with autoDownsample to avoid blocking
        g['item'].setData(x_np, y_np, autoDownsample=True, antialias=False)

        if call_autoscale and callable(self.autoscale_callback):
            QtCore.QTimer.singleShot(0, self.autoscale_callback)


# ---------------------------
# GraphWidget: 완성형 위젯
# ---------------------------
class GraphWidget(QtWidgets.QWidget):
    def __init__(self, parent=None, allow_vertical_pan=True, y_log=True):
        super().__init__(parent)

        # 기본 설정 (background/foreground)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        self.allow_vertical_pan = allow_vertical_pan
        self.y_log = y_log

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # CustomViewBox 사용한 PlotWidget 생성
        vb = CustomViewBox(parent_widget=self, allow_vertical_pan=self.allow_vertical_pan)
        self.plot_widget = pg.PlotWidget(viewBox=vb)
        # apply log mode if requested
        self.plot_widget.setLogMode(x=False, y=bool(self.y_log))

        # grid, legend
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.plot_widget.addLegend(offset=(10, 10))
        self.plot_widget.setMenuEnabled(False)
        self.plot_widget.setClipToView(True)

        # tick spacing: 안전하게 다루기 (로그일땐 left tickSpacing 사용하지 않음)
        # bottom 축은 선형이므로 적당한 spacing 설정 가능
        try:
            self.plot_widget.getAxis('bottom').setTickSpacing(major=1.0, minor=None)
        except Exception:
            pass

        layout.addWidget(self.plot_widget)

        # manager 생성 (autoscale callback으로 위젯의 auto-scale을 연결)
        self._autoscale_timer = QtCore.QTimer(self)
        self._autoscale_timer.setSingleShot(True)
        self._autoscale_timer.setInterval(80)  # 디바운스: 80ms 내 여러 호출은 합쳐짐
        self._autoscale_timer.timeout.connect(self._perform_auto_scale)

        self.manager = GraphManager(self.plot_widget, autoscale_callback=self._request_auto_scale)

        # auto scale 옵션
        self.auto_scale_x = True
        self.auto_scale_y = True
        self._init_range_done = False

        # 축 라벨
        self.set_axis_labels("Time", "Residual (log)" if self.y_log else "Value")

    # ---------------------------
    # 외부 API: 그래프 추가/삭제/append/update
    # ---------------------------
    def add_graph(self, id: int, name: str, data, group: int = 0, pen=None):
        # data 내부에서 y<=0 처리 (로그일 때 안정화)
        x, y = self._normalize_xy(data)
        self.manager.add_graph(id, name, (x, y), group=group, pen=pen)

    def remove_graph(self, id: int):
        self.manager.remove_graph(id)

    def set_group_visible(self, group: int, visible: bool):
        self.manager.set_group_visible(group, visible)

    def update_graph_append(self, id: int, x_new, y_new):
        # append할 때도 y<=0 처리
        _, y_arr = (None, None)
        # ensure numeric arrays and sanitize
        x_arr = np.atleast_1d(x_new)
        y_arr = np.atleast_1d(y_new).astype(float)
        if self.y_log:
            # replace non-positive with nan (pyqtgraph will skip drawing points at nan)
            y_arr = np.where(y_arr > 0, y_arr, np.nan)
        self.manager.append_to_graph(id, x_arr, y_arr)

    # ---------------------------
    # 축 라벨
    # ---------------------------
    def set_axis_labels(self, xlabel: str = "", ylabel: str = ""):
        self.plot_widget.setLabel('bottom', xlabel)
        self.plot_widget.setLabel('left', ylabel)

    # ---------------------------
    # 내부: xy 정규화 및 로그 안전 처리
    # ---------------------------
    def _normalize_xy(self, data):
        if isinstance(data, (list, tuple)) and len(data) == 2:
            x, y = data
        else:
            y = np.asarray(data)
            x = np.arange(len(y))
        x = np.asarray(x)
        y = np.asarray(y).astype(float)
        if self.y_log:
            # 로그일때 0이하를 NaN으로 바꿔 무한대/음수로 인한 문제 방지
            y = np.where(y > 0, y, np.nan)
        return x, y

    # ---------------------------
    # autoscale 디바운스 요청 (관리자/외부에서 호출)
    # ---------------------------
    def _request_auto_scale(self):
        # 여러번 호출되더라도 timer로 디바운스되어 _perform_auto_scale가 한 번만 실행됨
        self._autoscale_timer.start()

    def _perform_auto_scale(self):
        """안전한 auto scaling: 처음엔 전체 범위 잡고, 이후엔 오른쪽 확장 및 y범위 합산"""
        vb = self.plot_widget.getViewBox()
        if not self.manager.graphs:
            return

        all_x = []
        all_y = []
        for g in self.manager.graphs.values():
            # use stored buffers to avoid expensive getData
            x_buf = np.asarray(g['x']) if 'x' in g else np.array([])
            y_buf = np.asarray(g['y']) if 'y' in g else np.array([])
            if x_buf.size and y_buf.size:
                all_x.append(x_buf)
                all_y.append(y_buf)

        if not all_x or not all_y:
            return

        all_x = np.concatenate(all_x)
        all_y = np.concatenate(all_y)

        # filter nan and inf
        all_x = all_x[np.isfinite(all_x)]
        all_y = all_y[np.isfinite(all_y)]

        if all_x.size == 0 or all_y.size == 0:
            return

        x_min, x_max = float(np.min(all_x)), float(np.max(all_x))
        # y: 로그이면 음수/0 이미 NaN 처리되어있으므로 just min/max
        y_min, y_max = float(np.min(all_y)), float(np.max(all_y))

        # fallback if y_min==y_max (single-value)
        if y_min == y_max:
            # expand a bit
            y_min *= 0.9
            y_max *= 1.1
            if y_min == y_max:
                y_min -= 1.0
                y_max += 1.0

        # 첫 초기 설정은 전체 범위
        if not self._init_range_done:
            vb.setXRange(x_min, x_max, padding=0.02)
            vb.setYRange(y_min, y_max, padding=0.2)
            self._init_range_done = True
            return

        # 이후에는 오른쪽으로 확장(시계열), y는 필요시 확장
        cur_x_range, cur_y_range = vb.viewRange()
        cur_xmin, cur_xmax = cur_x_range
        cur_ymin, cur_ymax = cur_y_range

        # expand x to the right if new max exceeds current
        if self.auto_scale_x and x_max > cur_xmax:
            vb.setXRange(cur_xmin, x_max, padding=0.02)

        if self.auto_scale_y:
            # ensure we expand to include new min/max
            new_ymin = min(y_min, cur_ymin)
            new_ymax = max(y_max, cur_ymax)
            if new_ymin != cur_ymin or new_ymax != cur_ymax:
                vb.setYRange(new_ymin, new_ymax, padding=0.15)

    # ---------------------------
    # 편의: clear all
    # ---------------------------
    def clear(self):
        self.manager.clear()
        self._init_range_done = False


# ---------------------------
# 실행 테스트: 가짜 residual을 실시간으로 append 하는 예제
# ---------------------------
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)

    w = GraphWidget(allow_vertical_pan=False, y_log=True)
    w.resize(1000, 600)
    w.set_axis_labels("Time", "Residual (log)")
    w.show()

    # 초기 데이터 (sparse)
    t0 = np.arange(0, 101, 10)
    ux0 = np.exp(-t0 / 200.0) * 1e-1 + (np.random.rand(len(t0)) * 1e-5)
    uy0 = np.exp(-t0 / 180.0) * 5e-2 + (np.random.rand(len(t0)) * 1e-5)
    w.add_graph(0, "Ux", (t0, ux0), group=0, pen=pg.mkPen('r', width=2))
    w.add_graph(1, "Uy", (t0, uy0), group=0, pen=pg.mkPen('g', width=2))

    # 실시간으로 데이터 append (timer로 시뮬레이션)
    time_counter = 110.0

    def produce_new():
        self.time_counter = 0
        # 새로운 타임스텝 1개씩 추가
        self.time_counter += 1
        # residual 모사: 지수 감쇠 + 잡음
        new_ux = float(np.exp(-t / 200.0) * 1e-1 + (np.random.rand() * 1e-6))
        new_uy = float(np.exp(-t / 180.0) * 5e-2 + (np.random.rand() * 1e-6))
        # append (y<=0는 내부에서 NaN으로 바꿈)
        w.update_graph_append(0, t, new_ux)
        w.update_graph_append(1, t, new_uy)
        time_counter += 10.0

    timer = QtCore.QTimer()
    timer.setInterval(300)  # 300ms마다 새 데이터 추가 (실시간 시뮬레이션)
    timer.timeout.connect(produce_new)
    timer.start()

    sys.exit(app.exec())
