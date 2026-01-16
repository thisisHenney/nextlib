from PySide6.QtCore import QObject, Signal

# Message
# Notice: 'Ready', 'Start', 'Wait', 'Stop', 'Finish', 'Close', 'Reset', etc.
# Status: 'Ready', 'Started', 'Running', 'Waiting', 'Stopped', 'Finished',
#           'Closed', 'Reset', etc.

class Broadcaster(QObject):
    common_signal = Signal(int, dict)  # ex) priority: 0~1, data = {'Tab':0, 'Status':'Stop'}

    simple_signal = Signal(int)

    event_signal = Signal(int, dict)
    # ready_signal = Signal(int, dict)
    # start_signal = Signal(int, dict)
    # wait_signal = Signal(int, dict)
    # stop_signal = Signal(int, dict)
    # finish_signal = Signal(int, dict)
    close_signal = Signal(int, dict)

    state_signal = Signal(int, dict)
    # started_signal = Signal(int, dict)
    # running_signal = Signal(int, dict)
    # waiting_signal = Signal(int, dict)
    # stopping_signal = Signal(int, dict)
    # finished_signal = Signal(int, dict)

# 전역 변수(프로젝트 내 모든 파일에서 사용가능)로 정의
broadcaster = Broadcaster()     # 이 변수를 다른 파일에서 import 한 후 바로 사용


## Usage (Other.py) ##
# from nextlib.broadcast.broadcaster import broadcaster
#
# broadcaster.notice.connect(self._on_received_notice)
# broadcaster.notice.emit('Notice:Hi')
