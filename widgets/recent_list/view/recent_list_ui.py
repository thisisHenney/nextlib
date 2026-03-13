# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'recent_list.ui'
##
## Created by: Qt User Interface Compiler version 6.4.3
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QLayout,
    QLineEdit, QListView, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget)

class Ui_RecentListForm(object):
    def setupUi(self, RecentListForm):
        if not RecentListForm.objectName():
            RecentListForm.setObjectName(u"RecentListForm")
        RecentListForm.resize(400, 295)
        self.verticalLayout = QVBoxLayout(RecentListForm)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setSizeConstraint(QLayout.SetMinAndMaxSize)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.lineEdit_search = QLineEdit(RecentListForm)
        self.lineEdit_search.setObjectName(u"lineEdit_search")
        self.lineEdit_search.setStyleSheet(u"QLineEdit{\n"
"	height: 24 px;\n"
"	border: 1px solid darkgray;\n"
"	border-radius: 4px;\n"
"	padding: 2px;\n"
"}\n"
"\n"
"QLineEdit::hover{\n"
"    border: 1px solid darkorange;\n"
"   background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #FFE5B5, stop: 1 #FCBE4C);\n"
"}")
        self.lineEdit_search.setClearButtonEnabled(True)

        self.verticalLayout.addWidget(self.lineEdit_search)

        self.frame = QFrame(RecentListForm)
        self.frame.setObjectName(u"frame")
        self.frame.setStyleSheet(u"QFrame{\n"
"	border: 1px solid darkgray;\n"
"	border-radius: 4px;\n"
"}\n"
"")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Sunken)
        self.frame.setLineWidth(1)
        self.verticalLayout_2 = QVBoxLayout(self.frame)
        self.verticalLayout_2.setSpacing(9)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(4, 4, 4, 4)
        self.listWidget = QListWidget(self.frame)
        self.listWidget.setObjectName(u"listWidget")
        font = QFont()
        font.setPointSize(10)
        self.listWidget.setFont(font)
        self.listWidget.setMouseTracking(False)
        self.listWidget.setFocusPolicy(Qt.NoFocus)
        self.listWidget.setStyleSheet(u"QListWidget {\n"
"	border: none;\n"
"	background: transparent;\n"
"}\n"
"\n"
"QListWidget::item:hover {\n"
"    border-radius: 6px;\n"
"    color: black;\n"
"    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,\n"
"                                stop: 0 #FFE5B5, stop: 1 #FCBE4C);\n"
"}\n"
"\n"
"QListWidget::item {\n"
"    padding: 2px;\n"
"    border-radius: 6px;\n"
"}\n"
"")
        self.listWidget.setFrameShape(QFrame.Box)
        self.listWidget.setFrameShadow(QFrame.Sunken)
        self.listWidget.setAlternatingRowColors(False)
        self.listWidget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.listWidget.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.listWidget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.listWidget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.listWidget.setSpacing(0)
        self.listWidget.setViewMode(QListView.ListMode)
        self.listWidget.setUniformItemSizes(True)
        self.listWidget.setSelectionRectVisible(False)
        self.listWidget.setItemAlignment(Qt.AlignVCenter)

        self.verticalLayout_2.addWidget(self.listWidget)

        self.verticalLayout.addWidget(self.frame)

        self.retranslateUi(RecentListForm)

        QMetaObject.connectSlotsByName(RecentListForm)
    # setupUi

    def retranslateUi(self, RecentListForm):
        RecentListForm.setWindowTitle(QCoreApplication.translate("RecentListForm", u"Form", None))
        self.lineEdit_search.setPlaceholderText(QCoreApplication.translate("RecentListForm", u"Search...", None))
    # retranslateUi
