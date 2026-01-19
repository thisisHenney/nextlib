"""
후처리용 VTK 위젯
OpenFOAM 케이스 파일을 불러와 필드 데이터를 시각화하는 기능 제공
"""
from functools import partial
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolBar, QComboBox,
    QFileDialog, QLabel, QSlider
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Signal, Qt

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkDataSetMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkAppendFilter
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader
import vtk

from nextlib.vtk.camera.camera import Camera
from nextlib.vtk.tool.axes_tool import AxesTool


RES_DIR = Path(__file__).resolve().parent.parent
ICON_DIR = Path(RES_DIR / "vtk" / "res" / "icon")


class PostprocessWidget(QWidget):
    """
    후처리용 VTK 위젯
    - OpenFOAM 케이스 파일 로딩
    - 필드 데이터 시각화
    - 슬라이스 뷰
    - 스칼라 바 표시
    """

    case_loaded = Signal(str)  # 케이스 로드 완료 시그널
    field_changed = Signal(str)  # 필드 변경 시그널

    def __init__(self, parent=None, registry=None):
        super().__init__(parent)
        self.parent = parent
        self.registry = registry
        self.camera_sync_lock = False

        # OpenFOAM reader
        self.reader: vtkOpenFOAMReader | None = None
        self.field_names: list[str] = []

        # Slice control
        self.slice_enabled = False
        self.slice_z: float = 0.0
        self.zmin: float = 0.0
        self.zmax: float = 1.0

        # Scalar bar
        self.scalar_bar_actor = None
        self.scalar_bar_visible = False

        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._build_control_panel()

        self.set_widget_style()
        self.interactor.Initialize()

    def _setup_ui(self):
        """UI 레이아웃 설정"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = QToolBar("Postprocess Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        layout.addWidget(self.toolbar)

        self.vtk_widget = QVTKRenderWindowInteractor(self)
        layout.addWidget(self.vtk_widget, stretch=1)

    def _setup_vtk(self):
        """VTK 렌더러 및 인터랙터 설정"""
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()

    def _setup_tools(self):
        """VTK 도구 초기화"""
        self.camera = Camera(self)
        self.camera.init()

        self.colors = vtkNamedColors()
        self.axes = AxesTool(self)

    def _build_toolbar(self):
        """툴바 구성"""
        # 파일 로드
        self.add_toolbar_action("Load .foam", self.load_foam_file, None)
        self.toolbar.addSeparator()

        # Axes
        icon = self.make_icon("axes_on.png")
        self.axe_action = QAction(icon, "Axes On/Off", self)
        self.axe_action.setCheckable(True)
        self.axe_action.setChecked(True)
        self.axe_action.triggered.connect(self.on_axes_toggled)
        self.toolbar.addAction(self.axe_action)

        # Scalar Bar
        icon = self.make_icon("scalar_bar_off.png")
        self.scalar_bar_action = QAction(icon, "Scalar Bar On/Off", self)
        self.scalar_bar_action.setCheckable(True)
        self.scalar_bar_action.setChecked(False)
        self.scalar_bar_action.triggered.connect(self.on_scalar_bar_toggled)
        self.toolbar.addAction(self.scalar_bar_action)

        self.toolbar.addSeparator()

        # Camera Views
        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            act = QAction(self.make_icon(f"{name.lower()}.png"), name, self)
            act.triggered.connect(partial(self.camera.set_camera_view, name.lower()))
            self.toolbar.addAction(act)

        self.toolbar.addSeparator()

        # Fit
        self.add_toolbar_action("Fit", self.fit_to_scene, "fit.png")

        # Projection
        icon = self.make_icon("perspective.png")
        self.projection_action = QAction(icon, "Persp/Ortho", self)
        self.projection_action.setCheckable(True)
        self.projection_action.setChecked(False)
        self.projection_action.triggered.connect(self.on_projection_toggled)
        self.toolbar.addAction(self.projection_action)

    def _build_control_panel(self):
        """필드 선택 및 슬라이스 컨트롤 패널"""
        ctrl_layout = QHBoxLayout()

        # 필드 선택
        ctrl_layout.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        ctrl_layout.addWidget(self.field_combo)

        ctrl_layout.addStretch()

        # 슬라이스 Z 위치
        ctrl_layout.addWidget(QLabel("Slice Z:"))
        self.z_slider = QSlider(Qt.Horizontal)
        self.z_slider.setRange(0, 1000)
        self.z_slider.setMinimumWidth(200)
        self.z_slider.valueChanged.connect(self._on_slider_changed)
        self.z_slider.setEnabled(False)
        ctrl_layout.addWidget(self.z_slider)

        self.z_label = QLabel("0.0")
        self.z_label.setMinimumWidth(80)
        ctrl_layout.addWidget(self.z_label)

        # 메인 레이아웃에 추가
        self.layout().addLayout(ctrl_layout)

    def make_icon(self, name: str) -> QIcon:
        """아이콘 생성"""
        return QIcon(str(Path(ICON_DIR / name)))

    def add_toolbar_action(self, text, slot, icon_name=None):
        """툴바 액션 추가"""
        act = QAction(self.make_icon(icon_name) if icon_name else QIcon(), text, self)
        act.triggered.connect(partial(slot))
        self.toolbar.addAction(act)

    # ===== 파일 로딩 =====

    def load_foam_file(self):
        """OpenFOAM 케이스 파일 로드 다이얼로그"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select .foam File",
            "",
            "OpenFOAM Case (*.foam);;All Files (*.*)"
        )
        if file_path:
            self.load_foam(file_path)

    def load_foam(self, file_path: str | Path):
        """OpenFOAM 케이스 로드"""
        foam_path = Path(file_path)
        print(f"[INFO] Loading: {foam_path}")

        reader = vtkOpenFOAMReader()
        reader.SetFileName(str(foam_path))
        reader.EnableAllCellArrays()
        reader.EnableAllPointArrays()
        reader.Update()

        # 타임스텝 설정 (마지막 타임스텝 사용)
        ts_vtk = reader.GetTimeValues()
        if ts_vtk is not None and ts_vtk.GetNumberOfValues() > 0:
            timesteps = [ts_vtk.GetValue(i) for i in range(ts_vtk.GetNumberOfValues())]
            print(f"[INFO] Time steps: {timesteps}")
            last_t = timesteps[-1]
            reader.UpdateTimeStep(last_t)
            reader.Update()
            print(f"[INFO] Using time = {last_t}")
        else:
            print("[INFO] No time steps found, using default state.")

        self.reader = reader

        # 필드 목록 추출
        self.field_names = self._extract_fields()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        # Z 범위 계산
        self._compute_z_bounds()

        # 슬라이더 활성화
        self.z_slider.setEnabled(True)
        self.slice_z = (self.zmin + self.zmax) / 2.0
        self._update_slider_position()

        # 기본 필드 표시
        if self.field_names:
            self._display_field()

        self.case_loaded.emit(str(file_path))

    def _extract_fields(self) -> list[str]:
        """MultiBlock에서 필드 이름 추출"""
        if self.reader is None:
            return []

        mb = self.reader.GetOutput()
        if mb is None:
            return []

        it = mb.NewIterator()
        it.UnRegister(None)

        fields: set[str] = set()
        print("[INFO] Extracting fields from multiblock...")

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

        print(f"[INFO] Detected fields: {sorted(fields)}")
        return sorted(fields)

    def _compute_z_bounds(self):
        """전체 bounds에서 Z 범위 계산"""
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

        print(f"[INFO] Global Z-range: {self.zmin} to {self.zmax}")

    # ===== 필드 시각화 =====

    def _on_field_changed(self):
        """필드 선택 변경"""
        field = self.field_combo.currentText()
        if field:
            self.field_changed.emit(field)
            self._display_field()

    def _display_field(self):
        """선택된 필드 표시"""
        if self.reader is None:
            return

        field = self.field_combo.currentText()
        if not field:
            return

        print(f"[INFO] Displaying field: {field}")

        if self.slice_enabled:
            self._display_slice(field)
        else:
            self._display_volume(field)

    def _display_volume(self, field: str):
        """필드를 3D 볼륨으로 표시"""
        mb = self.reader.GetOutput()
        if mb is None:
            return

        # 해당 필드를 가진 블록만 병합
        append = vtkAppendFilter()
        append.MergePointsOn()

        it = mb.NewIterator()
        it.UnRegister(None)

        found_datasets = 0

        while not it.IsDoneWithTraversal():
            obj = it.GetCurrentDataObject()
            if isinstance(obj, vtkDataSet):
                pd = obj.GetPointData()
                cd = obj.GetCellData()
                if pd.HasArray(field) or cd.HasArray(field):
                    append.AddInputData(obj)
                    found_datasets += 1
            it.GoToNextItem()

        if found_datasets == 0:
            print(f"[WARN] No dataset contains field '{field}'.")
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()
            return

        append.Update()
        ug = append.GetOutput()

        if ug is None or ug.GetNumberOfPoints() == 0:
            print("[WARN] Unified grid is empty.")
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # 필드가 Point/Cell 어디에 있는지 확인
        pd_ug = ug.GetPointData()
        cd_ug = ug.GetCellData()

        arr = None
        use_point = False

        if pd_ug.HasArray(field):
            arr = pd_ug.GetArray(field)
            use_point = True
        elif cd_ug.HasArray(field):
            arr = cd_ug.GetArray(field)
            use_point = False
        else:
            print(f"[WARN] Field '{field}' not found in unified grid.")
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # Mapper 설정
        self.renderer.RemoveAllViewProps()

        mapper = vtkDataSetMapper()
        mapper.SetInputData(ug)
        mapper.SetScalarVisibility(True)
        mapper.SelectColorArray(field)
        mapper.SetColorModeToMapScalars()

        if use_point:
            mapper.SetScalarModeToUsePointFieldData()
        else:
            mapper.SetScalarModeToUseCellFieldData()

        if arr is not None:
            data_range = arr.GetRange()
            mapper.SetScalarRange(data_range)

            # Scalar bar 업데이트
            if self.scalar_bar_visible:
                self._create_scalar_bar(mapper, field, data_range)

        actor = vtkActor()
        actor.SetMapper(mapper)

        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def _display_slice(self, field: str):
        """필드를 슬라이스로 표시"""
        if self.reader is None:
            return

        # 필드 데이터셋 생성
        ug = self._build_field_dataset(field)
        if ug is None:
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # Z-normal 슬라이스
        plane = vtk.vtkPlane()
        plane.SetNormal(0, 0, 1)
        plane.SetOrigin(0, 0, self.slice_z)

        cutter = vtk.vtkCutter()
        cutter.SetInputData(ug)
        cutter.SetCutFunction(plane)
        cutter.Update()

        poly = cutter.GetOutput()
        if poly is None or poly.GetNumberOfPoints() == 0:
            print("[WARN] Empty slice")
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
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
            print(f"[WARN] Field '{field}' not found in slice output.")
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()
            return

        data_range = arr.GetRange()

        # 렌더러 초기화
        self.renderer.RemoveAllViewProps()

        # Mapper
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(poly)
        mapper.SetScalarVisibility(True)
        mapper.SelectColorArray(field)
        mapper.SetColorModeToMapScalars()
        if use_point:
            mapper.SetScalarModeToUsePointFieldData()
        else:
            mapper.SetScalarModeToUseCellFieldData()
        mapper.SetScalarRange(data_range)

        # Scalar bar
        if self.scalar_bar_visible:
            self._create_scalar_bar(mapper, field, data_range)

        slice_actor = vtkActor()
        slice_actor.SetMapper(mapper)
        self.renderer.AddActor(slice_actor)

        self.vtk_widget.GetRenderWindow().Render()

    def _build_field_dataset(self, field: str):
        """선택한 필드를 가진 DataSet 병합"""
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
            print(f"[WARN] No dataset contains field '{field}'.")
            return None

        append.Update()
        ug = append.GetOutput()
        if ug is None or ug.GetNumberOfPoints() == 0:
            print(f"[WARN] Unified grid empty for field: {field}")
            return None

        return ug

    # ===== 슬라이스 컨트롤 =====

    def _on_slider_changed(self, value: int):
        """슬라이더 값 변경"""
        if self.zmax == self.zmin:
            return
        ratio = value / 1000.0
        self.slice_z = self.zmin + (self.zmax - self.zmin) * ratio
        self.z_label.setText(f"{self.slice_z:.4f}")

        if self.slice_enabled:
            self._display_field()

    def _update_slider_position(self):
        """현재 slice_z 값에 맞춰 슬라이더 위치 업데이트"""
        if self.zmax == self.zmin:
            return
        ratio = (self.slice_z - self.zmin) / (self.zmax - self.zmin)
        slider_val = int(max(0.0, min(1.0, ratio)) * 1000)

        self.z_slider.blockSignals(True)
        self.z_slider.setValue(slider_val)
        self.z_slider.blockSignals(False)
        self.z_label.setText(f"{self.slice_z:.4f}")

    def enable_slice_mode(self, enabled: bool = True):
        """슬라이스 모드 활성화/비활성화"""
        self.slice_enabled = enabled
        self.z_slider.setEnabled(enabled)
        self._display_field()

    # ===== 스칼라 바 =====

    def _create_scalar_bar(self, mapper, title: str, data_range: tuple):
        """스칼라 바 생성"""
        self._remove_scalar_bar()

        scalar_bar = vtk.vtkScalarBarActor()
        scalar_bar.SetLookupTable(mapper.GetLookupTable())
        scalar_bar.SetTitle(title)
        scalar_bar.SetNumberOfLabels(5)
        scalar_bar.SetPosition(0.9, 0.1)
        scalar_bar.SetWidth(0.08)
        scalar_bar.SetHeight(0.8)

        self.renderer.AddActor2D(scalar_bar)
        self.scalar_bar_actor = scalar_bar

    def _remove_scalar_bar(self):
        """스칼라 바 제거"""
        if self.scalar_bar_actor:
            self.renderer.RemoveActor2D(self.scalar_bar_actor)
            self.scalar_bar_actor = None

    def on_scalar_bar_toggled(self, checked):
        """스칼라 바 표시 토글"""
        icon_name = "scalar_bar_on.png" if checked else "scalar_bar_off.png"
        self.scalar_bar_action.setIcon(self.make_icon(icon_name))
        self.scalar_bar_visible = checked

        if checked:
            self._display_field()
        else:
            self._remove_scalar_bar()
            self.vtk_widget.GetRenderWindow().Render()

    # ===== 뷰 컨트롤 =====

    def on_axes_toggled(self, checked):
        """축 표시 토글"""
        icon_name = "axes_on.png" if checked else "axes_off.png"
        self.axe_action.setIcon(self.make_icon(icon_name))
        if checked:
            self.axes.show()
        else:
            self.axes.hide()

    def on_projection_toggled(self, checked):
        """투영 방식 토글"""
        icon_name = "parallel.png" if checked else "perspective.png"
        self.projection_action.setIcon(self.make_icon(icon_name))
        camera = self.renderer.GetActiveCamera()
        camera.SetParallelProjection(not camera.GetParallelProjection())
        self.vtk_widget.GetRenderWindow().Render()

    def fit_to_scene(self):
        """씬에 맞춰 카메라 리셋"""
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()

    def set_widget_style(self):
        """위젯 스타일 설정"""
        self.renderer.SetBackground2(0.40, 0.40, 0.50)
        self.renderer.SetBackground(0.65, 0.65, 0.70)
        self.renderer.GradientBackgroundOn()

    # ===== 렌더링 =====

    def render_now(self):
        """즉시 렌더링"""
        self.vtk_widget.GetRenderWindow().Render()

    # ===== 정리 =====

    def end(self):
        """위젯 종료"""
        if getattr(self, "_ended", False):
            return
        self._ended = True

        self.cleanup()

        if self.registry:
            self.registry.unregister(self)

    def closeEvent(self, event):
        """닫기 이벤트"""
        self.end()
        super().closeEvent(event)

    def cleanup(self):
        """리소스 정리"""
        try:
            if self.interactor:
                self.interactor.Disable()
                self.interactor.TerminateApp()
                self.interactor = None

            if self.renderer:
                self.renderer.RemoveAllViewProps()
                self.renderer = None

            rw = None
            if self.vtk_widget:
                rw = self.vtk_widget.GetRenderWindow()
            if rw:
                rw.Finalize()
                rw.SetWindowInfo("")
                rw = None
            self.vtk_widget = None

        except Exception as e:
            print(f"[!!] Error (cleanup): {e}")
