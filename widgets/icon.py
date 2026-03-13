from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap


def create_icon(path=''):
    icon = QIcon()
    icon.addPixmap(QPixmap(path))
    return icon


def add_icon(widget, path, size=36):
    icon = QIcon()
    icon.addPixmap(QPixmap(path))
    widget.setIcon(icon)
    widget.setIconSize(QSize(size, size))
