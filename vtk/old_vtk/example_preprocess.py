"""
전처리 위젯 사용 예제
STL 파일을 로드하고 시각화하는 예제
"""
from PySide6.QtWidgets import QApplication
from nextlib.vtk.preprocess_widget import PreprocessWidget
from nextlib.vtk.vtk_manager import vtk_manager


if __name__ == "__main__":
    app = QApplication([])

    # 전처리 위젯 생성
    pre_widget = PreprocessWidget(registry=vtk_manager)
    vtk_manager.register("preprocess", pre_widget)

    # 윈도우 설정
    pre_widget.setWindowTitle("Preprocess Widget Example")
    pre_widget.resize(1200, 800)
    pre_widget.show()

    # 시그널 연결 예제
    def on_mesh_loaded(file_path: str):
        print(f"Mesh loaded: {file_path}")

    def on_selection_changed(info: dict):
        print(f"Selection changed: {info}")

    pre_widget.mesh_loaded.connect(on_mesh_loaded)
    pre_widget.selection_changed.connect(on_selection_changed)

    # 기본 큐브 추가 (테스트용)
    obj_id = pre_widget.add_geometry("cube")
    print(f"Added cube with ID: {obj_id}")

    # STL 파일 로드 예제 (파일 경로를 직접 지정하려면 주석 해제)
    # pre_widget.load_stl(r"D:\resources\stl\example.stl")

    app.exec()
