import os
import psutil
import subprocess
import time
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, Signal, QThread, QTimer
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTextCursor, QFontDatabase

from nextlib.utils.type import is_integer
from nextlib.utils.time import seconds_to_time
from nextlib.execute.view.message_ui import Ui_Form
from nextlib.execute.process_utils import get_cpu_num, get_idle_cpu, assign_cpu
from nextlib.utils.file import get_current_dir
from nextlib.utils.ui import load_ui
from nextlib.utils.function import create_func_args
from nextlib.widgets.messagebox import messagebox_error

QProcess_ProcessState_WAITING = 3
QProcess_ProcessState_START = 4

PROCESS_STATE = {
    QProcess.ProcessState.NotRunning: 'Ready',
    QProcess.ProcessState.Starting: 'Starting',
    QProcess.ProcessState.Running: 'Running',
    QProcess_ProcessState_WAITING: 'Waiting for processor',
    QProcess_ProcessState_START: 'Start',
}

FONT_SIZE = 9
WEIGHT_BOLD = 600
WEIGHT_NORMAL = 300




class FindUsableCPU(QThread):
    waiting = Signal()
    founded = Signal(int)
    stopped = Signal()

    def __init__(self, available_cpus=None, ratio=5.0):
        super().__init__()

        self.available_cpus = available_cpus or []
        self.ratio = ratio
        self.stop_message = False

    def run(self):
        self.waiting.emit()
        _get_cpu = -1
        _max_tries = 25
        _tries = 0
        while _get_cpu == -1:
            _get_cpu = get_idle_cpu(self.available_cpus, self.ratio)
            if _get_cpu != -1:
                break
            _tries += 1
            if _tries >= _max_tries:
                import random
                _pool = list(self.available_cpus) if self.available_cpus else list(range(get_cpu_num()))
                _get_cpu = random.choice(_pool) if _pool else 0
                break
            QThread.msleep(200)
            if self.stop_message:
                break

        if self.stop_message:
            self.stopped.emit()
        else:
            self.founded.emit(_get_cpu)
        self.quit()

    def stop_finding(self):
        self.stop_message = True


