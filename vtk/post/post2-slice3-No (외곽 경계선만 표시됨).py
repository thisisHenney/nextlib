import sys
from pathlib import Path
import vtk

from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import (
    vtkAppendFilter, vtkCutter, vtkTriangleFilter, vtkPolyDataNormals, vtkPlaneCutter
)
from vtkmodules.vtkCommonDataModel import vtkPlane
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QComboBox, QSlider
)
from PySide6.QtCore import Qt


class FoamSliceViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.reader = None
        self.field_names = []
        self.slice_z = 0.0
        self.zmin = 0.0
        self.zmax = 1.0

        self.setWindowTitle("Slice Viewer")
        self.resize(1000, 700)

        main_layout = QVBoxLayout(self)

        # --- VTK Viewer ---
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
                
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)  # Down
        self.renderer.GradientBackgroundOn()
        
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()

        # --- Controls ---
        ctrl_layout = QHBoxLayout()
        main_layout.addLayout(ctrl_layout)

        self.load_btn = QPushButton("Load .foam")
        self.load_btn.clicked.connect(self.load_foam)
        ctrl_layout.addWidget(self.load_btn)

        ctrl_layout.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.currentIndexChanged.connect(self.update_slice_view)
        ctrl_layout.addWidget(self.field_combo)

        ctrl_layout.addWidget(QLabel("Slice Z:"))
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(0, 1000)
        self.z_slider.valueChanged.connect(self.slider_changed)
        ctrl_layout.addWidget(self.z_slider)

        self.z_label = QLabel("0.0")
        ctrl_layout.addWidget(self.z_label)

    def load_foam(self):
        foam_file, _ = QFileDialog.getOpenFileName(
            self, "Select .foam", "", "OpenFOAM Case (*.foam)"
        )
        if not foam_file:
            return

        print("Loading:", foam_file)

        reader = vtk.vtkOpenFOAMReader()
        reader.SetFileName(foam_file)
        reader.EnableAllCellArrays()
        reader.EnableAllPointArrays()
        reader.Update()

        ts_vtk = reader.GetTimeValues()
        if ts_vtk and ts_vtk.GetNumberOfValues() > 0:
            timesteps = [ts_vtk.GetValue(i) for i in range(ts_vtk.GetNumberOfValues())]
            reader.UpdateTimeStep(timesteps[-1])
            reader.Update()
            print("Use time:", timesteps[-1])

        self.reader = reader

        # field names
        self.field_names = self.extract_fields()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        # z-range (from entire dataset bounds)
        self.compute_z_bounds()

        # --- slice_z를 0.0으로 초기 설정 ---
        self.slice_z = 0.0
        self.z_label.setText(f"{self.slice_z:.4f}")

        # 슬라이더도 1.0에 맞게 이동 (0~1000 범위)
        ratio = (self.slice_z - self.zmin) / (self.zmax - self.zmin)
        slider_val = int(ratio * 1000)

        self.z_slider.blockSignals(True)
        self.z_slider.setValue(slider_val)
        self.z_slider.blockSignals(False)

        if self.field_names:
            self.update_slice_view()

    def extract_fields(self):
        mb = self.reader.GetOutput()
        if mb is None:
            return []

        it = mb.NewIterator()
        it.UnRegister(None)

        fields = set()

        print("Extracting fields...")

        while not it.IsDoneWithTraversal():
            ds = it.GetCurrentDataObject()
            if isinstance(ds, vtkDataSet):
                pd = ds.GetPointData()
                cd = ds.GetCellData()

                for i in range(pd.GetNumberOfArrays()):
                    name = pd.GetArrayName(i)
                    if name:
                        fields.add(name)

                for i in range(cd.GetNumberOfArrays()):
                    name = cd.GetArrayName(i)
                    if name:
                        fields.add(name)

            it.GoToNextItem()

        print("Detected fields:", fields)
        return sorted(fields)

    def compute_z_bounds(self):
        mb = self.reader.GetOutput()
        it = mb.NewIterator()
        it.UnRegister(None)

        zmins = []
        zmaxs = []

        while not it.IsDoneWithTraversal():
            ds = it.GetCurrentDataObject()
            if isinstance(ds, vtkDataSet):
                b = [0.0] * 6
                ds.GetBounds(b)
                zmins.append(b[4])
                zmaxs.append(b[5])
            it.GoToNextItem()

        self.zmin = min(zmins)
        self.zmax = max(zmaxs)

        print("Z-range =", self.zmin, self.zmax)

    def slider_changed(self, v):
        ratio = v / 1000
        self.slice_z = self.zmin + (self.zmax - self.zmin) * ratio
        self.z_label.setText(f"{self.slice_z:.4f}")
        self.update_slice_view()

    def build_field_dataset(self, field):
        mb = self.reader.GetOutput()

        append = vtkAppendFilter()
        append.MergePointsOn()

        it = mb.NewIterator()
        it.UnRegister(None)

        count = 0
        while not it.IsDoneWithTraversal():
            ds = it.GetCurrentDataObject()
            if isinstance(ds, vtkDataSet):
                pd = ds.GetPointData()
                cd = ds.GetCellData()
                if pd.HasArray(field) or cd.HasArray(field):
                    append.AddInputData(ds)
                    count += 1
            it.GoToNextItem()

        if count == 0:
            print(f"No dataset contains field '{field}'")
            return None

        append.Update()
        ug = append.GetOutput()

        if ug is None or ug.GetNumberOfPoints() == 0:
            print("Unified grid empty for field:", field)
            return None

        return ug


    def set_color(self, mapper):
        anchors = [
            (0.231373, 0.298039, 0.752941),    # Blue (low)
            (0.960784, 0.900000, 0.835294),    # Beige (mid)
            (0.705882, 0.0156863, 0.14902),    # Red (high)
        ]

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(data_min, data_max)

        for i in range(256):
            t = i / 255.0

            if t <= 0.5:
                s = t / 0.5
                r = anchors[0][0] + (anchors[1][0] - anchors[0][0]) * s
                g = anchors[0][1] + (anchors[1][1] - anchors[0][1]) * s
                b = anchors[0][2] + (anchors[1][2] - anchors[0][2]) * s
            else:
                s = (t - 0.5) / 0.5
                r = anchors[1][0] + (anchors[2][0] - anchors[1][0]) * s
                g = anchors[1][1] + (anchors[2][1] - anchors[1][1]) * s
                b = anchors[1][2] + (anchors[2][2] - anchors[1][2]) * s

            lut.SetTableValue(i, r, g, b, 1.0)

        lut.Build()
        mapper.SetLookupTable(lut)

    def update_slice_view(self):
        if self.reader is None:
            return

        field = self.field_combo.currentText()
        if not field:
            return

        # 1) Unified Grid 생성
        ug = self.build_field_dataset(field)
        if ug is None:
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # ----------------------------------------------------------
        #  Paraview-Style Slice Pipeline
        #  ug → Geometry → Triangles → PlaneCutter → Normals → poly
        # ----------------------------------------------------------

        # (1) Polyhedral mesh → surface polygon 추출
        gfilter = vtkGeometryFilter()
        gfilter.SetInputData(ug)
        gfilter.Update()

        # (2) 삼각화 (Paraview와 동일)
        tri = vtkTriangleFilter()
        tri.SetInputConnection(gfilter.GetOutputPort())
        tri.Update()

        # (3) Filled Slice 생성 (vtkPlaneCutter = Paraview Slice)
        plane = vtk.vtkPlane()
        plane.SetNormal(0, 0, 1)
        plane.SetOrigin(0, 0, self.slice_z)

        pc = vtkPlaneCutter()
        pc.SetPlane(plane)
        pc.SetInputConnection(tri.GetOutputPort())
        pc.Update()

        # (4) 노멀 생성 (부드럽게 만들기)
        normals = vtkPolyDataNormals()
        normals.SetInputConnection(pc.GetOutputPort())
        normals.AutoOrientNormalsOn()
        normals.SplittingOff()
        normals.ConsistencyOn()
        normals.Update()

        poly = normals.GetOutput()

        if poly is None or poly.GetNumberOfPoints() == 0:
            print("Empty slice")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # ----------------------------------------------------------
        #  Field scalar 찾기 (PointData 우선)
        # ----------------------------------------------------------
        pd = poly.GetPointData()
        cd = poly.GetCellData()

        use_point = False
        arr = None

        if pd.HasArray(field):
            arr = pd.GetArray(field)
            use_point = True
        elif cd.HasArray(field):
            arr = cd.GetArray(field)
            use_point = False
        else:
            print(f"Field '{field}' not found on slice.")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        data_min, data_max = arr.GetRange()

        # ----------------------------------------------------------
        #  렌더러 리셋
        # ----------------------------------------------------------
        self.renderer.RemoveAllViewProps()

        # ----------------------------------------------------------
        #  Paraview CoolWarm LUT (정확 버전)
        # ----------------------------------------------------------
        low = (0.231373, 0.298039, 0.752941)
        high = (0.705882, 0.0156863, 0.14902)

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(data_min, data_max)

        for i in range(256):
            t = i / 255.0
            r = low[0] + (high[0] - low[0]) * t
            g = low[1] + (high[1] - low[1]) * t
            b = low[2] + (high[2] - low[2]) * t
            lut.SetTableValue(i, r, g, b, 1.0)

        lut.Build()

        # ----------------------------------------------------------
        #  Mapper 설정
        # ----------------------------------------------------------
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly)
        mapper.SetScalarVisibility(True)
        mapper.SelectColorArray(field)
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(data_min, data_max)

        if use_point:
            mapper.SetScalarModeToUsePointFieldData()
        else:
            mapper.SetScalarModeToUseCellFieldData()

        # ----------------------------------------------------------
        #  Actor
        # ----------------------------------------------------------
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetInterpolationToPhong()  # Paraview와 동일

        self.renderer.AddActor(actor)

        # ----------------------------------------------------------
        #  Lagrangian d overlay (이미 구현되어 있다면 유지)
        # ----------------------------------------------------------
        # self.add_lagrangian_overlay(lut)

        # ----------------------------------------------------------
        #  Camera / Render
        # ----------------------------------------------------------
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    win = FoamSliceViewer()
    win.show()

    sys.exit(app.exec())

