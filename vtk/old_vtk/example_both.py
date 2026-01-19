"""
전처리 및 후처리 위젯을 동시에 사용하는 예제
두 뷰어를 나란히 표시하고 카메라를 동기화
"""
from PySide6.QtWidgets import QApplication, QWidget, QHBoxLayout
from nextlib.vtk.preprocess_widget import PreprocessWidget
from nextlib.vtk.postprocess_widget import PostprocessWidget
from nextlib.vtk.vtk_manager import vtk_manager


class DualViewerWidget(QWidget):
    """전처리/후처리 듀얼 뷰어"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Dual Viewer - Preprocess & Postprocess")
        self.resize(1800, 900)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 전처리 위젯
        self.pre_widget = PreprocessWidget(registry=vtk_manager)
        vtk_manager.register("preprocess", self.pre_widget)
        layout.addWidget(self.pre_widget, stretch=1)

        # 후처리 위젯
        self.post_widget = PostprocessWidget(registry=vtk_manager)
        vtk_manager.register("postprocess", self.post_widget)
        layout.addWidget(self.post_widget, stretch=1)

        # 카메라 동기화 (선택사항)
        # self.sync_cameras()

    def sync_cameras(self):
        """두 뷰어의 카메라를 동기화"""
        # 전처리 뷰어를 마스터로 설정
        vtk_manager.sync_cameras("preprocess", ["postprocess"])


if __name__ == "__main__":
    app = QApplication([])

    viewer = DualViewerWidget()
    viewer.show()

    # 전처리 뷰어에 큐브 추가 (테스트용)
    viewer.pre_widget.add_geometry("cube")
    viewer.pre_widget.fit_to_scene()

    app.exec()
