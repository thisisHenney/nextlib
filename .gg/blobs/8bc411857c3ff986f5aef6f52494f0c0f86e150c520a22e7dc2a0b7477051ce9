from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QScreen

def center_on_screen(window):
    if window is None:
        return

    screen = window.screen() or QApplication.primaryScreen()
    screen_geometry = screen.availableGeometry()

    frame_geometry = window.frameGeometry()
    frame_geometry.moveCenter(screen_geometry.center())

    window.move(frame_geometry.topLeft())
