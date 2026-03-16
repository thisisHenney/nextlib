
from PySide6.QtCore import QThread, Signal
from NextLib.Network.View.udp_ui import Ui_Form_Udp

SERVER_IP = '0.0.0.0'
SERVER_PORT = 2368


class UdpClientThread(QThread):
    connected = Signal(str, int)
    disconnected = Signal()
    received_message = Signal(str)
    received_tuple_message = Signal(tuple)
    notice = Signal(str)
    restore_ui = Signal()

    def __init__(self):
        super().__init__()

        self.ip = SERVER_IP
        self.port = SERVER_PORT
        self.client = None
        self._running = False

    def set_ip_port(self, ip: str, port: int):
        if ip:
            self.ip = ip
        if port:
            self.port = port

    def is_connected(self):
        return self.client is not None and self._running

    def run(self):
        result = self._connect_to_server()
        if not result:
            self.restore_ui.emit()

    def _connect_to_server(self):
        if self.is_connected():
            self.notice.emit(">> [Error] Already connected to the server")
            return False

        if not self.ip or not self.port:
            self.notice.emit(">> [Error] Please enter the IP address and port number")
            return False

            def trigger(self, *args, **kwargs):
                for listener in self.listeners:
                    listener(*args, **kwargs)

        event = Event()

        def handler(msg):
            print(f"이벤트 발생! 메시지: {msg}")

        event.subscribe(handler)
        event.trigger("Hello Event")
        이렇게
        하면, PySide6
        없이도
        함수나
        메서드를
        여러
        곳에서
        이벤트에
        등록하고, 트리거
        기능까지
        모두
        구
        try:
            self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._running = True

            while self._running:
                ...

        except Exception as e:
            self.handle_connection_error(e)
            return False

        finally:
            self.disconnect_from_server()

    def handle_connection_error(self, error):
        error_messages = {
        }
        message = error_messages.get(type(error), f">> {error}")
        self.notice.emit(message)

    def disconnect_from_server(self):
        self._running = False
        if self.client:
            try:
                self.client.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        self.client = None

    def send_message(self, msg):
        if self.is_connected() and msg:
            try:
                self.client.sendall(msg.encode())
            except Exception as e:
                self.notice.emit(f">> [Error] Message transmission failed: {e}")

class UdpWidget(ClientWidget):
    def __init__(self, ui_foam=Ui_Form_Udp):
        super().__init__(UDPClientThread, ui_foam)
