"""
후처리 위젯 사용 예제
OpenFOAM 케이스를 로드하고 필드 데이터를 시각화하는 예제
"""
from PySide6.QtWidgets import QApplication
from nextlib.vtk.postprocess_widget import PostprocessWidget
from nextlib.vtk.vtk_manager import vtk_manager


if __name__ == "__main__":
    app = QApplication([])

    # 후처리 위젯 생성
    post_widget = PostprocessWidget(registry=vtk_manager)
    vtk_manager.register("postprocess", post_widget)

    # 윈도우 설정
    post_widget.setWindowTitle("Postprocess Widget Example")
    post_widget.resize(1200, 800)
    post_widget.show()

    # 시그널 연결 예제
    def on_case_loaded(file_path: str):
        print(f"Case loaded: {file_path}")

    def on_field_changed(field: str):
        print(f"Field changed: {field}")

    post_widget.case_loaded.connect(on_case_loaded)
    post_widget.field_changed.connect(on_field_changed)

    # OpenFOAM 케이스 파일 로드 예제 (파일 경로를 직접 지정하려면 주석 해제)
    # post_widget.load_foam(r"D:\path\to\case\case.foam")

    # 슬라이스 모드 활성화 예제
    # post_widget.enable_slice_mode(True)

    app.exec()
