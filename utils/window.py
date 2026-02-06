from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QRect
from PySide6.QtGui import QScreen


def center_on_screen(window):
    if window is None:
        return

    screen = window.screen() or QApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()

    frame_geometry = window.frameGeometry()
    frame_geometry.moveCenter(screen_geometry.center())

    window.move(frame_geometry.topLeft())


def save_window_geometry(window) -> dict:
    """
    현재 윈도우의 위치, 크기, 모니터 정보를 dict로 반환.

    Args:
        window: QMainWindow 인스턴스

    Returns:
        {"x", "y", "width", "height", "maximized", "screen_name"} dict
    """
    geometry = {}

    if window.isMaximized():
        geometry["maximized"] = True
    else:
        geometry["maximized"] = False
        geometry["x"] = window.x()
        geometry["y"] = window.y()
        geometry["width"] = window.width()
        geometry["height"] = window.height()

    current_screen = window.screen()
    if current_screen:
        geometry["screen_name"] = current_screen.name()

    return geometry


def restore_window_geometry(window, geometry: dict) -> None:
    """
    저장된 dict로부터 윈도우 위치, 크기, 모니터를 복원.
    위치가 없거나 화면 밖이면 center_on_screen으로 대체.

    Args:
        window: QMainWindow 인스턴스
        geometry: save_window_geometry()가 반환한 dict
    """
    if not geometry:
        center_on_screen(window)
        return

    # 크기 복원
    w = geometry.get("width", 0)
    h = geometry.get("height", 0)
    if w > 0 and h > 0:
        window.resize(w, h)

    # 위치 복원
    x = geometry.get("x", -1)
    y = geometry.get("y", -1)

    if x >= 0 and y >= 0:
        if _is_position_visible(x, y, window.width(), window.height()):
            window.move(x, y)
        else:
            center_on_screen(window)
    else:
        center_on_screen(window)

    # 최대화 상태 복원
    if geometry.get("maximized", False):
        window.showMaximized()


def _is_position_visible(x: int, y: int, w: int, h: int) -> bool:
    """윈도우 위치가 연결된 모니터 중 하나에 보이는지 확인."""
    window_rect = QRect(x, y, w, h)
    for screen in QApplication.screens():
        if screen.availableGeometry().intersects(window_rect):
            return True
    return False
