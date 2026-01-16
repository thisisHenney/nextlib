import sys
from pathlib import Path
import vtk

from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkAppendFilter, vtkCutter
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFileDialog, QLabel, QComboBox, QSlider
)
from PySide6.QtCore import Qt


class FoamSliceViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.reader = None
        self.field_names: list[str] = []
        self.slice_z: float = 0.0
        self.zmin: float = 0.0
        self.zmax: float = 1.0

        self.time_dir: Path | None = None
        self.lagrangian_poly: vtk.vtkPolyData | None = None

        self.setWindowTitle("OpenFOAM Slice + Lagrangian d Viewer")
        self.resize(1100, 700)

        main_layout = QVBoxLayout(self)

        # --- VTK Widget ---
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()

        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)  # Down
        self.renderer.GradientBackgroundOn()

        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()

        # --- Control UI ---
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

    # ---------------------------------------------------------
    def load_foam(self):
        foam_file, _ = QFileDialog.getOpenFileName(
            self, "Select .foam", "", "OpenFOAM Case (*.foam)"
        )
        if not foam_file:
            return

        foam_path = Path(foam_file)
        print("Loading:", foam_path)

        reader = vtk.vtkOpenFOAMReader()
        reader.SetFileName(str(foam_path))
        reader.EnableAllCellArrays()
        reader.EnableAllPointArrays()
        reader.Update()

        # 마지막 타임스텝 사용
        ts_vtk = reader.GetTimeValues()
        target_time = None
        if ts_vtk and ts_vtk.GetNumberOfValues() > 0:
            timesteps = [ts_vtk.GetValue(i) for i in range(ts_vtk.GetNumberOfValues())]
            target_time = timesteps[-1]
            reader.UpdateTimeStep(target_time)
            reader.Update()
            print("Use time:", target_time)
        else:
            print("No timesteps, using default state")

        self.reader = reader

        # 필드 목록 추출
        self.field_names = self.extract_fields()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        # time 디렉토리 추정 (마지막 타임과 가장 가까운 숫자 이름 폴더)
        self.time_dir = self.find_time_directory(foam_path.parent, target_time)
        print("time_dir:", self.time_dir)

        # z 범위 계산
        self.compute_z_bounds()

        # 기본 슬라이스 위치: z = 0.0
        self.slice_z = 0.0
        # z 범위 밖이면 클램프
        if self.slice_z < self.zmin:
            self.slice_z = self.zmin
        if self.slice_z > self.zmax:
            self.slice_z = self.zmax

        self.z_label.setText(f"{self.slice_z:.4f}")
        ratio = (self.slice_z - self.zmin) / (self.zmax - self.zmin or 1.0)
        slider_val = int(max(0.0, min(1.0, ratio)) * 1000)

        self.z_slider.blockSignals(True)
        self.z_slider.setValue(slider_val)
        self.z_slider.blockSignals(False)

        if self.field_names:
            self.update_slice_view()
            self.renderer.ResetCamera()
            
        # Lagrangian cloud (positions + d) 한 번만 구성
        # self.lagrangian_poly = self.build_lagrangian_poly()



    # ---------------------------------------------------------
    def extract_fields(self) -> list[str]:
        """MultiBlock 전체에서 Point/Cell array 이름 추출"""
        if self.reader is None:
            return []

        mb = self.reader.GetOutput()
        if mb is None:
            return []

        it = mb.NewIterator()
        it.UnRegister(None)

        fields: set[str] = set()
        print("Extracting fields from multiblock...")

        while not it.IsDoneWithTraversal():
            obj = it.GetCurrentDataObject()
            if isinstance(obj, vtkDataSet):
                pd = obj.GetPointData()
                cd = obj.GetCellData()
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

    # ---------------------------------------------------------
    def find_time_directory(self, root: Path, target_time: float | None) -> Path | None:
        """foam 파일이 있는 폴더(root) 아래에서 타임 디렉토리 추정"""
        candidates: list[tuple[float, Path]] = []
        for p in root.iterdir():
            if not p.is_dir():
                continue
            name = p.name
            if name in ("constant", "system"):
                continue
            try:
                t = float(name)
                candidates.append((t, p))
            except ValueError:
                continue

        if not candidates:
            return None

        if target_time is None:
            # 가장 큰 시간 사용
            return max(candidates, key=lambda x: x[0])[1]

        # target_time 과 가장 가까운 폴더 선택
        best = min(candidates, key=lambda x: abs(x[0] - target_time))
        return best[1]

    # ---------------------------------------------------------
    def compute_z_bounds(self):
        """MultiBlock 전체 bounds 로 z min/max 계산"""
        if self.reader is None:
            return

        mb = self.reader.GetOutput()
        it = mb.NewIterator()
        it.UnRegister(None)

        zmins = []
        zmaxs = []

        while not it.IsDoneWithTraversal():
            obj = it.GetCurrentDataObject()
            if isinstance(obj, vtkDataSet):
                b = [0.0] * 6
                obj.GetBounds(b)
                zmins.append(b[4])
                zmaxs.append(b[5])
            it.GoToNextItem()

        if zmins and zmaxs:
            self.zmin = min(zmins)
            self.zmax = max(zmaxs)
        else:
            self.zmin, self.zmax = 0.0, 1.0

        print("Global Z-range:", self.zmin, self.zmax)

    # ---------------------------------------------------------
    def slider_changed(self, value: int):
        if self.zmax == self.zmin:
            return
        ratio = value / 1000.0
        self.slice_z = self.zmin + (self.zmax - self.zmin) * ratio
        self.z_label.setText(f"{self.slice_z:.4f}")
        self.update_slice_view()

    # ---------------------------------------------------------
    def build_field_dataset(self, field: str) -> vtk.vtkDataSet | None:
        """선택한 필드를 가진 DataSet 만 Append 해서 하나의 DataSet 으로 생성"""
        if self.reader is None:
            return None

        mb = self.reader.GetOutput()
        if mb is None:
            return None

        append = vtkAppendFilter()
        append.MergePointsOn()

        it = mb.NewIterator()
        it.UnRegister(None)

        count = 0
        while not it.IsDoneWithTraversal():
            obj = it.GetCurrentDataObject()
            if isinstance(obj, vtkDataSet):
                pd = obj.GetPointData()
                cd = obj.GetCellData()
                if pd.HasArray(field) or cd.HasArray(field):
                    append.AddInputData(obj)
                    count += 1
            it.GoToNextItem()

        if count == 0:
            print(f"No dataset contains field '{field}'.")
            return None

        append.Update()
        ug = append.GetOutput()
        if ug is None or ug.GetNumberOfPoints() == 0:
            print("Unified grid empty for field:", field)
            return None

        return ug

    # ---------------------------------------------------------
    def update_slice_view(self):
        if self.reader is None:
            return

        field = self.field_combo.currentText()
        if not field:
            return

        ug = self.build_field_dataset(field)
        if ug is None:
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # --- z-normal slice ---
        plane = vtk.vtkPlane()
        plane.SetNormal(0, 0, 1)
        plane.SetOrigin(0, 0, self.slice_z)

        cutter = vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputData(ug)
        cutter.Update()

        poly = cutter.GetOutput()
        if poly is None or poly.GetNumberOfPoints() == 0:
            print("Empty slice")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

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
            print(f"Field '{field}' not found in slice output.")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        data_min, data_max = arr.GetRange()

        # --- 렌더러 초기화 ---
        self.renderer.RemoveAllViewProps()

        # --- 메인 슬라이스 Mapper ---
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly)
        mapper.SetScalarVisibility(True)
        mapper.SelectColorArray(field)
        mapper.SetColorModeToMapScalars()
        if use_point:
            mapper.SetScalarModeToUsePointFieldData()
        else:
            mapper.SetScalarModeToUseCellFieldData()
        mapper.SetScalarRange(data_min, data_max)

        # ---- 베이지 톤 CoolWarm LUT (Blue → Beige → Red) ----
        anchors = [
            (0.231373, 0.298039, 0.752941),   # Blue (low)
            (0.960784, 0.900000, 0.835294),   # Beige (mid)
            (0.705882, 0.0156863, 0.14902),   # Red (high)
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

        slice_actor = vtk.vtkActor()
        slice_actor.SetMapper(mapper)
        self.renderer.AddActor(slice_actor)

        # --- lagrangian d 오버레이 ---
        self.add_lagrangian_overlay(lut)

        self.vtk_widget.GetRenderWindow().Render()

    # ---------------------------------------------------------
    def build_lagrangian_poly(self) -> vtk.vtkPolyData | None:
        """
        Build lagrangian polydata from user-selected folder if available.
        Otherwise, try automatic detection under:
            <time>/fluid/lagrangian
            <time>/lagrangian
        """
        # -------------------------------
        # 1) 사용자 직접 선택 폴더가 최우선
        # -------------------------------
        if self.lag_root_manual is not None:
            lag_root = self.lag_root_manual
            print("Using user-selected lagrangian root:", lag_root)
        else:
            # -------------------------------
            # 2) 자동 탐색 fallback
            # -------------------------------
            if self.time_dir is None:
                print("No time directory. Cannot find lagrangian folder.")
                return None

            candidates = [
                self.time_dir / "fluid" / "lagrangian",
                self.time_dir / "lagrangian",
            ]

            lag_root = None
            for c in candidates:
                if c.exists():
                    lag_root = c
                    break

            if lag_root is None:
                print("No lagrangian folder found automatically.")
                return None

            print("Using auto-detected lagrangian root:", lag_root)

        # ---- Cloud 목록 제한 ----
        target_clouds = [
            "sprayMMHCloud",
            "sprayMMHCloudTracks",
            "sprayNTOCloud",
            "sprayNTOCloudTracks",
        ]

        # ---- Polydata 생성 ----
        points = vtk.vtkPoints()
        d_array = vtk.vtkDoubleArray()
        d_array.SetName("d")
        d_array.SetNumberOfComponents(1)

        total_points = 0

        for cloud in target_clouds:
            cloud_dir = lag_root / cloud
            if not cloud_dir.exists():
                continue

            pos_file = cloud_dir / "positions"
            d_file = cloud_dir / "d"

            if not pos_file.exists() or not d_file.exists():
                print("Missing files:", pos_file, d_file)
                continue

            print("Reading cloud:", cloud)

            pos_list = self.read_positions(pos_file)
            d_list = self.read_scalar_list(d_file)

            if len(pos_list) != len(d_list):
                print(f"Warning: mismatch in {cloud}: pos={len(pos_list)} d={len(d_list)}")
                n = min(len(pos_list), len(d_list))
                pos_list = pos_list[:n]
                d_list = d_list[:n]

            for (x, y, z), dv in zip(pos_list, d_list):
                points.InsertNextPoint(float(x), float(y), float(z))
                d_array.InsertNextValue(float(dv))
                total_points += 1

        if total_points == 0:
            print("No lagrangian points found.")
            return None

        poly = vtk.vtkPolyData()
        poly.SetPoints(points)
        poly.GetPointData().AddArray(d_array)
        poly.GetPointData().SetActiveScalars("d")

        print("Total lagrangian points:", total_points)
        return poly

    # ---------------------------------------------------------
    def read_positions(self, path: Path) -> list[tuple[float, float, float]]:
        """
        Read ASCII OpenFOAM vectorField:
            N
            (
            (x y z)
            (x y z)
            ...
            )
        Fully supports the format used in spray*Cloud positions files.
        """
        positions = []
        reading = False

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue

                # Skip header lines including FoamFile, braces, class, etc.
                if s.startswith("FoamFile") or s.startswith("//") or s.startswith("/*"):
                    continue
                if s.startswith("version") or s.startswith("format") or s.startswith("class"):
                    continue
                if s.startswith("location") or s.startswith("object"):
                    continue

                # Open parenthesis for vector list
                if s == "(":
                    reading = True
                    continue
                # End parenthesis
                if s == ")" or s == ");":
                    reading = False
                    continue

                if not reading:
                    continue

                # Now expecting (x y z)
                if s.startswith("(") and s.endswith(")"):
                    inside = s[1:-1].strip()
                    parts = inside.split()
                    if len(parts) >= 3:
                        try:
                            x, y, z = map(float, parts[:3])
                            positions.append((x, y, z))
                        except ValueError:
                            pass

        return positions

    # ---------------------------------------------------------
    def read_scalar_list(self, path: Path) -> list[float]:
        """OpenFOAM scalar field 파일에서 괄호 안의 값들만 추출"""
        values: list[float] = []
        reading = False

        with open(path, "r") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("//"):
                    continue

                if s == "(":
                    reading = True
                    continue
                if s == ");" or s == ")":
                    reading = False
                    continue

                if not reading:
                    continue

                # 괄호 안의 숫자들
                # 예: "1.23" 또는 "1.23 4.56"
                parts = s.split()
                for tok in parts:
                    try:
                        v = float(tok)
                        values.append(v)
                    except ValueError:
                        pass

        return values

    # ---------------------------------------------------------
    def add_lagrangian_overlay(self, lut: vtk.vtkLookupTable):
        """이미 만들어둔 lagrangian_poly 를 d 값으로 컬러맵해서 오버레이"""
        if self.lagrangian_poly is None:
            return
        if self.lagrangian_poly.GetNumberOfPoints() == 0:
            return

        darr = self.lagrangian_poly.GetPointData().GetArray("d")
        if darr is None:
            return

        d_min, d_max = darr.GetRange()

        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(self.lagrangian_poly)
        mapper.SetScalarVisibility(True)
        mapper.SelectColorArray("d")
        mapper.SetScalarModeToUsePointFieldData()
        mapper.SetScalarRange(d_min, d_max)
        mapper.SetLookupTable(lut)  # 메인 슬라이스와 같은 LUT 사용

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetPointSize(5.0)

        self.renderer.AddActor(actor)


# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    viewer = FoamSliceViewer()
    viewer.show()

    sys.exit(app.exec())
