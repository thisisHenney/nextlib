from PySide6.QtCore import QObject, Signal


class Broadcaster(QObject):
    common_signal = Signal(int, dict)

    simple_signal = Signal(int)

    event_signal = Signal(int, dict)
    close_signal = Signal(int, dict)

    state_signal = Signal(int, dict)

broadcaster = Broadcaster()


