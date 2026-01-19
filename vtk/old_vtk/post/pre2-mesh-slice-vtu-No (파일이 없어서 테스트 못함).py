from pathlib import Path

import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog
)


class VtkSliceViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        # 상단 버튼
        row = QHBoxLayout()
        self.btn_load = QPushButton("VTK(.vtu) 파일 열기")
        self.btn_load.clicked.connect(self.open_vtu_file)
        row.addWidget(self.btn_load)
        main_layout.addLayout(row)

        # VTK 위젯
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.interactor.Initialize()

        # 배경 그라데이션
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)   # Down
        self.renderer.GradientBackgroundOn()

    # -------------------------------------------------
    def open_vtu_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "VTK(.vtu) 파일 선택",
            "",
            "VTK Unstructured (*.vtu);;All Files (*)",
        )
        if file_path:
            self.load_and_slice(Path(file_path))

    # -------------------------------------------------
    def load_and_slice(self, vtu_path: Path):
        print(f"[INFO] Loading VTK file: {vtu_path}")

        # 1) VTU 읽기 (foamToVTK 결과)
        reader = vtk.vtkXMLUnstructuredGridReader()
        reader.SetFileName(str(vtu_path))
        reader.Update()

        ugrid = reader.GetOutput()
        print("[INFO] cells:", ugrid.GetNumberOfCells())
        print("[INFO] bounds:", ugrid.GetBounds())

        if ugrid.GetNumberOfCells() == 0:
            print("[ERROR] UnstructuredGrid에 셀이 없습니다.")
            return

        # 2) 메쉬 중심 z 위치 계산
        xmin, xmax, ymin, ymax, zmin, zmax = ugrid.GetBounds()
        z_center = 0.5 * (zmin + zmax)
        print("[INFO] z-center:", z_center)

        # 3) 슬라이스 평면 (z = z_center, Z-normal)
        plane = vtk.vtkPlane()
        plane.SetOrigin(0.0, 0.0, z_center)
        plane.SetNormal(0.0, 0.0, 1.0)

        # 4) vtkCutter로 단면 생성 (실제 Volume mesh 단면)
        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputConnection(reader.GetOutputPort())
        cutter.Update()

        slice_poly = cutter.GetOutput()
        print("[INFO] slice points:", slice_poly.GetNumberOfPoints())

        if slice_poly.GetNumberOfPoints() == 0:
            print("[WARN] 이 z 위치에서 단면이 없습니다.")
            return

        # 5) 단면에서 edge만 추출 (격자선만 보기)
        edges = vtk.vtkExtractEdges()
        edges.SetInputData(slice_poly)
        edges.Update()

        edge_poly = edges.GetOutput()
        print("[INFO] edge lines:", edge_poly.GetNumberOfCells())

        # 6) Mapper / Actor 설정
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(edge_poly)
        mapper.ScalarVisibilityOff()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(0.0, 0.0, 1.0)   # 격자선 색
        prop.SetLineWidth(1.0)

        # 7) Renderer 갱신
        self.renderer.RemoveAllViewProps()
        self.renderer.AddActor(actor)

        # 8) 카메라 중앙 맞추기
        self._reset_camera(edge_poly)

        # 9) 축(Axes) 표시
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.1, 0.1, 0.1)
        om = vtk.vtkOrientationMarkerWidget()
        om.SetOrientationMarker(axes)
        om.SetInteractor(self.interactor)
        om.SetEnabled(True)
        om.InteractiveOn()

        self.vtk_widget.GetRenderWindow().Render()

    # -------------------------------------------------
    def _reset_camera(self, poly: vtk.vtkPolyData):
        bounds = poly.GetBounds()
        xmin, xmax, ymin, ymax, zmin, zmax = bounds

        cx = 0.5 * (xmin + xmax)
        cy = 0.5 * (ymin + ymax)
        cz = 0.5 * (zmin + zmax)

        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin
        dmax = max(dx, dy, dz, 1e-6)

        cam = self.renderer.GetActiveCamera()
        cam.SetFocalPoint(cx, cy, cz)
        cam.SetPosition(cx, cy, cz + dmax * 2.0)
        cam.SetViewUp(0, 1, 0)
        cam.ParallelProjectionOn()
        cam.SetParallelScale(dmax * 0.6)

        self.renderer.ResetCameraClippingRange()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = VtkSliceViewer()
    w.resize(1400, 800)
    w.show()
    sys.exit(app.exec())
