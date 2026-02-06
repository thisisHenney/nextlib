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
        # 기존 인스턴스가 있는지 확인
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)
        if socket.waitForConnected(500):
            # 연결 성공 → 이미 실행 중
            socket.disconnectFromServer()
            return False
        socket.close()

        # 서버 시작 (이 프로세스가 첫 번째 인스턴스)
        self._server = QLocalServer(self)
        # 이전 비정상 종료로 남은 소켓 파일 제거
        QLocalServer.removeServer(self._app_key)

        if not self._server.listen(self._app_key):
            return False

        return True

    def unlock(self):
        """잠금 해제."""
        if self._server:
            self._server.close()
            self._server = None
