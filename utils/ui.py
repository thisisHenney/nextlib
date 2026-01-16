from pathlib import Path
from typing import Optional, Type, Union
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget


def load_ui_file(ui_path: Union[str, Path], parent: Optional[QWidget] = None) -> QWidget:
    """
    ui 파일에서 QWidget 인스턴스 반환
    # Usage:
    ui = load_ui_path(files_info)
    ui.show()
    """
    ui_loader = QUiLoader()
    try:
        widget = ui_loader.load(str(ui_path), parent)
        if widget is None:
            raise RuntimeError(f"Failed to load UI file: {ui_path}")
        return widget
    except Exception as e:
        raise RuntimeError(f"Error loading UI file: {ui_path}") from e


def create_widget_from_ui_class(ui_class: Type, widget: Optional[QWidget] = None) -> QWidget:
    """
    컴파일된 UI 클래스 인스턴스 생성 후 QWidget으로 반환
    """
    if widget is None:
        widget = QWidget()
    ui = ui_class()
    ui.setupUi(widget)
    widget.ui = ui
    ui.widget = widget
    return widget


def load_ui(widget: Optional[QWidget] = None,
            ui_class: Optional[Type] = None) -> Union[QWidget, object]:
    """
    widget과 ui_class를 받아 UI 초기화;
    widget 미제공 시 create_widget_from_ui_class 사용,
    제공 시 ui_class.setupUi 호출

    # Usage:
    ui = load_ui(widget, Ui_MainWindow())  # or Ui_~()
    ui.show()
    """
    if ui_class is None:
        raise ValueError("[!!] ui_class must be provided")

    if widget is None:
        widget = create_widget_from_ui_class(ui_class)
        return widget
    else:
        ui = ui_class()
        ui.setupUi(widget)
        widget.ui = ui
        ui.widget = widget

        """ 이전 코드
        ui = ui_class()
        ui.setupUi(widget)
        ui.widget = widget
        widget.ui = ui
        """
        return ui
