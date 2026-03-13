from PySide6.QtGui import QPixmap


class Picture:
    def __init__(self, path=''):
        self.pixmap = None
        self.label = None
        self.path = path
        self.is_scaled = False

        self._initialize()

    def _initialize(self):
        self.load_file(self.path)

    def load_file(self, path):
        if path:
            self.pixmap = QPixmap(path)

    def set_label_widget(self, label=None):
        if label is not None:
            self.label = label

    def set_resize(self, is_scaled=True):
        self.is_scaled = True
        if self.label is not None:
            self.label.setScaledContents(True)

    def show(self, is_resize=True):
        if self.label is None or self.pixmap is None:
            return

        self.label.setPixmap(self.pixmap)
        if is_resize:
            self.set_resize(True)
