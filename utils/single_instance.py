"""
Single Instance - 애플리케이션 중복 실행 방지

QLocalServer/QLocalSocket 기반으로 동일 애플리케이션의 중복 실행을 방지합니다.

사용 예시:
    from nextlib.utils.single_instance import SingleInstance

    app = QApplication(sys.argv)
    single = SingleInstance("MyApp")

    if not single.try_lock():
        # 이미 실행 중
        QMessageBox.warning(None, "Warning", "Application is already running.")
        sys.exit(0)

    # 정상 실행
    ...
"""

from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtCore import QObject


class SingleInstance(QObject):
    """QLocalServer 기반 단일 인스턴스 관리자.

    Args:
        app_key: 고유 애플리케이션 식별자 (예: "com.nextfoam.BipropThrust")
        parent: 부모 QObject
    """

    def __init__(self, app_key: str, parent=None):
        super().__init__(parent)
        self._app_key = app_key
        self._server = None

    def try_lock(self) -> bool:
        """단일 인스턴스 잠금 시도.

        Returns:
            True: 잠금 성공 (첫 번째 인스턴스)
            False: 잠금 실패 (이미 실행 중)
        """
        if self._is_running():
            return False

        self._server = QLocalServer(self)
        QLocalServer.removeServer(self._app_key)

        if not self._server.listen(self._app_key):
            return False

        return True

    def _is_running(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        connected = socket.waitForConnected(200)
        if connected:
            socket.disconnectFromServer()
            socket.close()
            return True
        socket.close()

        import time
        time.sleep(0.15)

        socket2 = QLocalSocket()
        socket2.connectToServer(self._app_key)
        connected2 = socket2.waitForConnected(200)
        if connected2:
            socket2.disconnectFromServer()
            socket2.close()
            return True
        socket2.close()
        return False

    def unlock(self):
        """잠금 해제."""
        if self._server:
            self._server.close()
            self._server = None
