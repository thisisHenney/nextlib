"""
개선된 DialogBox 사용 예제
"""

import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel

# 상대 경로로 import
from dialogbox_improved import (
    FileDialogBox, DirDialogBox, DialogBoxConfig,
    select_folder, select_file, save_as,
    CommonFilters
)


class DialogBoxDemo(QMainWindow):
    """DialogBox 데모 윈도우"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DialogBox Demo")
        self.setGeometry(100, 100, 400, 500)

        # 중앙 위젯
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # 결과 라벨
        self.result_label = QLabel("No selection yet")
        self.result_label.setWordWrap(True)
        layout.addWidget(self.result_label)

        # 설정 버튼들
        self.add_section(layout, "Settings")
        self.add_button(layout, "Toggle Path Memory", self.toggle_path_memory)
        self.add_button(layout, "Toggle Hidden Files", self.toggle_hidden_files)

        # 폴더 선택
        self.add_section(layout, "Folder Selection")
        self.add_button(layout, "Select Folder", self.demo_select_folder)
        self.add_button(layout, "Create Folder", self.demo_create_folder)
        self.add_button(layout, "Select Folder (Quick)", self.demo_quick_folder)

        # 파일 선택
        self.add_section(layout, "File Selection")
        self.add_button(layout, "Open File", self.demo_open_file)
        self.add_button(layout, "Open Files (Multiple)", self.demo_open_files)
        self.add_button(layout, "Open with Validation", self.demo_open_with_validation)
        self.add_button(layout, "Open File (Quick)", self.demo_quick_file)

        # 파일 저장
        self.add_section(layout, "File Save")
        self.add_button(layout, "Save File", self.demo_save_file)
        self.add_button(layout, "Save with Default Name", self.demo_save_with_default)
        self.add_button(layout, "Save As (Quick)", self.demo_quick_save)

        # 필터 예제
        self.add_section(layout, "Filter Examples")
        self.add_button(layout, "Open Image", self.demo_image_filter)
        self.add_button(layout, "Open JSON", self.demo_json_filter)
        self.add_button(layout, "Open CAD File", self.demo_cad_filter)
        self.add_button(layout, "Custom Filter", self.demo_custom_filter)

        layout.addStretch()

        # 현재 설정 표시
        self.update_settings_display()

    def add_section(self, layout, title):
        """섹션 구분선 추가"""
        label = QLabel(f"\n--- {title} ---")
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)

    def add_button(self, layout, text, callback):
        """버튼 추가"""
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        layout.addWidget(btn)

    def update_result(self, result):
        """결과 업데이트"""
        if result is None:
            self.result_label.setText("Cancelled")
        elif isinstance(result, list):
            if result:
                paths = "\n".join(str(p) for p in result)
                self.result_label.setText(f"Selected {len(result)} file(s):\n{paths}")
            else:
                self.result_label.setText("No files selected")
        else:
            self.result_label.setText(f"Selected:\n{result}")

    def update_settings_display(self):
        """설정 상태 표시"""
        self.setWindowTitle(
            f"DialogBox Demo - "
            f"Memory: {'ON' if DialogBoxConfig.remember_paths else 'OFF'} | "
            f"Hidden: {'SHOW' if DialogBoxConfig.show_hidden_files else 'HIDE'}"
        )

    # ============================================================
    # 설정
    # ============================================================

    def toggle_path_memory(self):
        """경로 기억 토글"""
        DialogBoxConfig.remember_paths = not DialogBoxConfig.remember_paths
        self.update_settings_display()
        self.result_label.setText(
            f"Path Memory: {'Enabled' if DialogBoxConfig.remember_paths else 'Disabled'}"
        )

    def toggle_hidden_files(self):
        """숨김 파일 표시 토글"""
        DialogBoxConfig.show_hidden_files = not DialogBoxConfig.show_hidden_files
        self.update_settings_display()
        self.result_label.setText(
            f"Show Hidden Files: {'Enabled' if DialogBoxConfig.show_hidden_files else 'Disabled'}"
        )

    # ============================================================
    # 폴더 선택
    # ============================================================

    def demo_select_folder(self):
        """폴더 선택 데모"""
        result = DirDialogBox.open_folder(
            parent=self,
            title="프로젝트 폴더 선택",
            path=Path.home()
        )
        self.update_result(result)

    def demo_create_folder(self):
        """폴더 생성 데모"""
        result = DirDialogBox.create_folder(
            parent=self,
            title="새 폴더 생성",
        )
        self.update_result(result)

    def demo_quick_folder(self):
        """빠른 폴더 선택"""
        result = select_folder(self)
        self.update_result(result)

    # ============================================================
    # 파일 선택
    # ============================================================

    def demo_open_file(self):
        """파일 열기 데모"""
        result = FileDialogBox.open_file(
            parent=self,
            title="파일 열기",
            filters=CommonFilters.ALL
        )
        self.update_result(result)

    def demo_open_files(self):
        """복수 파일 열기 데모"""
        result = FileDialogBox.open_files(
            parent=self,
            title="여러 파일 선택",
            filters=CommonFilters.TEXT
        )
        self.update_result(result)

    def demo_open_with_validation(self):
        """검증 기능 데모"""
        def validate_size(path: Path) -> bool:
            """1MB 이하만 허용"""
            return path.stat().st_size <= 1024 * 1024

        result = FileDialogBox.open_file(
            parent=self,
            title="파일 열기 (1MB 이하만)",
            filters=CommonFilters.ALL,
            validate=validate_size
        )
        self.update_result(result)

    def demo_quick_file(self):
        """빠른 파일 선택"""
        result = select_file(self, filters=CommonFilters.TEXT)
        self.update_result(result)

    # ============================================================
    # 파일 저장
    # ============================================================

    def demo_save_file(self):
        """파일 저장 데모"""
        result = FileDialogBox.save_file(
            parent=self,
            title="파일 저장",
            filters=CommonFilters.TEXT
        )
        self.update_result(result)

    def demo_save_with_default(self):
        """기본 파일명 지정 데모"""
        result = FileDialogBox.save_file(
            parent=self,
            title="결과 저장",
            filters=CommonFilters.JSON,
            default_filename="result.json"
        )
        self.update_result(result)

    def demo_quick_save(self):
        """빠른 저장"""
        result = save_as(
            self,
            filters=CommonFilters.TEXT,
            default_filename="output.txt"
        )
        self.update_result(result)

    # ============================================================
    # 필터 예제
    # ============================================================

    def demo_image_filter(self):
        """이미지 필터 데모"""
        result = FileDialogBox.open_file(
            parent=self,
            title="이미지 선택",
            filters=CommonFilters.IMAGE
        )
        self.update_result(result)

    def demo_json_filter(self):
        """JSON 필터 데모"""
        result = FileDialogBox.open_file(
            parent=self,
            title="JSON 파일 열기",
            filters=CommonFilters.JSON
        )
        self.update_result(result)

    def demo_cad_filter(self):
        """CAD 필터 데모"""
        result = FileDialogBox.open_file(
            parent=self,
            title="CAD 파일 열기",
            filters=CommonFilters.CAD
        )
        self.update_result(result)

    def demo_custom_filter(self):
        """커스텀 필터 데모"""
        result = FileDialogBox.open_file(
            parent=self,
            title="로그 파일 선택",
            filters=CommonFilters.custom("log", "txt", "out")
        )
        self.update_result(result)


def main():
    """메인 함수"""
    app = QApplication(sys.argv)

    # 전역 설정 (선택사항)
    DialogBoxConfig.remember_paths = True
    DialogBoxConfig.confirm_overwrite = True

    window = DialogBoxDemo()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
