#!/usr/bin/env python3
# -*- coding:utf8 -*-
# !/bin/bash

import time

from PySide6.QtCore import Qt, QObject, Signal, QRunnable, QThreadPool
from PySide6.QtWidgets import QDialog, QVBoxLayout, QTextEdit

from NextLib.Widgets.Function import create_func_args
from NextLib.Ui import load_ui
from NextLib.Execute.View.waiting_ui import Ui_Dialog


class TaskSignals(QObject):
    started = Signal()
    updating = Signal()
    current = Signal(int)
    finished = Signal()
    stopped = Signal(str)


class Task(QRunnable):
    def __init__(self):
        super().__init__()
        self.signals = TaskSignals()

        self.run = None

        self._running_state = False
        self._run_functions = []
        self._total_task_num = 0
        self._completed_task_num = 0

        self.autoDelete()

    def get_total_task_num(self):
        return self._total_task_num

    def get_completed_task_num(self):
        return self._completed_task_num

    def _run(self):
        self._total_task_num = len(self._run_functions)
        self.signals.started.emit()

        try:
            num = len(self._run_functions)
            for i in range(num):
                self._completed_task_num = i
                self.signals.current.emit(i)  # Refer: this signal is maybe too late
                self._run_functions[i]()    # self._run_functions.pop(0)()
                self.signals.updating.emit()

        except Exception as e:
            self.signals.stopped.emit(str(e))
        finally:
            self.signals.finished.emit()

    def set_task(self, function):
        self._run_functions = function
        self.run = self._run

    def is_running(self):
        return self._running_state


class Runner(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._task = None
        self._task_functions = []
        self._threadpool = None

        self._ui = load_ui(self, Ui_Dialog)
        self._show_message = False
        self._show_message_infinite_loading = False

        self.hide()

    def event_dlg_close(self, e):
        e.ignore()

    def event_dlg_org_close(self, e):
        e.accept()

    def end(self):
        if self._threadpool is not None:
            self._threadpool.clear()
            self._threadpool.deleteLater()

    def set_defaults(self, parent=None):
        if parent is not None:
            self._parent = parent
        self.setParent(self._parent)

    def set_show_message(self, show=True):
        self._show_message = show

    def set_message_title(self, title='Notice'):
        self.setWindowTitle(title)

    def add_task(self, function, *args):
        # Warning: Do not append thread function
        self._task_functions.append(create_func_args(function, *args))

    def start(self):
        self._task = Task()
        self._task.set_task(self._task_functions)

        self._task.signals.started.connect(self._started)
        self._task.signals.updating.connect(self.updating)
        self._task.signals.current.connect(self._current)
        self._task.signals.finished.connect(self._finished)
        self._task.signals.stopped.connect(self._stopped)

        if self._threadpool is not None:
            self._threadpool.clear()
        self._threadpool = QThreadPool()
        self._threadpool.start(self._task)

    def _started(self):
        self._running_state = True

        if self._show_message:
            self._ui.label.setText('Starting...')
            if self._show_message_infinite_loading:
                self._ui.progressBar.setRange(0, 0)
            else:
                self._ui.progressBar.setRange(0, self._task.get_total_task_num())

            self.closeEvent = self.event_dlg_close
            self.show()

    def updating(self):
        self._update()

    def _update(self):
        if self._show_message:
            self._ui.label.setText('updating...')
            self._ui.progressBar.setValue(self._task.get_completed_task_num())
            self.show()

    def _current(self, i):
        if self._show_message:
            self._ui.label.setText(f'current task...{i}')
            self._ui.progressBar.setValue(i)

    def _finished(self):
        self._running_state = False
        self._threadpool.clear()
        self._task_functions = []

        if self._show_message:
            self.closeEvent = self.event_dlg_org_close
            self._ui.label.setText(f'Completed')
            self._ui.progressBar.setValue(self._ui.progressBar.maximum())
            time.sleep(0.2)
            self.hide()

    def _stopped(self, e):
        if self._show_message:
            self._ui.label.setText(f'Stopped!!! {e}')
