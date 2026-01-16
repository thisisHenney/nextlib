#!/usr/bin/env python3
# -*- coding:utf8 -*-

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QWidget
from NextLib.Widgets.Icon import load_basic_icon


class ClientWidget(QWidget):
    def __init__(self, clientThread, ui_foam):
        super().__init__()

        self._ui = ui_foam()
        self._ui.setupUi(self)

        self.client = clientThread()
        self.ip = ""
        self.port = 0

        self._init_ui()
        self._init_signal()

    def _init_ui(self):
        ui = self._ui

        ui.ip_comboBox.lineEdit().returnPressed.connect(self.connect_to_server)

        ui.port_comboBox.setValidator(QIntValidator())
        ui.port_comboBox.lineEdit().returnPressed.connect(self.connect_to_server)

        ui.settings_button.setIcon(load_basic_icon('settings.png'))

        ui.connect_button.clicked.connect(self.connect_to_server)
        ui.disconnect_button.clicked.connect(self.disconnect_from_server)

        # ui.send_message_edit.returnPressed.connect(self.send_message)
        ui.send_button.setIcon(load_basic_icon('send.png'))
        ui.send_button.clicked.connect(self.send_message)

    def _init_signal(self):
        ui = self._ui
        self.client.connected.connect(self.on_connected)
        self.client.disconnected.connect(self.on_disconnected)
        self.client.received_message.connect(self.on_message)
        self.client.received_tuple_message.connect(self.on_message_tuple)
        self.client.notice.connect(self.on_notice)
        self.client.restore_ui.connect(self.on_restore_ui)

    def set_defaults(self):
        self.set_disconnected_UI()

    def end(self):
        self.disconnect_from_server()

    def on_connected(self, ip, port):
        self.ip = ip
        self.port = port
        self._ui.received_message_edit.append(f'>> Connected')
        self.set_connected_UI()

    def on_disconnected(self):
        self.ip = ""
        self.port = 0
        self._ui.received_message_edit.append(f'>> Disconnected')
        self.set_disconnected_UI()

    def on_message(self, msg):
        self._ui.received_message_edit.append(msg)

    def on_message_tuple(self, msg):
        for d in msg:
            self._ui.received_message_edit.append(d)

    def on_notice(self, msg):
        self._ui.received_message_edit.append(msg)

    def on_restore_ui(self):
        self.set_disconnected_UI()

    def connect_to_server(self):
        ui = self._ui

        ip = ui.ip_comboBox.currentText()
        port = ui.port_comboBox.currentText()

        ui.connect_button.setText('Connecting')
        ui.connect_button.setEnabled(False)

        self.client.set_ip_port(ip, int(port))
        self.client.start()

    def disconnect_from_server(self):
        if self.client is None:
            return
        self.client.disconnect_from_server()
        self.set_disconnected_UI()

    def send_message(self, msg='', msg2=''):
        ui = self._ui

        if not msg:
            msg = ui.send_message_edit.text()
        if msg and self.client.is_connected():
            self.client.send_message(msg)

    def set_connected_UI(self):
        ui = self._ui
        ui.ip_comboBox.setEnabled(False)
        ui.port_comboBox.setEnabled(False)
        ui.connect_button.setEnabled(False)
        ui.connect_button.setText('Connected')
        ui.disconnect_button.setEnabled(True)
        ui.send_message_edit.setEnabled(True)
        ui.send_button.setEnabled(True)

    def set_disconnected_UI(self):
        ui = self._ui
        ui.ip_comboBox.setEnabled(True)
        ui.port_comboBox.setEnabled(True)
        ui.connect_button.setText('Connect')
        ui.connect_button.setEnabled(True)
        ui.disconnect_button.setEnabled(False)
        ui.send_message_edit.setEnabled(False)
        ui.send_button.setEnabled(False)
