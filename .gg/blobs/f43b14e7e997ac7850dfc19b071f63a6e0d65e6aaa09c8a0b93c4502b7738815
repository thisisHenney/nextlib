from pathlib import Path

import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
)


class FoamMeshViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("OpenFOAM 케이스 불러오기")
        self.btn_load.clicked.connect(self.open_case_folder)
        btn_layout.addWidget(self.btn_load)

        main_layout.addLayout(btn_layout)

        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.interactor.Initialize()

        self.axes_actor = vtkAxesActor()

        self.marker_widget = vtkOrientationMarkerWidget()
        self.marker_widget.SetOrientationMarker(self.axes_actor)
        self.marker_widget.SetInteractor(self.interactor)
        self.marker_widget.SetViewport(0.0, 0.0, 0.2, 0.2)

        self.marker_widget.EnabledOn()
        self.marker_widget.InteractiveOff()

        self.interactor.Render()

        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)   # Down
        self.renderer.GradientBackgroundOn()

    def open_case_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "OpenFOAM 케이스 폴더 선택")
        if folder:
            self.load_openfoam_case(Path(folder))

    def load_openfoam_case(self, case_dir: Path):
        foam_file = case_dir / "case.foam"
        if not foam_file.exists():
            foam_file.write_text("", encoding="utf-8")

        print(f"[INFO] Loading case: {case_dir}")

        reader = vtk.vtkOpenFOAMReader()
        reader.SetFileName(str(foam_file))

        if hasattr(reader, "SetCreateCellToPointOn"):
            reader.SetCreateCellToPointOn()
        elif hasattr(reader, "SetCreateCellToPoint"):
            reader.SetCreateCellToPoint(1)

        if hasattr(reader, "DecomposePolyhedraOn"):
            reader.DecomposePolyhedraOn()
        elif hasattr(reader, "SetDecomposePolyhedra"):
            reader.SetDecomposePolyhedra(1)

        reader.Update()

        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputConnection(reader.GetOutputPort())
        geom.Update()

        polydata = geom.GetOutput()
        print("[INFO] Surface points:", polydata.GetNumberOfPoints())
        print("[INFO] Bounds:", polydata.GetBounds())

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)
        mapper.ScalarVisibilityOff()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)

        prop = actor.GetProperty()
        prop.SetRepresentationToSurface()
        prop.EdgeVisibilityOn()          
        prop.SetColor(0.85, 0.85, 0.90)  
        prop.SetEdgeColor(0.10, 0.10, 0.40)
        prop.SetLineWidth(1.0)

        self.renderer.RemoveAllViewProps()
        self.renderer.AddActor(actor)

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()

        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.1, 0.1, 0.1)

        om = vtk.vtkOrientationMarkerWidget()
        om.SetOrientationMarker(axes)
        om.SetInteractor(self.vtk_widget.GetRenderWindow().GetInteractor())
        om.SetEnabled(True)
        om.InteractiveOn()

        self.vtk_widget.GetRenderWindow().Render()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    win = FoamMeshViewer()
    win.resize(1200, 800)
    win.show()

    sys.exit(app.exec())