class ExecWidget(QWidget):
    sig_proc_status = Signal(int, int, int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent

        self._ui = load_ui(self, Ui_Form)
        self._log_view = self._ui.textEdit_log
        self._output_view = self._ui.textEdit_output

        self._commands = []
        self._total_cmd_num = 0
        self._cur_count = 1
        self._task_name = ''

        self._added_env = []

        self._ignore_error = False

        self._show_command = True


        self._procs = []
        self._procs_cmd = []
        self._procs_state = []
        self._thread_find_cpus = []
        self._pending_cpu_assign = {}

        self._stop_all_proc = False
        self._pause_all_proc = False

        self._total_proc_num = 1
        self._using_proc_num = 0

        self._available_cpus = [i for i in range(get_cpu_num())]

        self._is_assigned_cpu = False
        self._assigned_cpus = []
        self._idle_ratio = 5.0

        self._funcs_changed_state = []
        self._funcs_get_message_output = []
        self._funcs_get_message_error = []
        self._funcs_get_finished = []

        self._funcs_after_finished = []
        self._funcs_after_error = []
        self._funcs_restore_ui = []

        self._log_msg = ''

        self._working_path = './'

        self._start_time = []
        self._elapsed_time = []

        self._menu_action = None
        self._progressbar = self._ui.progressBar
        self._statusbar = None
        self._dock = None

        self._dock_show = False

        self._is_tracking = True
        self._scrollbar_last_position = -1

        self._output_buffer = {}
        self._flush_timer = None
        self._flush_interval = 100

        self._log_file_handles = []

        self._initialize()

    def get_current_view(self):
        return self._ui.comboBox_output_proc_index.currentIndex()

    def set_current_view(self, index=0):
        if index < len(self._all_msgs):
            self._ui.comboBox_output_proc_index.setCurrentIndex(index)

    def get_procs(self):
        return self._procs

    def get_messages(self, index):
        log_path = self._get_log_path(index)
        if log_path and log_path.exists():
            try:
                return log_path.read_text(encoding='utf-8', errors='replace')
            except Exception:
                pass
        return ''

    def _get_log_path(self, proc_idx: int):
        return Path(self._working_path) / f'stdout_{proc_idx}.log'

    def _close_log_file_for(self, proc_idx):
        if proc_idx < len(self._log_file_handles):
            fh = self._log_file_handles[proc_idx]
            if fh:
                try:
                    fh.flush()
                except Exception:
                    pass

    def _close_log_files(self):
        for fh in self._log_file_handles:
            if fh:
                try:
                    fh.flush()
                    fh.close()
                except Exception:
                    pass

    def _initialize(self):
        self._init_edit()
        self.add_log_ready()
        self.set_tracking(False)

        self._ui.pushButton_clear.clicked.connect(self._clicked_button_clear)
        self._ui.checkBox_tracking.hide()
        self._ui.checkBox_tracking.stateChanged.connect(self._changed_state_combo_tracking)
        self._ui.progressBar.setValue(0)
        self._ui.comboBox_output_proc_index.currentIndexChanged.connect(self._changed_combo_output_cpu)

        self._flush_timer = QTimer(self)
        self._flush_timer.timeout.connect(self._flush_output_buffer)
        self._flush_timer.start(self._flush_interval)

    def _changed_state_combo_tracking(self, state):
        if state == 0:
            self.set_tracking(False)
        else:
            self.set_tracking(True)

    def _clicked_button_clear(self):
        cur_view = self._ui.stackedWidget.currentIndex()
        if cur_view == 0:
            self._log_view.clear()
            self._log_msg = ''

            self.add_log_notice('Log cleared')
            self.add_log_ready()

        elif cur_view == 1:
            cur_proc = self.get_current_view() - 1
            self._output_view.clear()
            if cur_proc < len(self._log_file_handles):
                fh = self._log_file_handles[cur_proc]
                if fh:
                    try:
                        fh.seek(0)
                        fh.truncate()
                    except Exception:
                        pass
            self.add_message_output('######### cleared log #########\n',
                                    cur_proc, record=False)

    def _changed_combo_output_cpu(self, index):
        if index < 0:
            return

        if index == 0:
            self._ui.stackedWidget.setCurrentIndex(0)
            self._ui.checkBox_tracking.hide()
            self.set_scroll_bottom(index)
        else:
            self._ui.stackedWidget.setCurrentIndex(1)
            self._ui.checkBox_tracking.show()
            proc_idx = index - 1
            self._close_log_file_for(proc_idx)
            self._output_buffer.pop(proc_idx, None)
            text = self.get_messages(proc_idx)
            self.set_text(text, index)
            self.set_scroll_bottom(1)

    def _init_edit(self):
        self._log_view = self._ui.textEdit_log
        self._log_view.clear()

        self._output_view = self._ui.textEdit_output
        self._output_view.clear()

        general_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont)
        general_font.setPointSize(FONT_SIZE)
        self._log_view.setFont(general_font)
        self._log_view.document().setMaximumBlockCount(2000)

        mono_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        mono_font.setPointSize(FONT_SIZE)
        self._output_view.setFont(mono_font)
        self._output_view.setMaximumBlockCount(100000)

    def put_in_layout(self, layout):
        layout.addWidget(self)

    def add_with_dock(self, parent=None, title=''):
        if parent is not None:
            self._dock = Dock(parent, title)
        else:
            self._dock = Dock(self._parent, title)

        self._dock.setWidget(self)

    def show_dock_widget(self, show_state=True):
        if self._dock is None:
            return
        self._dock.show_dock(show_state)

    def hide_dock_widget(self):
        if self._dock is None:
            return
        self._dock.hide_dock()


    def connect_to_menu_action(self, action):
        if self._dock is not None:
            self._dock.connect_to_action(action)

    def connect_to_statusbar(self, statusbar):
        self._statusbar = statusbar
        self._statusbar.showMessage('Ready', 0)

    def connect_to_progressbar(self, progressbar):
        self._progressbar = progressbar
        self._progressbar.setValue(0)

    def set_defaults(self, reset=False):
        self._commands = []
        self._total_cmd_num = 0
        self._cur_count = 1
        self._task_name = ''

        if not reset:
            self._ignore_error = False

        self._procs = []
        self._procs_cmd = []
        self._procs_state = []
        self._thread_find_cpus = []
        self._pending_cpu_assign = {}

        self._stop_all_proc = False
        self._pause_all_proc = False

        if not reset:
            self._total_proc_num = 1
        self._using_proc_num = 0

        self._available_cpus = [i for i in range(get_cpu_num())]

        if not reset:
            self._is_assigned_cpu = False
            self._assigned_cpus = []

        self._funcs_changed_state = []
        self._funcs_get_message_output = []
        self._funcs_get_message_error = []
        self._funcs_get_finished = []

        if not reset:
            self._funcs_after_finished = []
            self._funcs_after_error = []
            self._funcs_restore_ui = []

        if not reset:
            self._log_msg = ''

        self._close_log_files()
        self._log_file_handles = []

        self._start_time = []
        self._elapsed_time = []

    def end(self):
        if self._flush_timer:
            self._flush_timer.stop()
        self._close_log_files()
        self.stop_process()

    def reset(self):
        if self.is_running():
            return

        self.set_defaults(True)

    def set_edit_font(self, font=''):
        self._log_view.setStyleSheet(font)
        self._output_view.setStyleSheet(font)

    def set_working_path(self, path):
        if not Path(path).is_dir():
            return
        self._working_path = get_current_dir(path)
        self.add_log_working_path(self._working_path)

    def set_environment(self, key='PATH', value=''):
        env = QProcessEnvironment.systemEnvironment()
        env.insert(key, value)
        self._added_env = env

    def get_environment(self, key):
        value = QProcessEnvironment.systemEnvironment().value(key)
        return value

    def get_total_proc_num(self):
        return self._total_proc_num

    def get_using_proc_num(self):
        return self._using_proc_num

    def set_total_proc(self, num=1):
        max_cpu = get_cpu_num()
        if num < 1:
            num = 1
        if num > max_cpu:
            num = max_cpu
        self._total_proc_num = num

    def set_preferred_cpu(self, cpus_number=None):
        self._assigned_cpus = []
        total_num = get_cpu_num(True)

        cpus_number = [] if cpus_number is None else cpus_number
        if cpus_number:
            _check_cpus_number = []
            for d in cpus_number:
                if is_integer(d) and d < total_num:
                    if not d in _check_cpus_number:
                        _check_cpus_number.append(d)

            if _check_cpus_number:
                self._is_assigned_cpu = True
                self._assigned_cpus = _check_cpus_number
            else:
                self._is_assigned_cpu = False
        else:
            self._is_assigned_cpu = False

    def set_idle_ratio(self, ratio=5.0):
        self._idle_ratio = ratio

    def set_tracking(self, tracking=True):
        self._is_tracking = tracking

    def set_scroll_bottom(self, index=0):
        if index == 0:
            view = self._log_view
        else:
            view = self._output_view

        scrollbar = view.verticalScrollBar()
        scrollbar.setSliderPosition(scrollbar.maximum())

    def clear_view(self, index=-1):
        if index == 0 or index == -1:
            self._log_view.clear()
        if index == 1 or index == -1:
            self._output_view.clear()

    def add_log_ready(self):
        msg = f'<span style="font-weight: {WEIGHT_BOLD};">&gt;&gt; Ready</span>\n'
        self._log_view.append(msg)

    def add_log_working_path(self, text):
        msg = f'\n<span style="font-weight: {WEIGHT_BOLD};"><br>&gt;&gt; Path: {text}</span>\n'
        self._log_view.append(msg)

    def add_log_command(self, count, text=''):
        title = f'[{count}/{self._total_cmd_num}]'
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: green;"><br>&gt;&gt; {title} {text}</span>\n'
        self._log_view.append(msg)

    def add_log_notice(self, text=''):
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: darkorange;">&gt;&gt; {text}</span>\n'
        self._log_view.append(msg)

    def add_log_warning(self, text=''):
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: yellow;">&gt;&gt; {text}</span>\n'
        self._log_view.append(msg)

    def add_log_error(self, count, text=''):
        if count == 0:
            title = ''
        else:
            title = f'[{count}/{self._total_cmd_num}] '
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: #ee0000;">&gt;&gt; {title}{text}</span>\n'
        self._log_view.append(msg)
        self.set_scroll_bottom(0)

    def add_log_end(self, count=''):
        title = f'[{count}/{self._total_cmd_num}]'
        msg = f'\n<span style="font-weight: {WEIGHT_BOLD}; color: #0000fa;">&lt;&lt; {title} Done</span>\n'
        self._log_view.append(msg)

    def add_log_completed(self):
        msg = f'\n<span style="font-weight: {WEIGHT_BOLD}; color: #0000fa;">&lt;&lt; All done</span>\n'
        self._log_view.append(msg)

    def add_log_stopped(self, count):
        title = f'[{count}/{self._total_cmd_num}]'
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: #ee0000;">&lt;&lt; {title} Stopped</span>\n'
        self._log_view.append(msg)
        self.set_scroll_bottom(0)

    def add_message_output(self, text='', proc_idx=0, record=True):
        if record and proc_idx < len(self._log_file_handles):
            fh = self._log_file_handles[proc_idx]
            if fh:
                try:
                    fh.write(text)
                except Exception:
                    pass
        if proc_idx not in self._output_buffer:
            self._output_buffer[proc_idx] = []
        self._output_buffer[proc_idx].append(text)

    def add_message_error(self, text='', proc_idx=0, record=True):
        if record and proc_idx < len(self._log_file_handles):
            fh = self._log_file_handles[proc_idx]
            if fh:
                try:
                    fh.write(text)
                except Exception:
                    pass
        if proc_idx not in self._output_buffer:
            self._output_buffer[proc_idx] = []
        self._output_buffer[proc_idx].append(text)

    def _flush_output_buffer(self):
        try:
            if not self._output_view or not self._output_view.isVisible():
                return

            current_view = self.get_current_view() - 1
            if current_view < 0:
                return

            self._flush_output_buffer_for(current_view)
        except Exception:
            pass

    def _flush_output_buffer_for(self, proc_idx):
        try:
            if not self._output_view:
                return

            chunks = self._output_buffer.get(proc_idx, [])
            if not chunks:
                return

            current_view = self.get_current_view() - 1
            if current_view != proc_idx:
                return

            text = ''.join(chunks)
            self._output_buffer[proc_idx] = []

            if not text:
                return

            self._output_view.moveCursor(QTextCursor.MoveOperation.End)
            self._output_view.insertPlainText(text)

            if self._is_tracking:
                scrollbar = self._output_view.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    def set_text(self, text='', index=0):
        if index == 0:
            view = self._log_view
        else:
            view = self._output_view
        view.setPlainText(text)

    def set_show_command(self, show=True):
        self._show_command = show

    def set_task_name(self, name=''):
        self._task_name = name

    def get_commands(self):
        return self._commands

    def set_function_after_error(self, func=None, *argv):
        self._funcs_after_error.append([func, *argv])

    def set_function_after_finished(self, func=None, *argv):
        self._funcs_after_finished.append([func, *argv])

    def set_function_restore_ui(self, func=None, *argv):
        self._funcs_restore_ui.append([func, *argv])

    def run(self, commands):
        if self.is_running():
            messagebox_error(self._parent, text='Currently working on another task')
            return

        self.reset()

        if not commands:
            self.add_log_error(0, 'There are no commands')
            return False
        else:
            self._commands = []

            if not isinstance(commands, list):
                commands = [commands]
            for c in commands:
                if isinstance(c, tuple) and len(c) == 3:
                    self._commands.append(c)
                elif isinstance(c, tuple) and len(c) == 2:
                    self._commands.append((c[0], c[1], None))
                else:
                    self._commands.append((c, c, None))

        if not self._commands:
            self.add_log_error(0, 'There are no commands')
            return False

        self._total_cmd_num = len(self._commands)
        self._using_proc_num = min(self._total_cmd_num, self._total_proc_num)

        if self._is_assigned_cpu and len(self._assigned_cpus) < self._using_proc_num:
            self.add_log_error(0, 'Please input the appropriate CPU number')
            return False

        if self._progressbar is not None:
            self._progressbar.setFormat('%p %')
            self._progressbar.setRange(0, 100)
            self._progressbar.setValue(0)

        self._ui.comboBox_output_proc_index.blockSignals(True)
        self._ui.comboBox_output_proc_index.clear()
        self._ui.comboBox_output_proc_index.addItem('Log')
        self._ui.comboBox_output_proc_index.addItems([str(f'Proc. {i}') for i in range(self._using_proc_num)])
        self._ui.comboBox_output_proc_index.blockSignals(False)

        for i in range(self._using_proc_num):
            try:
                fh = open(self._get_log_path(i), 'w', encoding='utf-8', buffering=1)
                self._log_file_handles.append(fh)
            except Exception:
                self._log_file_handles.append(None)

        for proc_idx in range(self._using_proc_num):
            self._funcs_get_finished.append(create_func_args(self._get_finished, proc_idx))
            self._funcs_changed_state.append(create_func_args(self._changed_state, proc_idx))
            self._funcs_get_message_output.append(create_func_args(self._get_message_output, proc_idx))
            self._funcs_get_message_error.append(create_func_args(self._get_message_error, proc_idx))

            self._procs_state.append(QProcess.ProcessState.NotRunning)
            self._start_time.append(0)
            self._elapsed_time.append(0)

        for proc_idx in range(self._using_proc_num):
            new_proc = QProcess()
            new_proc.finished.connect(self._funcs_get_finished[proc_idx])
            new_proc.stateChanged.connect(self._funcs_changed_state[proc_idx])
            new_proc.readyReadStandardOutput.connect(self._funcs_get_message_output[proc_idx])
            new_proc.readyReadStandardError.connect(self._funcs_get_message_error[proc_idx])
            new_proc.setWorkingDirectory(self._working_path)

            if self._added_env:
                new_proc.setProcessEnvironment(self._added_env)

            self._procs.append(new_proc)

            _cmd, _label, _wdir = self._commands.pop(0)
            if _wdir:
                new_proc.setWorkingDirectory(_wdir)
            self._procs_cmd.append([self._cur_count, _cmd, _label])
            self._cur_count += 1

            self._thread_find_cpus.append(None)
            self._get_usable_procs(proc_idx)
        return True

    def _get_usable_procs(self, proc_idx):
        if proc_idx >= len(self._thread_find_cpus):
            return

        if self._cur_count == 2:
            self._progressbar.setValue(1)

        if self._thread_find_cpus[proc_idx] is not None:
            self._thread_find_cpus[proc_idx].stop_finding()
            self._thread_find_cpus[proc_idx].wait(1000)
            self._thread_find_cpus[proc_idx] = None

        if self._is_assigned_cpu:
            self._thread_find_cpus[proc_idx] = FindUsableCPU(self._assigned_cpus, self._idle_ratio)
        else:
            self._thread_find_cpus[proc_idx] = FindUsableCPU(self._available_cpus, self._idle_ratio)

        self._thread_find_cpus[proc_idx].waiting.connect(partial(self._waiting_proc, proc_idx))
        self._thread_find_cpus[proc_idx].founded.connect(partial(self._start_proc, proc_idx))
        self._thread_find_cpus[proc_idx].stopped.connect(partial(self._stopped_proc, proc_idx))
        self._thread_find_cpus[proc_idx].start()

    def _waiting_proc(self, proc_idx):
        self._procs_state[proc_idx] = QProcess_ProcessState_WAITING
        self.show_process_state(proc_idx)
        self.sig_proc_status.emit(proc_idx, -1, -1, 'Waiting')

        _cmd = self._procs_cmd[proc_idx][1]
        _label = self._procs_cmd[proc_idx][2] if len(self._procs_cmd[proc_idx]) > 2 else _cmd
        if self._show_command:
            self.add_log_command(self._procs_cmd[proc_idx][0], _label)
        else:
            if self._task_name:
                self.add_log_command(self._procs_cmd[proc_idx][0], self._task_name)
            else:
                self.add_log_command('Start...')

    def _start_proc(self, proc_idx, get_cpu):
        self._procs_state[proc_idx] = QProcess_ProcessState_START
        self.show_process_state(proc_idx)

        _cmd = self._procs_cmd[proc_idx][1]

        if self._stop_all_proc:
            self._stopped_proc(proc_idx, f'Cannot execute: {_cmd}')
            return False

        if self._pause_all_proc:
            self._stopped_proc(proc_idx)
            return False

        self._start_time[proc_idx] = time.time()

        self._pending_cpu_assign[proc_idx] = get_cpu

        split_cmd = self._procs[proc_idx].splitCommand(_cmd)
        if len(split_cmd) == 1:
            self._procs[proc_idx].start(split_cmd[0])
        elif len(split_cmd) > 1:
            self._procs[proc_idx].start(split_cmd[0], split_cmd[1:])
        else:
            self._stopped_proc(proc_idx, f'There is no command: {_cmd}')
            return False

        self.sig_proc_status.emit(proc_idx, get_cpu, -1, 'Starting')
        return True

    def _stopped_proc(self, proc_idx, msg='Stopped'):
        proc = self._procs[proc_idx]
        if proc is not None:
            try:
                proc.readyReadStandardOutput.disconnect()
                proc.readyReadStandardError.disconnect()
                proc.stateChanged.disconnect()
                proc.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                proc.deleteLater()
            except RuntimeError:
                pass
        self._procs[proc_idx] = None

        self._procs_state[proc_idx] = QProcess.ProcessState.NotRunning
        self.show_process_state(proc_idx)

        self.add_log_error(self._procs_cmd[proc_idx][0], msg)

        if self._progressbar is not None:
            self._progressbar.setFormat('Stopped')

        if self._funcs_restore_ui:
            self._run_restore_ui()

    def _get_message_output(self, proc_idx):
        try:
            proc = self._procs[proc_idx]
            if proc is None:
                return
            _message = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='replace')
            if _message:
                self.add_message_output(_message, proc_idx)
        except (RuntimeError, IndexError, AttributeError):
            pass

    def _get_message_error(self, proc_idx):
        try:
            proc = self._procs[proc_idx]
            if proc is None:
                return
            _message = bytes(proc.readAllStandardError()).decode('utf-8', errors='replace')
            if _message:
                self.add_message_error(_message, proc_idx)
        except (RuntimeError, IndexError, AttributeError):
            pass

    def _get_finished(self, proc_idx, exit_code, *args):
        is_next = False
        is_stopped = False

        proc = self._procs[proc_idx]
        if proc is not None:
            try:
                remaining = bytes(proc.readAllStandardOutput()).decode('utf-8', errors='replace')
                if remaining:
                    self.add_message_output(remaining, proc_idx)
            except (RuntimeError, AttributeError):
                pass
            self._output_buffer.pop(proc_idx, None)

            current_view = self.get_current_view() - 1
            if current_view == proc_idx:
                self._close_log_file_for(proc_idx)
                text = self.get_messages(proc_idx)
                self.set_text(text, 1)

            try:
                proc.readyReadStandardOutput.disconnect()
                proc.readyReadStandardError.disconnect()
                proc.stateChanged.disconnect()
                proc.finished.disconnect()
            except (RuntimeError, TypeError):
                pass
            try:
                proc.deleteLater()
            except RuntimeError:
                pass
        self._procs[proc_idx] = None

        self._procs_state[proc_idx] = QProcess.ProcessState.NotRunning

        exit_status = args[0] if args else QProcess.ExitStatus.NormalExit
        was_killed = (exit_status == QProcess.ExitStatus.CrashExit) or self._stop_all_proc

        if exit_code == 0 and not was_killed:
            self.add_log_end(self._procs_cmd[proc_idx][0])
            if self._commands:
                self._elapsed_time[proc_idx] = time.time() - self._start_time[proc_idx]
                self._run_next(proc_idx)
                is_next = True
        else:
            if exit_code == 2:
                self.add_log_error(self._procs_cmd[proc_idx][0], f'No such file or directory (Check the log for details)')
                is_stopped = True
            else:
                self.add_log_stopped(self._procs_cmd[proc_idx][0])
                is_stopped = True

            if self._ignore_error and self._commands:
                self._run_next(proc_idx)
                is_next = True
            else:
                if self._funcs_after_error:
                    self._run_error()

        if self._progressbar is not None:
            if is_stopped:
                self._progressbar.setFormat('Stopped!!')
            else:
                cur_value = (int)(((self._cur_count - 2) / self._total_cmd_num) * 100)
                self._progressbar.setValue(cur_value)

        for state in self._procs_state:
            if state != QProcess.ProcessState.NotRunning:
                return

        if not is_next and exit_code == 0:
            if self._funcs_after_finished:
                self._run_finished()

            if self._total_cmd_num > 1:
                self.add_log_completed()

            if self._progressbar is not None:
                self._progressbar.setValue(100)

        if not is_next:
            if self._funcs_restore_ui:
                self._run_restore_ui()

        if not is_next and self._thread_find_cpus[proc_idx] is not None:
            t = self._thread_find_cpus[proc_idx]
            self._thread_find_cpus[proc_idx] = None
            t.wait(500)

    def _run_next(self, proc_idx):
        new_proc = QProcess()
        self._procs[proc_idx] = new_proc

        new_proc.stateChanged.connect(self._funcs_changed_state[proc_idx])
        new_proc.readyReadStandardOutput.connect(self._funcs_get_message_output[proc_idx])
        new_proc.readyReadStandardError.connect(self._funcs_get_message_error[proc_idx])
        new_proc.finished.connect(self._funcs_get_finished[proc_idx])
        new_proc.setWorkingDirectory(self._working_path)

        if self._added_env:
            new_proc.setProcessEnvironment(self._added_env)

        _cmd, _label, _wdir = self._commands.pop(0)
        if _wdir:
            new_proc.setWorkingDirectory(_wdir)
        self._procs_cmd[proc_idx] = [self._cur_count, _cmd, _label]
        self._cur_count += 1

        self._get_usable_procs(proc_idx)

    def _changed_state(self, proc_idx, state):
        self._procs_state[proc_idx] = state

        if state == QProcess.ProcessState.Running:
            cpu_id = self._pending_cpu_assign.pop(proc_idx, None)
            if cpu_id is not None:
                try:
                    proc = self._procs[proc_idx]
                    if proc is not None:
                        pid = proc.processId()
                        assign_cpu(pid, cpu_id)
                        self.sig_proc_status.emit(proc_idx, cpu_id, pid, 'Running')
                except Exception:
                    pass

        self.show_process_state(proc_idx)

    def show_process_state(self, proc_idx):
        if self._statusbar is None:
            return

        message = PROCESS_STATE[self._procs_state[proc_idx]]
        if message == 'Ready':
            for d in self._procs_state:
                if PROCESS_STATE[d] != 'Ready':
                    return
            self._statusbar.showMessage(message)
        else:
            _max_time = 0
            for d in self._elapsed_time:
                if d > 0:
                    _max_time = max(_max_time, d)

            if _max_time == 0:
                _str_ete = 'calculating...'

            else:
                remain_cmds = len(self._commands) + 1
                if remain_cmds < self._using_proc_num:
                    remain_cmds = self._using_proc_num
                total_time = (_max_time * remain_cmds)
                remain_time = total_time / (self._using_proc_num * 0.85)

                hour, min, sec = seconds_to_time(remain_time)
                _str_ete = ''
                if hour > 0:
                    _str_ete += f' {hour}h'
                if min > 0:
                    _str_ete += ' %02dm' % min
                if sec > 0:
                    _str_ete += ' %02ds' % sec

            message = (message + ' (Remaining: %d tasks / %s)' %
                       (len(self._commands), _str_ete))

            self._statusbar.showMessage(message)

    def _run_error(self):
        _function, *_argv = self._funcs_after_error.pop(0)
        if _function is not None:
            _function(*_argv)

    def _run_finished(self):
        _function, *_argv = self._funcs_after_finished.pop(0)
        if _function is not None:
            _function(*_argv)

    def _run_restore_ui(self):
        _function, *_argv = self._funcs_restore_ui.pop(0)
        if _function is not None:
            _function(*_argv)

    def is_running(self):
        for d in self._procs_state:
            if d != QProcess.ProcessState.NotRunning:
                return True
        return False

    def stop_process(self, kill=False):
        if not self.is_running():
            for i, d in enumerate(self._procs):
                if self._thread_find_cpus[i] is not None:
                    self._thread_find_cpus[i].stop_finding()
                    self._thread_find_cpus[i].wait(500)
                    self._thread_find_cpus[i] = None
            return

        self._commands = []

        for i, proc in enumerate(self._procs):
            if not proc:
                continue

            try:
                proc_id = proc.processId()
            except Exception:
                continue

            if proc.state() == QProcess.ProcessState.Running:
                if kill:
                    self._kill_process_tree(proc_id)
                else:
                    try:
                        psutil.Process(proc_id).terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

            elif self._procs_state[i] == QProcess_ProcessState_WAITING:
                if self._thread_find_cpus[i] is not None:
                    self._thread_find_cpus[i].stop_finding()
                    self._thread_find_cpus[i].wait(500)
                    self._thread_find_cpus[i] = None

            else:
                ...

        self._stop_all_proc = True
        self._pause_all_proc = False

    def _kill_process_tree(self, pid: int):
        try:
            parent = psutil.Process(pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass
            parent.kill()
            psutil.wait_procs([parent], timeout=0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def _suspend_tree(self, pid: int):
        """부모 및 모든 자식 프로세스에 SIGSTOP 전송."""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.suspend()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.suspend()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def _resume_tree(self, pid: int):
        """부모 및 모든 자식 프로세스에 SIGCONT 전송."""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.resume()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.resume()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def pause_process(self):
        if not self.is_running():
            for i, d in enumerate(self._thread_find_cpus):
                if d is not None:
                    d.stop_finding()
            return

        for i, proc in enumerate(self._procs):
            if self._procs_state[i] in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
                proc_id = proc.processId()
                self._suspend_tree(proc_id)
            elif self._procs_state[i] == QProcess_ProcessState_WAITING:
                self._thread_find_cpus[i].stop_finding()

        self._pause_all_proc = True
        self.add_log_notice('Paused')

    def resume_process(self):
        if not self.is_running():
            return

        for i, proc in enumerate(self._procs):
            state = self._procs_state[i]
            if state in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
                proc_id = proc.processId()
                self._resume_tree(proc_id)
            elif state in (QProcess_ProcessState_WAITING, QProcess_ProcessState_START):
                self._get_usable_procs(i)

        self._pause_all_proc = False
        self.add_log_notice('Continue')
