import os
import psutil
import subprocess
import time
from functools import partial
from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QProcessEnvironment, Signal, QThread   # QMutex
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QTextCursor

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

# 사용 방법
# - 공통적으로 CPU는 idle 상태인 아무거나로 실행하거나 또는 사용할 CPU를 지정하여 실행 가능
# - 명령어는 리스트로 한꺼번에 넣으면 됨
# - 싱글 코어로 실행 시

# >> self.cmd.run(['python run_hardwork.py', 'python run_hardwork.py'])

# 병렬로 실행 시(여러 코어로 실행)
# >> self.cmd.set_total_proc(2)
# >> self.cmd.run(['python run_hardwork.py', 'python run_hardwork.py'])

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
        while _get_cpu == -1:
            _get_cpu = get_idle_cpu(self.available_cpus, self.ratio)
            if _get_cpu != -1:
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

        # self._mutex = QMutex()

        self._procs = []
        self._procs_cmd = []
        self._procs_state = []       # default is QProcess.ProcessState.NotRunning
        self._thread_find_cpus = []

        self._stop_all_proc = False
        self._pause_all_proc = False

        self._total_proc_num = 1  # 1 runs in single, 1> runs in parallel
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
        self._all_msgs = []

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

        self._initialize()

    def get_current_view(self):
        return self._ui.comboBox_output_proc_index.currentIndex()

    def set_current_view(self, index=0):
        if index <= len(self._all_msgs):
            self._ui.comboBox_output_proc_index.setCurrentIndex(index)

    def get_procs(self):
        return self._procs

    def get_messages(self, index):
        if index >= len(self._all_msgs):
            return ''
        return self._all_msgs[index]

    def _initialize(self):
        self._init_edit()
        self.add_log_ready()
        self.set_tracking(True)

        self._ui.pushButton_clear.clicked.connect(self._clicked_button_clear)
        self._ui.checkBox_tracking.hide()
        self._ui.checkBox_tracking.stateChanged.connect(self._changed_state_combo_tracking)
        self._ui.progressBar.setValue(0)
        self._ui.comboBox_output_proc_index.currentIndexChanged.connect(self._changed_combo_output_cpu)

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
            self._all_msgs[cur_proc] = ''
            self._output_view.clear()
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
            text = self.get_messages(index-1)
            self.set_text(text, index)
            self._ui.stackedWidget.setCurrentIndex(1)
            self._ui.checkBox_tracking.show()
            self.set_scroll_bottom(1)

    def _init_edit(self):
        self._log_view = self._ui.textEdit_log
        self._log_view.clear()

        self._output_view = self._ui.textEdit_output
        self._output_view.clear()

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

    # def set_dock_widget_position(self, parent, position):
    #     self.addDockWidget(Qt.LeftDockWidgetArea, dock)

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
        self._all_msgs = []

        self._start_time = []
        self._elapsed_time = []

    def end(self):
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
        scrollbar = self._output_view.verticalScrollBar()
        if tracking:
            self._output_view.verticalScrollBar().setTracking(tracking)
            scrollbar.rangeChanged.connect(self._changed_range_scrollbar)
            scrollbar.setSliderPosition(scrollbar.maximum())
            self._is_tracking = True
        else:
            if self._is_tracking:
                scrollbar.rangeChanged.disconnect()
            self._is_tracking = False

    def _changed_range_scrollbar(self, _min, _max):
        scrollbar = self._output_view.verticalScrollBar()

        if self._scrollbar_last_position == -1:
            scrollbar.setSliderPosition(_max)
        elif self._scrollbar_last_position <= scrollbar.value():
            scrollbar.setSliderPosition(_max)

        self._scrollbar_last_position = _max

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
        elif index == 0 or index == -1:
            self._output_view.clear()

    def add_log_ready(self):
        msg = f'<span style="font-weight: {WEIGHT_BOLD}; color: #000000;">&gt;&gt; Ready</span>\n'
        self._log_view.append(msg)

    def add_log_working_path(self, text):
        msg = f'\n<span style="font-weight: {WEIGHT_BOLD}; color: #000000;"><br>&gt;&gt; Path: {text}</span>\n'
        self._log_view.append(msg)

    def add_log_command(self, count, text=''):
        title = f'[{count}/{self._total_cmd_num}]'
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: green;"><br>&gt;&gt; {title} {text}</span>\n'
        self._log_view.append(msg)

    def add_log_notice(self, text=''):
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: darkorange;">&gt;&gt; {text}</span>\n'
        self._log_view.append(msg)

    def add_log_warning(self, text=''):
        msg = f'\n\n<span style="font-weight: {WEIGHT_BOLD}; color: lightgray;">&gt;&gt; {text}</span>\n'
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
        if record:
            self._all_msgs[proc_idx] += f'{text}'
        if proc_idx == (self.get_current_view()-1):
            cursor = self._output_view.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)

    def add_message_error(self, text='', proc_idx=0, record=True):
        if record:
            self._all_msgs[proc_idx] += f'{text}'
        if proc_idx == (self.get_current_view()-1):
            cursor = self._output_view.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text)

    def set_text(self, text='', index=0):
        if index == 0:
            view = self._log_view
        else:
            view = self._output_view
        view.setText(text)

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
                self._commands.append(c)

        if not self._commands:
            self.add_log_error(0, 'There are no commands')
            return False

        self._total_cmd_num = len(self._commands)
        self._using_proc_num = min(self._total_cmd_num, self._total_proc_num)

        if self._is_assigned_cpu and len(self._assigned_cpus) < self._using_proc_num:
            self.add_log_error(0, 'Please input the appropriate CPU number')
            return False

        if self._progressbar is not None:
            # self._progressbar.reset()
            self._progressbar.setFormat('%p %')
            self._progressbar.setRange(0, 100)
            self._progressbar.setValue(0)

        self._ui.comboBox_output_proc_index.clear()
        self._ui.comboBox_output_proc_index.addItem('Log')
        self._ui.comboBox_output_proc_index.addItems([str(f'Proc. {i}') for i in range(self._using_proc_num)])

        # Run Process
        for proc_idx in range(self._using_proc_num):
            self._funcs_get_finished.append(create_func_args(self._get_finished, proc_idx))
            self._funcs_changed_state.append(create_func_args(self._changed_state, proc_idx))
            self._funcs_get_message_output.append(create_func_args(self._get_message_output, proc_idx))
            self._funcs_get_message_error.append(create_func_args(self._get_message_error, proc_idx))

            self._procs_state.append(QProcess.ProcessState.NotRunning)
            self._all_msgs.append('')
            self._start_time.append(0)
            self._elapsed_time.append(0)

        for proc_idx in range(self._using_proc_num):
            # State: Not Running
            new_proc = QProcess()
            # new_proc.errorOccurred.connect()   # Don't use, there is some bug in QProcess
            new_proc.finished.connect(self._funcs_get_finished[proc_idx])
            new_proc.stateChanged.connect(self._funcs_changed_state[proc_idx])
            new_proc.readyReadStandardOutput.connect(self._funcs_get_message_output[proc_idx])
            new_proc.readyReadStandardError.connect(self._funcs_get_message_error[proc_idx])
            new_proc.setWorkingDirectory(self._working_path)

            if self._added_env:
                new_proc.setProcessEnvironment(self._added_env)

            self._procs.append(new_proc)

            _cmd = self._commands.pop(0)
            self._procs_cmd.append([self._cur_count, _cmd])
            self._cur_count += 1

            self._thread_find_cpus.append(None)
            self._get_usable_procs(proc_idx)
        return True

    def _get_usable_procs(self, proc_idx):
        if proc_idx >= len(self._thread_find_cpus):
            return

        if self._cur_count == 2:
            self._progressbar.setValue(1)
            # self.sig_proc_status.emit(proc_idx, cpu_id, pid, 'Running=1')

        if self._thread_find_cpus[proc_idx] is not None:
            self._thread_find_cpus[proc_idx].terminate()
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
        if self._show_command:
            self.add_log_command(self._procs_cmd[proc_idx][0], _cmd)
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

        split_cmd = self._procs[proc_idx].splitCommand(_cmd)
        if len(split_cmd) == 1:
            self._procs[proc_idx].start(split_cmd[0])
        elif len(split_cmd) > 1:
            self._procs[proc_idx].start(split_cmd[0], split_cmd[1:])
        else:   # Cannot reach this point
            self._stopped_proc(proc_idx, f'There is no command: {_cmd}')
            return False

        # State: Starting
        cpu_id = get_cpu
        pid = -1  # Will be set after process starts
        self.sig_proc_status.emit(proc_idx, cpu_id, pid, 'Starting')
        _start_state = self._procs[proc_idx].waitForStarted(-1)
        if _start_state:
            # State: Running
            pid = self._procs[proc_idx].processId()
            assign_cpu(pid, get_cpu)
            self.sig_proc_status.emit(proc_idx, cpu_id, pid, 'Running')
            return True
        else:
            self._stopped_proc(proc_idx, f'Not an executable file or command, or not found: {split_cmd[0]}')
            return False

    def _stopped_proc(self, proc_idx, msg='Stopped'):
        self._procs[proc_idx] = None

        self._procs_state[proc_idx] = QProcess.ProcessState.NotRunning
        self.show_process_state(proc_idx)

        self.add_log_error(self._procs_cmd[proc_idx][0], msg)

        if self._progressbar is not None:
            self._progressbar.setFormat('Stopped')

        if self._funcs_restore_ui:
            self._run_restore_ui()

    def _get_message_output(self, proc_idx):
        _message = bytes(self._procs[proc_idx].readAllStandardOutput()).decode('utf-8', errors='replace')
        if _message:
            self.add_message_output(_message, proc_idx)

    def _get_message_error(self, proc_idx):
        _message = bytes(self._procs[proc_idx].readAllStandardError()).decode('utf-8', errors='replace')
        if _message:
            self.add_message_error(_message, proc_idx)

    def _get_finished(self, proc_idx, exit_code, *args):
        is_next = False
        is_stopped = False

        self._procs[proc_idx] = None

        if exit_code == 0:
            self.add_log_end(self._procs_cmd[proc_idx][0])
            if self._commands:
                self._elapsed_time[proc_idx] = time.time() - self._start_time[proc_idx]
                self._run_next(proc_idx)
                is_next = True
        else:   # Error
            if exit_code == 2:
                self.add_log_error(self._procs_cmd[proc_idx][0], f'No such file or directory (Check the log for details)')
                is_stopped = True
            else:   # Error 1, ...
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
                # self.sig_proc_status.emit(proc_idx, -1, -1, f'Running-{cur_value}%')

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
                # self.sig_proc_status.emit(proc_idx, -1, -1, f'Finished-100%')

        if self._funcs_restore_ui:
            self._run_restore_ui()

        # Only wait for thread if not proceeding to next command
        # (if is_next is True, a new thread was started in _run_next)
        if not is_next and self._thread_find_cpus[proc_idx] is not None:
            self._thread_find_cpus[proc_idx].wait()
            self._thread_find_cpus[proc_idx] = None

    def _run_next(self, proc_idx):
        new_proc = QProcess()
        self._procs[proc_idx] = new_proc

        # State: Not Running
        new_proc.stateChanged.connect(self._funcs_changed_state[proc_idx])
        new_proc.readyReadStandardOutput.connect(self._funcs_get_message_output[proc_idx])
        new_proc.readyReadStandardError.connect(self._funcs_get_message_error[proc_idx])
        new_proc.finished.connect(self._funcs_get_finished[proc_idx])
        new_proc.setWorkingDirectory(self._working_path)

        if self._added_env:
            new_proc.setProcessEnvironment(self._added_env)

        _cmd = self._commands.pop(0)
        self._procs_cmd[proc_idx] = [self._cur_count, _cmd]
        self._cur_count += 1

        self._get_usable_procs(proc_idx)

    def _changed_state(self, proc_idx, state):
        self._procs_state[proc_idx] = state

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
                remain_time = total_time / (self._using_proc_num * 0.85)  # parallel value (0.8~0.9)

                hour, min, sec = seconds_to_time(remain_time)
                _str_ete = ''  # '≦'
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
                    self._thread_find_cpus[i].wait()
            return

        self._commands = []

        for i, proc  in enumerate(self._procs):
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
                self._thread_find_cpus[i].stop_finding()
                self._thread_find_cpus[i].wait()

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
            psutil.wait_procs([parent], timeout=3)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def pause_process(self):
        if not self.is_running():
            for i, d in enumerate(self._thread_find_cpus):
                if d is not None:
                    d.stop_finding()
                    d.wait()
            return

        for i, proc in enumerate(self._procs):
            if self._procs_state[i] in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
                proc_id = proc.processId()
                try:
                    psutil.Process(proc_id).suspend()
                    # subprocess.run(f'kill -STOP {proc_id}', shell=True)
                    # os.system('kill -STOP %proc' % self._process_id)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            elif self._procs_state[i] == QProcess_ProcessState_WAITING:
                self._thread_find_cpus[i].stop_finding()
                self._thread_find_cpus[i].wait()

            # elif self._procs_state[i] == QProcess_ProcessState_START:
            #     ...
            else:
                ...

        self._pause_all_proc = True
        self.add_log_notice('Paused')
        # self.sig_proc_status.emit(0, -1, -1, 'Paused')

    def resume_process(self):
        if not self.is_running():
            return

        for i, proc in enumerate(self._procs):
            state = self._procs_state[i]
            if state in (QProcess.ProcessState.Starting, QProcess.ProcessState.Running):
                proc_id = proc.processId()
                try:
                    p = psutil.Process(proc_id)
                    p.resume()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            elif state in (QProcess_ProcessState_WAITING, QProcess_ProcessState_START):
                self._get_usable_procs(i)

        self._pause_all_proc = False
        self.add_log_notice('Continue')
        # self.sig_proc_status.emit(0, -1, -1, 'Continue')
