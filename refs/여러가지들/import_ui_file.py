# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ui 수정중 일 경우
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import sys
from PySide6.QtCore import QFile
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        loader = QUiLoader()

        ui_path = "main.ui"     # ui파일이 있는 경로
        ui_file = QFile(ui_path)
        ui_file.open(QFile.ReadOnly)
        self.ui = loader.load(ui_file, self)
        ui_file.close()

        # 변수 사용법
        # >> self.ui

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1000, 700)
    win.show()
    app.exec()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# ui 수정 완료 후 인 경우
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from NextLib2.tests.Just.View.main2_ui import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # 참고(~_ui.py) 파일에서 아래 항목 주석시키기
        # # MainWindow.setCentralWidget(self.centralwidget)

        # 변수 사용법
        # >> self.ui.tabWidget.~
        # >> self.ui.menuFile.~
        # >> self.ui.statusbar.~

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1000, 700)
    win.show()
    app.exec()