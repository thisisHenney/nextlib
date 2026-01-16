import sys
import json
import os
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QGroupBox, QLabel, QLineEdit
)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("연동형 자동저장 GUI")

        self.data = {}

        # 상단 레이아웃 (버튼)
        top_layout = QHBoxLayout()
        self.load_btn = QPushButton("파일에서 읽어오기")
        self.save_btn = QPushButton("파일로 저장하기")
        top_layout.addWidget(self.load_btn)
        top_layout.addWidget(self.save_btn)

        # QComboBox1은 버튼 아래에 배치
        self.combo1 = QComboBox()
        self.combo1.addItems(["A", "B", "C"])

        # 그룹박스1 (QComboBox1)
        self.groupbox1 = QGroupBox("AComboBox1 그룹")
        gb1_layout = QVBoxLayout()
        gb1_layout.addWidget(self.combo1)

        # Label2(QLineEdit)는 QComboBox1과만 연동
        gb1_layout.addWidget(QLabel("Label2 텍스트:"))
        self.label2 = QLineEdit("Label2")
        gb1_layout.addWidget(self.label2)

        # 그룹박스2 (QComboBox2) - 그룹박스1의 하위
        self.groupbox2 = QGroupBox("QComboBox2 연동")
        gb2_layout = QVBoxLayout()
        self.lineedit2 = QLineEdit()
        self.combo2 = QComboBox()
        self.combo2.addItems(["A-1", "A-2", "A-3"])
        gb2_layout.addWidget(QLabel("LineEdit2:"))
        gb2_layout.addWidget(self.lineedit2)
        gb2_layout.addWidget(self.combo2)
        self.groupbox2.setLayout(gb2_layout)

        # 그룹박스3 (QComboBox3) - 그룹박스2의 하위
        self.groupbox3 = QGroupBox("QComboBox3 연동")
        gb3_layout = QVBoxLayout()
        self.label3 = QLineEdit("Label3")
        self.lineedit3 = QLineEdit()
        self.combo3 = QComboBox()
        self.combo3.addItems(["A-1-x", "A-1-y", "A-1-z"])
        gb3_layout.addWidget(QLabel("Label3 텍스트:"))
        gb3_layout.addWidget(self.label3)
        gb3_layout.addWidget(QLabel("LineEdit3:"))
        gb3_layout.addWidget(self.lineedit3)
        gb3_layout.addWidget(self.combo3)
        self.groupbox3.setLayout(gb3_layout)

        # 계층 구조 반영
        gb2_layout.addWidget(self.groupbox3)
        gb1_layout.addWidget(self.groupbox2)
        self.groupbox1.setLayout(gb1_layout)

        # 메인 레이아웃
        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.groupbox1)
        self.setLayout(main_layout)

        # 시그널 연결
        self.combo1.currentIndexChanged.connect(self.on_combo1_changed)
        self.combo2.currentIndexChanged.connect(self.on_combo2_changed)
        self.combo3.currentIndexChanged.connect(self.save_all)
        self.lineedit2.textChanged.connect(self.save_lineedit2)
        self.lineedit3.textChanged.connect(self.save_all)
        self.label2.textChanged.connect(self.save_label2)  # Label2는 QComboBox1과만 연동
        self.label3.textChanged.connect(self.save_all)
        self.load_btn.clicked.connect(self.load_data)
        self.save_btn.clicked.connect(self.save_data)

        # 초기화
        self.on_combo1_changed(0)

    def save_label2(self):
        c1 = self.combo1.currentText()
        if c1 not in self.data:
            self.data[c1] = {}
        self.data[c1]['label2'] = self.label2.text()
        self.save_data(auto=True)

    def save_lineedit2(self):
        c1, c2 = self.combo1.currentText(), self.combo2.currentText()
        if c1 not in self.data:
            self.data[c1] = {}
        if c2 not in self.data[c1]:
            self.data[c1][c2] = {}
        self.data[c1][c2]['lineedit2'] = self.lineedit2.text()
        self.save_data(auto=True)

    def save_all(self):
        c1, c2, c3 = self.combo1.currentText(), self.combo2.currentText(), self.combo3.currentText()
        if c1 not in self.data:
            self.data[c1] = {}
        if c2 not in self.data[c1]:
            self.data[c1][c2] = {}
        if 'sub' not in self.data[c1][c2]:
            self.data[c1][c2]['sub'] = {}
        self.data[c1][c2]['sub'][c3] = {
            'label3': self.label3.text(),
            'lineedit3': self.lineedit3.text()
        }
        self.save_data(auto=True)

    def on_combo1_changed(self, idx):
        self.combo2.blockSignals(True)
        self.combo2.clear()
        self.combo2.addItems([f"{self.combo1.currentText()}-1", f"{self.combo1.currentText()}-2", f"{self.combo1.currentText()}-3"])
        self.combo2.blockSignals(False)
        self.load_label2()
        self.on_combo2_changed(0)

    def on_combo2_changed(self, idx):
        self.combo3.blockSignals(True)
        self.combo3.clear()
        self.combo3.addItems([f"{self.combo2.currentText()}-x", f"{self.combo2.currentText()}-y", f"{self.combo2.currentText()}-z"])
        self.combo3.blockSignals(False)
        self.load_fields()

    def load_label2(self):
        c1 = self.combo1.currentText()
        val = self.data.get(c1, {})
        self.label2.setText(val.get('label2', 'Label2'))

    def load_fields(self):
        c1, c2 = self.combo1.currentText(), self.combo2.currentText()
        val = self.data.get(c1, {}).get(c2, {})
        self.lineedit2.setText(val.get('lineedit2', ''))
        # QComboBox3 관련 값
        c3 = self.combo3.currentText()
        subval = val.get('sub', {}).get(c3, {})
        self.label3.setText(subval.get('label3', 'Label3'))
        self.lineedit3.setText(subval.get('lineedit3', ''))

    def load_data(self):
        if os.path.exists("mydata.json"):
            with open("mydata.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
            self.on_combo1_changed(0)

    def save_data(self, auto=False):
        with open("mydata.json", "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        if not auto:
            print("수동 저장 완료")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
