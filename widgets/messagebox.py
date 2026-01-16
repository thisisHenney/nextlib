from PySide6.QtWidgets import QMessageBox

def messagebox(parent=None, text=''):
    QMessageBox.information(parent, 'Notice', text)
    return True

def messagebox_warning(parent=None, text=''):
    result = QMessageBox.warning(
        parent, 'Warning', text,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
    )
    return result == QMessageBox.StandardButton.Yes

def messagebox_error(parent=None, text=''):
    QMessageBox.critical(parent, 'Error', text)
    return True

def messagebox_question(parent=None, text=''):
    result = QMessageBox.question(parent, 'Question', text)
    return result == QMessageBox.StandardButton.Yes
