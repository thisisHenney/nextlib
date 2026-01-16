# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'message_pre.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
    QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QSpacerItem, QStackedWidget, QTextEdit,
    QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(568, 572)
        self.verticalLayout = QVBoxLayout(Form)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.groupBox_Message = QGroupBox(Form)
        self.groupBox_Message.setObjectName(u"groupBox_Message")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_Message.sizePolicy().hasHeightForWidth())
        self.groupBox_Message.setSizePolicy(sizePolicy)
        self.groupBox_Message.setMinimumSize(QSize(300, 0))
        font = QFont()
        font.setFamilies([u"Ubuntu"])
        font.setPointSize(9)
        font.setBold(True)
        self.groupBox_Message.setFont(font)
        self.groupBox_Message.setStyleSheet(u"QGroupBox {\n"
"	border: 1px solid;\n"
"	border-radius: 6px;\n"
"	margin-top: 7;\n"
"	border-color : rgb(150, 150, 150);\n"
"	padding: 3px;\n"
"}\n"
"\n"
"QGroupBox::title {\n"
"	subcontrol-origin: margin;\n"
"	subcontrol-position: top left;\n"
"	left : 16;\n"
"	padding: 0 3 0 3;\n"
"	font-weight: bold;\n"
"}")
        self.verticalLayout_16 = QVBoxLayout(self.groupBox_Message)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(-1, 9, -1, -1)
        self.stackedWidget = QStackedWidget(self.groupBox_Message)
        self.stackedWidget.setObjectName(u"stackedWidget")
        font1 = QFont()
        font1.setPointSize(9)
        self.stackedWidget.setFont(font1)
        self.page_log = QWidget()
        self.page_log.setObjectName(u"page_log")
        self.verticalLayout_2 = QVBoxLayout(self.page_log)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.textEdit_log = QTextEdit(self.page_log)
        self.textEdit_log.setObjectName(u"textEdit_log")
        self.textEdit_log.setFont(font1)
        self.textEdit_log.viewport().setProperty(u"cursor", QCursor(Qt.CursorShape.IBeamCursor))
        self.textEdit_log.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.textEdit_log.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.textEdit_log.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.textEdit_log.setReadOnly(True)
        self.textEdit_log.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_2.addWidget(self.textEdit_log)

        self.stackedWidget.addWidget(self.page_log)
        self.page_output = QWidget()
        self.page_output.setObjectName(u"page_output")
        self.verticalLayout_3 = QVBoxLayout(self.page_output)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.textEdit_output = QTextEdit(self.page_output)
        self.textEdit_output.setObjectName(u"textEdit_output")
        self.textEdit_output.setFont(font1)
        self.textEdit_output.viewport().setProperty(u"cursor", QCursor(Qt.CursorShape.IBeamCursor))
        self.textEdit_output.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.textEdit_output.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.textEdit_output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.textEdit_output.setReadOnly(True)
        self.textEdit_output.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse|Qt.TextInteractionFlag.TextSelectableByKeyboard|Qt.TextInteractionFlag.TextSelectableByMouse)

        self.verticalLayout_3.addWidget(self.textEdit_output)

        self.stackedWidget.addWidget(self.page_output)

        self.verticalLayout_16.addWidget(self.stackedWidget)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(-1, 0, -1, -1)
        self.label_9 = QLabel(self.groupBox_Message)
        self.label_9.setObjectName(u"label_9")
        font2 = QFont()
        font2.setPointSize(10)
        self.label_9.setFont(font2)

        self.horizontalLayout_12.addWidget(self.label_9)

        self.comboBox_output_proc_index = QComboBox(self.groupBox_Message)
        self.comboBox_output_proc_index.addItem("")
        self.comboBox_output_proc_index.setObjectName(u"comboBox_output_proc_index")
        self.comboBox_output_proc_index.setMinimumSize(QSize(20, 0))
        self.comboBox_output_proc_index.setMaximumSize(QSize(90, 16777215))
        self.comboBox_output_proc_index.setFont(font2)
        self.comboBox_output_proc_index.setStyleSheet(u"QComboBox{\n"
"	combobox-popup: 0;\n"
"}\n"
"")

        self.horizontalLayout_12.addWidget(self.comboBox_output_proc_index)

        self.horizontalSpacer = QSpacerItem(0, 20, QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer)

        self.checkBox_tracking = QCheckBox(self.groupBox_Message)
        self.checkBox_tracking.setObjectName(u"checkBox_tracking")
        self.checkBox_tracking.setEnabled(True)
        self.checkBox_tracking.setFont(font1)
        self.checkBox_tracking.setStyleSheet(u"QCheckBox::hover{\n"
"   color:  blue;\n"
"}")
        self.checkBox_tracking.setChecked(True)

        self.horizontalLayout_12.addWidget(self.checkBox_tracking)

        self.pushButton_clear = QPushButton(self.groupBox_Message)
        self.pushButton_clear.setObjectName(u"pushButton_clear")
        self.pushButton_clear.setMinimumSize(QSize(80, 22))
        self.pushButton_clear.setFont(font1)
        self.pushButton_clear.setStyleSheet(u"QPushButton {\n"
"    color: #000000;\n"
"    border: 1px solid #a0a0a0;\n"
"	border-radius: 4px;\n"
"    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #fcfcfc, stop: 1 #eeeeee);\n"
"}\n"
"\n"
"QPushButton::hover {\n"
"    border: 1px solid blue;\n"
"    border-radius: 4px;\n"
"	background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #e5f1fb, stop: 1 #c1e0fa);\n"
"}\n"
"\n"
"QPushButton::pressed {\n"
"    border: 1px solid blue;\n"
"    border-radius: 4px;\n"
"	background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #c1e0fa, stop: 1 #e5f1fb);\n"
"}\n"
"\n"
"QPushButton::disabled {\n"
"    border-radius: 4px;\n"
"	background-color: #dddddd;\n"
"}")

        self.horizontalLayout_12.addWidget(self.pushButton_clear)

        self.horizontalLayout_12.setStretch(2, 1)

        self.verticalLayout_16.addLayout(self.horizontalLayout_12)

        self.progressBar = QProgressBar(self.groupBox_Message)
        self.progressBar.setObjectName(u"progressBar")
        self.progressBar.setMaximumSize(QSize(16777215, 16777215))
        self.progressBar.setFont(font2)
        self.progressBar.setStyleSheet(u"QProgressBar {\n"
"	border: 1px solid #a0a0a0;   \n"
"	border-radius: 4px;\n"
"	text-align: center;\n"
"}\n"
"\n"
"QProgressBar::chunk {\n"
"	background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #1C76C1, stop: 1 #8CCBFF);\n"
"	border-radius: 4px;\n"
"}\n"
"\n"
"")
        self.progressBar.setValue(50)
        self.progressBar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progressBar.setTextVisible(True)
        self.progressBar.setInvertedAppearance(False)

        self.verticalLayout_16.addWidget(self.progressBar)


        self.verticalLayout.addWidget(self.groupBox_Message)


        self.retranslateUi(Form)

        self.stackedWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.groupBox_Message.setTitle(QCoreApplication.translate("Form", u"< Message >", None))
        self.label_9.setText(QCoreApplication.translate("Form", u"Output", None))
        self.comboBox_output_proc_index.setItemText(0, QCoreApplication.translate("Form", u"Log", None))

        self.checkBox_tracking.setText(QCoreApplication.translate("Form", u"Tracking", None))
        self.pushButton_clear.setText(QCoreApplication.translate("Form", u"Clear View", None))
        self.progressBar.setFormat(QCoreApplication.translate("Form", u"%p %", None))
    # retranslateUi

