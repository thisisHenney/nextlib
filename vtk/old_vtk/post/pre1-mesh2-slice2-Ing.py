from pathlib import Path
import math

import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkInteractionWidgets import vtkOrientationMarkerWidget
from vtkmodules.vtkRenderingAnnotation import vtkAxesActor
from vtkmodules.vtkCommonCore import vtkOutputWindow

from vtkmodules.vtkFiltersCore import vtkPlaneCutter
from vtkmodules.vtkFiltersGeometry import vtkCompositeDataGeometryFilter
from vtkmodules.vtkFiltersCore import vtkCleanPolyData
from vtkmodules.vtkFiltersCore import vtkPolyDataNormals

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QComboBox,
    QSlider,
    QCheckBox,
    QDoubleSpinBox,
)


class FoamMeshViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        # ------------------------------------------------------------------
        # 1) 상단: 케이스 불러오기 버튼
        # ------------------------------------------------------------------
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("OpenFOAM 케이스 불러오기")
        self.btn_load.clicked.connect(self.open_case_folder)
        btn_layout.addWidget(self.btn_load)
        main_layout.addLayout(btn_layout)

        # ------------------------------------------------------------------
        # 2) 슬라이스 방향 선택 (X, Y, Z, Custom)
        # ------------------------------------------------------------------
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("슬라이스 방향:"))

        self.combo_dir = QComboBox()
        self.combo_dir.addItems(["X", "Y", "Z", "Custom"])
        dir_layout.addWidget(self.combo_dir)

        dir_layout.addWidget(QLabel("n = ("))
        self.spin_nx = QDoubleSpinBox()
        self.spin_nx.setRange(-1.0, 1.0)
        self.spin_nx.setSingleStep(0.1)
        self.spin_nx.setValue(0.0)
        dir_layout.addWidget(self.spin_nx)

        dir_layout.addWidget(QLabel(","))
        self.spin_ny = QDoubleSpinBox()
        self.spin_ny.setRange(-1.0, 1.0)
        self.spin_ny.setSingleStep(0.1)
        self.spin_ny.setValue(0.0)
        dir_layout.addWidget(self.spin_ny)

        dir_layout.addWidget(QLabel(","))
        self.spin_nz = QDoubleSpinBox()
        self.spin_nz.setRange(-1.0, 1.0)
        self.spin_nz.setSingleStep(0.1)
        self.spin_nz.setValue(1.0)
        dir_layout.addWidget(self.spin_nz)
        dir_layout.addWidget(QLabel(")"))

        main_layout.addLayout(dir_layout)

        # ------------------------------------------------------------------
        # 3) 슬라이스 위치 슬라이더 (0~100%)
        # ------------------------------------------------------------------
        slider_layout = QHBoxLayout()
        slider_layout.addWidget(QLabel("슬라이스 위치:"))

        self.slider_pos = QSlider(Qt.Horizontal)
        self.slider_pos.setRange(0, 100)
        self.slider_pos.setValue(50)
        slider_layout.addWidget(self.slider_pos)

        self.lbl_pos_value = QLabel("50%")
        slider_layout.addWidget(self.lbl_pos_value)

        main_layout.addLayout(slider_layout)

        # ------------------------------------------------------------------
        # 4) Slice + Clip 조합 체크박스
        # ------------------------------------------------------------------
        self.chk_clip = QCheckBox("Slice + Clip (외곽 일부 제거)")
        self.chk_clip.setChecked(False)
        main_layout.addWidget(self.chk_clip)

        # ------------------------------------------------------------------
        # 5) VTK 위젯
        # ------------------------------------------------------------------
        # 경고 메세지 없애기
        vtk.vtkObject.GlobalWarningDisplayOff()
        vtkOutputWindow.SetGlobalWarningDisplay(0)

        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.interactor.Initialize()
        
        # 파라뷰와 동일한 마우스 조작
        style = vtk.vtkInteractorStyleTrackballCamera()
        self.interactor.SetInteractorStyle(style)

        # Orientation 위젯
        self.axes_actor = vtkAxesActor()
        self.marker_widget = vtkOrientationMarkerWidget()
        self.marker_widget.SetOrientationMarker(self.axes_actor)
        self.marker_widget.SetInteractor(self.interactor)
        self.marker_widget.SetViewport(0.0, 0.0, 0.2, 0.2)
        self.marker_widget.EnabledOn()
        self.marker_widget.InteractiveOff()

        # 배경 색상
        self.renderer.SetBackground2(0.40, 0.40, 0.50)
        self.renderer.SetBackground(0.65, 0.65, 0.70)
        self.renderer.GradientBackgroundOn()

        self.interactor.Render()

        # ------------------------------------------------------------------
        # VTK 파이프라인 상태 변수
        # ------------------------------------------------------------------
        self.foam_reader: vtk.vtkOpenFOAMReader | None = None
        self.geom_output: vtk.vtkPolyData | None = None  # 전체 surface polydata
        self.bounds = None      # (xmin, xmax, ymin, ymax, zmin, zmax)
        self.center = None      # (cx, cy, cz)
        self.diagonal_length = None

        self.surface_actor: vtk.vtkActor | None = None

        # 슬라이스 / 클립 파이프라인
        self.slice_plane: vtk.vtkPlane | None = None

        self.slice_cutter: vtk.vtkCutter | None = None
        self.slice_geom: vtk.vtkCompositeDataGeometryFilter | None = None
        self.slice_mapper: vtk.vtkPolyDataMapper | None = None
        self.slice_actor: vtk.vtkActor | None = None

        self.clip_filter: vtk.vtkClipDataSet | None = None
        self.clip_geom: vtk.vtkCompositeDataGeometryFilter | None = None
        self.clip_mapper: vtk.vtkPolyDataMapper | None = None
        self.clip_actor: vtk.vtkActor | None = None

        # ------------------------------------------------------------------
        # 시그널 연결 (케이스 로드 이후에도 항상 동작)
        # ------------------------------------------------------------------
        self.combo_dir.currentIndexChanged.connect(self.update_slice)
        self.slider_pos.valueChanged.connect(self.on_slider_changed)
        self.chk_clip.toggled.connect(self.update_slice)
        self.spin_nx.valueChanged.connect(self.update_slice)
        self.spin_ny.valueChanged.connect(self.update_slice)
        self.spin_nz.valueChanged.connect(self.update_slice)

    # ======================================================================
    # 케이스 로드 관련
    # ======================================================================
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
        self.foam_reader = reader

        # 기존 actor 및 slice/clip 파이프라인 초기화
        self._clear_slice_clip()

        # ------------------------------------------------------------------
        # 외곽 surface 생성 (MultiBlock → PolyData)
        # ------------------------------------------------------------------
        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputConnection(reader.GetOutputPort())
        geom.Update()

        polydata = geom.GetOutput()
        self.geom_output = polydata

        # bounds / center / 대각선 길이 계산
        b = polydata.GetBounds()
        self.bounds = b
        cx = 0.5 * (b[0] + b[1])
        cy = 0.5 * (b[2] + b[3])
        cz = 0.5 * (b[4] + b[5])
        self.center = (cx, cy, cz)
        dx = b[1] - b[0]
        dy = b[3] - b[2]
        dz = b[5] - b[4]
        self.diagonal_length = math.sqrt(dx * dx + dy * dy + dz * dz)

        print("[INFO] Surface points:", polydata.GetNumberOfPoints())
        print("[INFO] Bounds:", b)

        # surface actor 생성
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
        self.surface_actor = actor

        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()

        # Orientation marker (케이스 로드마다 새로)
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.1, 0.1, 0.1)
        om = vtk.vtkOrientationMarkerWidget()
        om.SetOrientationMarker(axes)
        om.SetInteractor(self.vtk_widget.GetRenderWindow().GetInteractor())
        om.SetEnabled(True)
        om.InteractiveOn()

        self.vtk_widget.GetRenderWindow().Render()

        # 케이스 로드 후, 현재 슬라이더/방향 기준으로 슬라이스 한 번 갱신
        self.update_slice()

    # ======================================================================
    # 슬라이스 / 클립 파이프라인 초기화
    # ======================================================================
    def _clear_slice_clip(self):
        # renderer에서 제거
        if self.slice_actor is not None:
            self.renderer.RemoveActor(self.slice_actor)
        if self.clip_actor is not None:
            self.renderer.RemoveActor(self.clip_actor)

        # 참조 초기화
        self.slice_plane = None
        self.slice_cutter = None
        self.slice_geom = None
        self.slice_mapper = None
        self.slice_actor = None

        self.clip_filter = None
        self.clip_geom = None
        self.clip_mapper = None
        self.clip_actor = None

    # ======================================================================
    # 슬라이스 방향/위치 계산
    # ======================================================================
    def _get_plane_params(self):
        """현재 UI 상태에서 슬라이스 평면의 origin, normal을 계산."""
        if self.bounds is None or self.center is None:
            return None, None

        xmin, xmax, ymin, ymax, zmin, zmax = self.bounds
        cx, cy, cz = self.center

        t = self.slider_pos.value() / 100.0  # 0.0 ~ 1.0

        dir_text = self.combo_dir.currentText()

        # 기본 normal, origin
        if dir_text == "X":
            normal = (1.0, 0.0, 0.0)
            x = xmin + t * (xmax - xmin)
            origin = (x, cy, cz)

        elif dir_text == "Y":
            normal = (0.0, 1.0, 0.0)
            y = ymin + t * (ymax - ymin)
            origin = (cx, y, cz)

        elif dir_text == "Z":
            normal = (0.0, 0.0, 1.0)
            z = zmin + t * (zmax - zmin)
            origin = (cx, cy, z)

        else:  # Custom
            nx = self.spin_nx.value()
            ny = self.spin_ny.value()
            nz = self.spin_nz.value()
            length = math.sqrt(nx * nx + ny * ny + nz * nz)
            if length < 1e-6:
                # 너무 작은 경우 기본 Z-normal
                nx, ny, nz = 0.0, 0.0, 1.0
                length = 1.0
            normal = (nx / length, ny / length, nz / length)

            # 중심을 기준으로 대각선 길이만큼 슬라이더에 따라 이동
            if self.diagonal_length is None:
                d = 1.0
            else:
                d = self.diagonal_length

            # t: 0~1 → -0.5 ~ +0.5
            s = (t - 0.5) * d
            ox = cx + s * normal[0]
            oy = cy + s * normal[1]
            oz = cz + s * normal[2]
            origin = (ox, oy, oz)

        return origin, normal

    # ======================================================================
    # 슬라이더 값 변경 시
    # ======================================================================
    def on_slider_changed(self, value: int):
        self.lbl_pos_value.setText(f"{value}%")
        self.update_slice()

    # ======================================================================
    # 슬라이스 / 클립 갱신
    # ======================================================================
    def update_slice(self):
        """Slice + Clip + ParaView-style pipeline + 삼각형(대각선) 방향 반전 포함"""
        if self.foam_reader is None or self.geom_output is None:
            return

        # --------------------------------------------------------
        # 1) Slice Plane 계산
        # --------------------------------------------------------
        origin, normal = self._get_plane_params()
        if origin is None or normal is None:
            return

        if self.slice_plane is None:
            self.slice_plane = vtk.vtkPlane()

        self.slice_plane.SetOrigin(*origin)
        self.slice_plane.SetNormal(*normal)

        # 기존 슬라이스 actor 제거
        if self.slice_actor is not None:
            self.renderer.RemoveActor(self.slice_actor)
            self.slice_actor = None

        # Clip OFF 시 surface actor 다시 표시
        if not self.chk_clip.isChecked() and self.surface_actor is not None:
            self.surface_actor.SetVisibility(True)

        # =====================================================================
        # 2) ParaView-style Slice Pipeline (Triangulation + Clean 등)
        # =====================================================================

        # Step 1: MultiBlock → PolyData
        geom_all = vtk.vtkCompositeDataGeometryFilter()
        geom_all.SetInputConnection(self.foam_reader.GetOutputPort())

        # Step 2: CellData → PointData
        cd2pd = vtk.vtkCellDataToPointData()
        cd2pd.SetInputConnection(geom_all.GetOutputPort())

        # Step 3: Clean
        clean1 = vtk.vtkCleanPolyData()
        clean1.SetInputConnection(cd2pd.GetOutputPort())

        # Step 4: Slice (Cutter)
        cutter = vtk.vtkCutter()
        cutter.SetInputConnection(clean1.GetOutputPort())
        cutter.SetCutFunction(self.slice_plane)

        # Step 5: Clean slice output
        clean2 = vtk.vtkCleanPolyData()
        clean2.SetInputConnection(cutter.GetOutputPort())

        # Step 6: Triangulate
        tri = vtk.vtkTriangleFilter()
        tri.SetInputConnection(clean2.GetOutputPort())

        # Step 7: Clean again
        clean3 = vtk.vtkCleanPolyData()
        clean3.SetInputConnection(tri.GetOutputPort())

        # --------------------------------------------------------
        # ★ Step 8: Triangulation orientation(대각선 방향) 반전
        #    - 이것이 ParaView와 패턴 차이를 줄이는 핵심
        # --------------------------------------------------------
        rev = vtk.vtkReverseSense()
        rev.SetInputConnection(clean3.GetOutputPort())

        rev.ReverseCellsOn()  # ★ 삼각형 방향 뒤집기 → 대각선 패턴 반전
        rev.ReverseNormalsOff()  # 노멀은 뒤집지 않음 (면 색 반전 방지)

        # =====================================================================
        # Mapper + Actor
        # =====================================================================
        slice_mapper = vtk.vtkPolyDataMapper()
        slice_mapper.SetInputConnection(rev.GetOutputPort())
        slice_mapper.ScalarVisibilityOff()

        slice_actor = vtk.vtkActor()
        slice_actor.SetMapper(slice_mapper)

        # ParaView-style 단면 색
        p = slice_actor.GetProperty()
        p.SetColor(1.0, 1.0, 0.0)  # 노란 슬라이스
        p.SetLineWidth(2.0)
        p.EdgeVisibilityOn()
        p.SetEdgeColor(0.0, 0.0, 0.0)

        p.SetAmbient(0.2)
        p.SetDiffuse(0.8)
        p.SetSpecular(0.1)
        p.SetSpecularPower(10)

        self.slice_actor = slice_actor
        self.renderer.AddActor(slice_actor)

        # =====================================================================
        # 3) Clip 조합 (옵션)
        # =====================================================================
        if self.chk_clip.isChecked():
            if self.clip_actor is not None:
                self.renderer.RemoveActor(self.clip_actor)

            if self.surface_actor is not None:
                self.surface_actor.SetVisibility(False)

            clip_filter = vtk.vtkClipDataSet()
            clip_filter.SetInputConnection(self.foam_reader.GetOutputPort())
            clip_filter.SetClipFunction(self.slice_plane)
            clip_filter.InsideOutOn()

            clip_geom = vtk.vtkCompositeDataGeometryFilter()
            clip_geom.SetInputConnection(clip_filter.GetOutputPort())

            # clean + triangulate
            cg_clean1 = vtk.vtkCleanPolyData()
            cg_clean1.SetInputConnection(clip_geom.GetOutputPort())

            cg_tri = vtk.vtkTriangleFilter()
            cg_tri.SetInputConnection(cg_clean1.GetOutputPort())

            cg_clean2 = vtk.vtkCleanPolyData()
            cg_clean2.SetInputConnection(cg_tri.GetOutputPort())

            # ★ Clip geometry 도 삼각형 방향 반전 적용
            clip_rev = vtk.vtkReverseSense()
            clip_rev.SetInputConnection(cg_clean2.GetOutputPort())
            clip_rev.ReverseCellsOn()
            clip_rev.ReverseNormalsOff()

            clip_mapper = vtk.vtkPolyDataMapper()
            clip_mapper.SetInputConnection(clip_rev.GetOutputPort())
            clip_mapper.ScalarVisibilityOff()

            clip_actor = vtk.vtkActor()
            clip_actor.SetMapper(clip_mapper)

            cp = clip_actor.GetProperty()
            cp.SetColor(0.8, 0.8, 0.9)
            cp.EdgeVisibilityOn()
            cp.SetEdgeColor(0.1, 0.1, 0.1)
            cp.SetLineWidth(1.0)

            self.clip_actor = clip_actor
            self.renderer.AddActor(clip_actor)

        else:
            if self.clip_actor is not None:
                self.renderer.RemoveActor(self.clip_actor)
                self.clip_actor = None
            if self.surface_actor is not None:
                self.surface_actor.SetVisibility(True)

        # --------------------------------------------------------
        # Render
        # --------------------------------------------------------
        self.vtk_widget.GetRenderWindow().Render()


# ------------------------------------------------------------------------------
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    win = FoamMeshViewer()
    win.resize(1200, 800)
    win.show()

    sys.exit(app.exec())
