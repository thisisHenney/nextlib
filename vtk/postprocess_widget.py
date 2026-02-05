"""
후처리용 VTK 위젯
OpenFOAM 케이스 파일을 불러와 필드 데이터를 시각화하는 기능 제공
"""
from functools import partial
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QToolBar, QComboBox,
    QFileDialog, QLabel, QSlider, QCheckBox, QMessageBox, QLineEdit, QFrame
)
from PySide6.QtGui import QAction, QIcon, QDoubleValidator
from PySide6.QtCore import Signal, Qt

import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkDataSetMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkAppendFilter
import vtk

from .camera import Camera
from .tool import AxesTool
from .core import OpenFOAMReader

# VTK 경고 메시지 비활성화 (vtk_widget_base.py에서도 설정되지만, 독립 사용 시를 위해 유지)
vtk.vtkObject.GlobalWarningDisplayOff()

RES_DIR = Path(__file__).resolve().parent
ICON_DIR = RES_DIR / "res" / "icon"


class PostprocessWidget(QMainWindow):
    """
    후처리용 VTK 위젯 (QMainWindow 기반 - QToolBar 플로팅/도킹 지원)
    - OpenFOAM 케이스 파일 로딩
    - 필드 데이터 시각화
    - 슬라이스 뷰
    - 스칼라 바 표시
    """

    case_loaded = Signal(str)  # 케이스 로드 완료 시그널
    field_changed = Signal(str)  # 필드 변경 시그널

    def __init__(self, parent=None, registry=None):
        super().__init__(parent)
        self.registry = registry
        self.camera_sync_lock = False

        # OpenFOAM reader
        self.reader = None
        self.field_names: list = []
        self._case_path: str = ""

        # Slice control
        self.slice_enabled = False
        self.slice_axis = "Z"  # 슬라이스 축: X, Y, Z
        self.slice_pos: float = 0.0  # 슬라이스 위치
        self.axis_min: float = 0.0
        self.axis_max: float = 1.0
        # 전체 bounds 저장 (xmin, xmax, ymin, ymax, zmin, zmax)
        self.bounds: tuple = (0, 1, 0, 1, 0, 1)

        # Scalar bar
        self.scalar_bar_actor = None
        self.scalar_bar_widget = None
        self.scalar_bar_visible = True

        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._build_control_panel()

        self._set_background()
        self.interactor.Initialize()

    def _setup_ui(self):
        """UI 레이아웃 설정 (QMainWindow 기반)"""
        # 툴바 (QMainWindow 툴바 영역에 추가 - 플로팅/도킹 지원)
        self.toolbar = QToolBar("Postprocess Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)

        # VTK 위젯을 감싸는 프레임 (Styled Panel)
        self.vtk_frame = QFrame(self)
        self.vtk_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.vtk_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.vtk_frame.setLineWidth(1)

        # 프레임 내부 레이아웃
        frame_layout = QVBoxLayout(self.vtk_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        self.vtk_widget = QVTKRenderWindowInteractor(self.vtk_frame)
        frame_layout.addWidget(self.vtk_widget, stretch=1)

        self.setCentralWidget(self.vtk_frame)

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
        self._add_action("Refresh", "open.png", lambda: self.load_foam_file())
        self.toolbar.addSeparator()

        # Home
        self._add_action("Home", "home.png", self.camera.home)

        # 6방향 뷰
        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            self._add_action(name, f"{name.lower()}.png",
                           partial(self.camera.set_view, name.lower()))

        self.toolbar.addSeparator()

        # 줌 & 피팅
        self._add_action("Zoom In", "zoom_in.png", lambda: self.camera.zoom_in())
        self._add_action("Zoom Out", "zoom_out.png", lambda: self.camera.zoom_out())
        self._add_action("Fit", "fit.png", self.fit_to_scene)

        # 투영 방식 토글
        self._projection_action = self._add_toggle_action(
            "Projection", "perspective.png", "parallel.png",
            self._on_projection_toggled, checked=False
        )

        self.toolbar.addSeparator()

        # 축 토글
        self._axes_action = self._add_toggle_action(
            "Axes", "axes_on.png", "axes_off.png",
            self._on_axes_toggled, checked=True
        )

        # 스칼라 바 토글
        self._scalar_bar_action = self._add_toggle_action(
            "Scalar Bar", "scalar_bar_off.png", "scalar_bar_on.png",
            self._on_scalar_bar_toggled, checked=True
        )

    def _build_control_panel(self):
        """필드 선택 및 슬라이스 컨트롤 툴바 (하단 영역)"""
        ctrl_toolbar = QToolBar("Controls", self)
        ctrl_toolbar.setFloatable(True)
        ctrl_toolbar.setMovable(True)

        # 필드 선택
        ctrl_toolbar.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.setMinimumWidth(120)
        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        ctrl_toolbar.addWidget(self.field_combo)

        ctrl_toolbar.addSeparator()

        # 슬라이스 모드 체크박스
        self.slice_check = QCheckBox("Slice")
        self.slice_check.setChecked(False)
        self.slice_check.toggled.connect(self._on_slice_toggled)
        ctrl_toolbar.addWidget(self.slice_check)

        # 슬라이스 축 선택
        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])
        self.axis_combo.setCurrentText("Z")
        self.axis_combo.currentTextChanged.connect(self._on_axis_changed)
        self.axis_combo.setEnabled(False)
        ctrl_toolbar.addWidget(self.axis_combo)

        # 슬라이스 위치 라벨
        self.axis_label = QLabel("Z:")
        ctrl_toolbar.addWidget(self.axis_label)

        # 슬라이스 위치 슬라이더
        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.setRange(0, 1000)
        self.pos_slider.setMinimumWidth(200)
        self.pos_slider.valueChanged.connect(self._on_slider_changed)
        self.pos_slider.setEnabled(False)
        ctrl_toolbar.addWidget(self.pos_slider)

        # 슬라이스 위치 직접 입력
        self.pos_edit = QLineEdit("0.0")
        self.pos_edit.setFixedWidth(80)
        self.pos_edit.setValidator(QDoubleValidator())
        self.pos_edit.editingFinished.connect(self._on_pos_edit_finished)
        self.pos_edit.setEnabled(False)
        ctrl_toolbar.addWidget(self.pos_edit)

        self.addToolBar(Qt.BottomToolBarArea, ctrl_toolbar)

    def _add_action(self, name: str, icon_name: str, slot):
        """툴바 액션 추가"""
        icon = self._make_icon(icon_name) if icon_name else QIcon()
        action = QAction(icon, name, self)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    def _add_toggle_action(self, name: str, icon_off: str, icon_on: str,
                          slot, checked: bool = False):
        """토글 액션 추가"""
        icon = self._make_icon(icon_on if checked else icon_off)
        action = QAction(icon, name, self)
        action.setCheckable(True)
        action.setChecked(checked)
        action.triggered.connect(slot)
        self.toolbar.addAction(action)
        return action

    def _make_icon(self, name: str) -> QIcon:
        """아이콘 생성"""
        icon_path = ICON_DIR / name
        if icon_path.exists():
            return QIcon(str(icon_path))
        return QIcon()

    def _set_background(self):
        """배경 설정"""
        self.renderer.SetBackground2(0.25, 0.27, 0.33)
        self.renderer.SetBackground(0.15, 0.15, 0.18)
        self.renderer.GradientBackgroundOn()

    # ===== 파일 로딩 =====

    def set_case_path(self, case_path: str):
        """케이스 폴더 경로 등록 (Refresh 버튼에서 사용)"""
        self._case_path = case_path

    def load_foam_file(self, case_path: str = ""):
        """OpenFOAM 케이스 폴더 로드

        Args:
            case_path: 케이스 폴더 경로. 비어있으면 등록된 경로로 새로고침,
                       등록된 경로도 없으면 폴더 선택 다이얼로그 표시.
        """
        if case_path:
            self.load_foam(case_path)
            return

        # 등록된 경로가 있으면 새로고침
        if self._case_path:
            self.load_foam(self._case_path)
            return

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select OpenFOAM Case Folder",
            "",
            QFileDialog.ShowDirsOnly
        )
        if folder_path:
            self.load_foam(folder_path)

    def load_foam(self, file_path: str):
        """OpenFOAM 케이스 로드 (.foam 파일 또는 케이스 폴더)"""
        # OpenFOAMReader 사용 가능 여부 확인
        if not OpenFOAMReader.is_available():
            QMessageBox.warning(
                self, "Module Not Found",
                "vtkOpenFOAMReader를 사용할 수 없습니다.\n\n"
                "다음 명령으로 VTK를 재설치해 주세요:\n"
                "pip install vtk\n\n"
                "또는 conda:\n"
                "conda install -c conda-forge vtk"
            )
            return

        # 폴더인 경우 OpenFOAM 케이스인지 먼저 확인
        from pathlib import Path
        path = Path(file_path)
        if path.is_dir() and not OpenFOAMReader.is_openfoam_case(path):
            QMessageBox.warning(
                self, "Invalid Case",
                f"유효한 OpenFOAM 케이스 폴더가 아닙니다:\n{file_path}\n\n"
                "다음 중 하나가 필요합니다:\n"
                "- constant/polyMesh 폴더\n"
                "- constant 및 system 폴더\n"
                "- .foam 파일"
            )
            return

        # OpenFOAMReader로 로드
        self.foam_reader = OpenFOAMReader()
        if not self.foam_reader.load(file_path):
            QMessageBox.warning(
                self, "Load Failed",
                f"OpenFOAM 케이스 로드 실패:\n{file_path}"
            )
            return

        # VTK 리더 참조 (기존 코드 호환용)
        self.reader = self.foam_reader.get_reader()

        # 필드 목록
        self.field_names = self.foam_reader.get_field_names()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        # Bounds 저장
        bounds = self.foam_reader.get_bounds()
        if bounds:
            self.bounds = bounds
        else:
            self.bounds = (0, 1, 0, 1, 0, 1)

        # 현재 축에 맞는 범위 설정
        self._update_axis_range()

        # 슬라이더/입력 활성화
        self.pos_slider.setEnabled(True)
        self.pos_edit.setEnabled(True)
        self.axis_combo.setEnabled(True)
        self.slice_pos = (self.axis_min + self.axis_max) / 2.0
        self._update_slider_position()

        # 기본 필드 표시
        if self.field_names:
            self._display_field()

        self.fit_to_scene()
        self.case_loaded.emit(str(file_path))

    def _extract_fields(self) -> list:
        """MultiBlock에서 필드 이름 추출"""
        if self.reader is None:
            return []

        mb = self.reader.GetOutput()
        if mb is None:
            return []

        it = mb.NewIterator()
        it.UnRegister(None)

        fields = set()

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
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
            return

        append.Update()
        ug = append.GetOutput()

        if ug is None or ug.GetNumberOfPoints() == 0:
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
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
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
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
        self.axes.show()
        self._render()

    def _display_slice(self, field: str):
        """필드를 슬라이스로 표시"""
        if self.reader is None:
            return

        # 필드 데이터셋 생성
        ug = self._build_field_dataset(field)
        if ug is None:
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
            return

        # 축에 따른 슬라이스 평면 설정
        plane = vtk.vtkPlane()
        if self.slice_axis == "X":
            plane.SetNormal(1, 0, 0)
            plane.SetOrigin(self.slice_pos, 0, 0)
        elif self.slice_axis == "Y":
            plane.SetNormal(0, 1, 0)
            plane.SetOrigin(0, self.slice_pos, 0)
        else:  # Z
            plane.SetNormal(0, 0, 1)
            plane.SetOrigin(0, 0, self.slice_pos)

        cutter = vtk.vtkCutter()
        cutter.SetInputData(ug)
        cutter.SetCutFunction(plane)
        cutter.Update()

        poly = cutter.GetOutput()
        if poly is None or poly.GetNumberOfPoints() == 0:
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
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
            self.renderer.RemoveAllViewProps()
            self._remove_scalar_bar()
            self._render()
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

        self.axes.show()
        self._render()

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
            return None

        append.Update()
        ug = append.GetOutput()
        if ug is None or ug.GetNumberOfPoints() == 0:
            return None

        return ug

    # ===== 슬라이스 컨트롤 =====

    def _on_slice_toggled(self, checked: bool):
        """슬라이스 모드 토글"""
        self.slice_enabled = checked
        enabled = checked and self.reader is not None
        self.pos_slider.setEnabled(enabled)
        self.pos_edit.setEnabled(enabled)
        self.axis_combo.setEnabled(enabled)
        if self.reader is not None:
            self._display_field()

    def _on_axis_changed(self, axis: str):
        """슬라이스 축 변경"""
        self.slice_axis = axis
        self.axis_label.setText(f"{axis}:")
        self._update_axis_range()
        self.slice_pos = (self.axis_min + self.axis_max) / 2.0
        self._update_slider_position()
        if self.slice_enabled and self.reader is not None:
            self._display_field()

    def _update_axis_range(self):
        """현재 축에 맞는 범위 업데이트"""
        if self.slice_axis == "X":
            self.axis_min = self.bounds[0]
            self.axis_max = self.bounds[1]
        elif self.slice_axis == "Y":
            self.axis_min = self.bounds[2]
            self.axis_max = self.bounds[3]
        else:  # Z
            self.axis_min = self.bounds[4]
            self.axis_max = self.bounds[5]

    def _on_slider_changed(self, value: int):
        """슬라이더 값 변경"""
        if self.axis_max == self.axis_min:
            return
        ratio = value / 1000.0
        self.slice_pos = self.axis_min + (self.axis_max - self.axis_min) * ratio

        # 입력창 업데이트 (시그널 차단)
        self.pos_edit.blockSignals(True)
        self.pos_edit.setText(f"{self.slice_pos:.4f}")
        self.pos_edit.blockSignals(False)

        if self.slice_enabled:
            self._display_field()

    def _on_pos_edit_finished(self):
        """위치 직접 입력 완료"""
        try:
            value = float(self.pos_edit.text())
            # 범위 제한
            value = max(self.axis_min, min(self.axis_max, value))
            self.slice_pos = value
            self._update_slider_position()
            if self.slice_enabled:
                self._display_field()
        except ValueError:
            # 잘못된 입력이면 현재 값으로 복원
            self.pos_edit.setText(f"{self.slice_pos:.4f}")

    def _update_slider_position(self):
        """현재 slice_pos 값에 맞춰 슬라이더와 입력창 업데이트"""
        if self.axis_max == self.axis_min:
            return
        ratio = (self.slice_pos - self.axis_min) / (self.axis_max - self.axis_min)
        slider_val = int(max(0.0, min(1.0, ratio)) * 1000)

        self.pos_slider.blockSignals(True)
        self.pos_slider.setValue(slider_val)
        self.pos_slider.blockSignals(False)

        self.pos_edit.blockSignals(True)
        self.pos_edit.setText(f"{self.slice_pos:.4f}")
        self.pos_edit.blockSignals(False)

    # ===== 스칼라 바 =====

    def _create_scalar_bar(self, mapper, title: str, data_range: tuple):
        """스칼라 바 생성 (ParaView 스타일, 드래그 이동/리사이즈 가능)"""
        self._remove_scalar_bar()

        scalar_bar = vtk.vtkScalarBarActor()
        scalar_bar.SetLookupTable(mapper.GetLookupTable())
        scalar_bar.SetTitle(title)
        scalar_bar.SetNumberOfLabels(7)

        # 레이아웃
        scalar_bar.SetTextPositionToPrecedeScalarBar()
        scalar_bar.SetBarRatio(0.25)
        scalar_bar.SetTitleRatio(0.35)
        scalar_bar.SetLabelFormat("%-#6.4g")
        scalar_bar.SetUnconstrainedFontSize(True)
        scalar_bar.SetFixedAnnotationLeaderLineColor(True)

        # 배경/프레임 비활성화
        scalar_bar.SetDrawBackground(False)
        scalar_bar.SetDrawFrame(False)

        # 제목 스타일 (ParaView: 흰색, 볼드, Arial, 그림자)
        title_prop = scalar_bar.GetTitleTextProperty()
        title_prop.SetFontFamilyToArial()
        title_prop.SetFontSize(24)
        title_prop.SetBold(True)
        title_prop.SetItalic(False)
        title_prop.SetColor(1.0, 1.0, 1.0)
        title_prop.SetShadow(True)
        title_prop.SetShadowOffset(1, -1)

        # 라벨 스타일 (ParaView: 흰색, Arial, 그림자)
        label_prop = scalar_bar.GetLabelTextProperty()
        label_prop.SetFontFamilyToArial()
        label_prop.SetFontSize(16)
        label_prop.SetBold(False)
        label_prop.SetItalic(False)
        label_prop.SetColor(1.0, 1.0, 1.0)
        label_prop.SetShadow(True)
        label_prop.SetShadowOffset(1, -1)
        label_prop.SetJustificationToLeft()

        # Annotation 텍스트 스타일
        ann_prop = scalar_bar.GetAnnotationTextProperty()
        ann_prop.SetFontFamilyToArial()
        ann_prop.SetFontSize(10)
        ann_prop.SetColor(1.0, 1.0, 1.0)
        ann_prop.SetShadow(True)

        self.scalar_bar_actor = scalar_bar

        # vtkScalarBarWidget으로 감싸서 드래그 이동/리사이즈 가능하게
        widget = vtk.vtkScalarBarWidget()
        widget.SetInteractor(self.interactor)
        widget.SetScalarBarActor(scalar_bar)
        widget.SetRepositionable(True)
        widget.SetResizable(True)

        # 초기 위치/크기
        rep = widget.GetRepresentation()
        rep.SetPosition(0.87, 0.08)
        rep.SetPosition2(0.12, 0.72)

        widget.On()
        self.scalar_bar_widget = widget

    def _remove_scalar_bar(self):
        """스칼라 바 제거"""
        if self.scalar_bar_widget:
            self.scalar_bar_widget.Off()
            self.scalar_bar_widget = None
        if self.scalar_bar_actor:
            self.scalar_bar_actor = None

    def _on_scalar_bar_toggled(self, checked: bool):
        """스칼라 바 표시 토글"""
        icon_name = "scalar_bar_on.png" if checked else "scalar_bar_off.png"
        self._scalar_bar_action.setIcon(self._make_icon(icon_name))
        self.scalar_bar_visible = checked

        if checked:
            self._display_field()
        else:
            self._remove_scalar_bar()
            self._render()

    # ===== 뷰 컨트롤 =====

    def _on_axes_toggled(self, checked: bool):
        """축 표시 토글"""
        icon_name = "axes_on.png" if checked else "axes_off.png"
        self._axes_action.setIcon(self._make_icon(icon_name))
        if checked:
            self.axes.show()
        else:
            self.axes.hide()

    def _on_projection_toggled(self, checked: bool):
        """투영 방식 토글"""
        icon_name = "parallel.png" if checked else "perspective.png"
        self._projection_action.setIcon(self._make_icon(icon_name))
        self.camera.set_parallel_projection(checked)

    def fit_to_scene(self):
        """씬에 맞춰 카메라 리셋"""
        self.renderer.ResetCamera()
        self._render()

    def _render(self):
        """렌더링"""
        try:
            rw = self.renderer.GetRenderWindow()
            if rw:
                rw.Render()
        except:
            pass

    # ===== 정리 =====

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
            self.vtk_widget = None

        except Exception:
            pass

    def closeEvent(self, event):
        """닫기 이벤트"""
        self.cleanup()
        super().closeEvent(event)
