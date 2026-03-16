"""
후처리용 VTK 위젯
OpenFOAM 케이스 파일을 불러와 필드 데이터를 시각화하는 기능 제공
"""
from functools import partial
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QHBoxLayout, QToolBar, QComboBox,
    QFileDialog, QLabel, QSlider, QCheckBox, QMessageBox, QLineEdit, QFrame,
    QProgressBar, QSpinBox, QSizePolicy
)
from PySide6.QtGui import QAction, QIcon, QDoubleValidator
from PySide6.QtCore import Signal, Qt, QObject, QThread, QTimer
from PySide6.QtWidgets import QApplication

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkDataSetMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkAppendFilter
import vtk

from .camera import Camera
from .tool import AxesTool
from .core import OpenFOAMReader

vtk.vtkObject.GlobalWarningDisplayOff()

RES_DIR = Path(__file__).resolve().parent
ICON_DIR = RES_DIR / "res" / "icon"


class FoamLoaderWorker(QObject):
    """OpenFOAM 케이스 로드를 별도 스레드에서 실행하는 Worker.

    Qt 메인(UI) 스레드를 블로킹하지 않도록 QThread 위에서 실행됩니다.
    VTK reader.Update() 호출은 데이터 처리만 하므로 스레드 안전합니다.
    렌더링(actor 추가, Render())은 메인 스레드에서만 수행됩니다.
    """
    finished = Signal(bool, str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
        self.foam_reader = None

    def run(self):
        try:
            reader = OpenFOAMReader()
            if reader.load(self.file_path, build_surface=False):
                self.foam_reader = reader
                self.finished.emit(True, "")
            else:
                self.finished.emit(False, "OpenFOAM 케이스 로드 실패")
        except Exception as e:
            self.finished.emit(False, str(e))


class PostprocessWidget(QMainWindow):
    """
    후처리용 VTK 위젯 (QMainWindow 기반 - QToolBar 플로팅/도킹 지원)
    - OpenFOAM 케이스 파일 로딩
    - 필드 데이터 시각화
    - 슬라이스 뷰
    - 스칼라 바 표시
    """

    case_loaded = Signal(str)
    field_changed = Signal(str)

    def __init__(self, parent=None, registry=None):
        super().__init__(parent)
        self.registry = registry
        self.camera_sync_lock = False

        self.reader = None
        self.foam_reader = None
        self.field_names: list = []
        self._case_path: str = ""

        self.slice_enabled = False
        self.slice_axis = "Z"
        self.slice_pos: float = 0.0
        self.axis_min: float = 0.0
        self.axis_max: float = 1.0
        self.bounds: tuple = (0, 1, 0, 1, 0, 1)

        self.scalar_bar_actor = None
        self.scalar_bar_widget = None
        self.scalar_bar_visible = True

        self._loading: bool = False
        self._foam_loader_worker = None
        self._foam_loader_thread = None

        self._anim_time_values: list = []
        self._anim_current_idx: int = 0
        self._anim_is_playing: bool = False
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._on_anim_tick)

        self._overlay_actors: list = []

        self._setup_ui()
        self._setup_vtk()
        self._setup_tools()
        self._build_toolbar()
        self._build_control_panel()
        self._build_anim_toolbar()

        self._set_background()
        self.interactor.Initialize()

    def _setup_ui(self):
        """UI 레이아웃 설정 (QMainWindow 기반)"""
        self.toolbar = QToolBar("Postprocess Toolbar", self)
        self.toolbar.setFloatable(True)
        self.toolbar.setMovable(True)
        self.addToolBar(self.toolbar)

        self.vtk_frame = QFrame(self)
        self.vtk_frame.setFrameShape(QFrame.Shape.StyledPanel)
        self.vtk_frame.setFrameShadow(QFrame.Shadow.Sunken)
        self.vtk_frame.setLineWidth(1)

        frame_layout = QVBoxLayout(self.vtk_frame)
        frame_layout.setContentsMargins(1, 1, 1, 1)
        frame_layout.setSpacing(0)

        self.vtk_widget = QVTKRenderWindowInteractor(self.vtk_frame)
        frame_layout.addWidget(self.vtk_widget, stretch=1)

        self._progress_container = QFrame(self.vtk_frame)
        self._progress_container.setFixedHeight(24)
        progress_layout = QHBoxLayout(self._progress_container)
        progress_layout.setContentsMargins(4, 2, 4, 2)
        progress_layout.setSpacing(8)

        self._progress_label = QLabel("Loading...")
        self._progress_label.setStyleSheet("color: #333; font-size: 10pt;")
        progress_layout.addWidget(self._progress_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #aaa;
                border-radius: 3px;
                background-color: #e8e8ec;
                text-align: center;
                color: #333;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:0.5 #22c55e,
                    stop:1 #f97316
                );
                border-radius: 2px;
            }
        """)
        progress_layout.addWidget(self._progress_bar, stretch=1)

        frame_layout.addWidget(self._progress_container)
        self._progress_container.hide()

        self.setCentralWidget(self.vtk_frame)

    def _setup_vtk(self):
        """VTK 렌더러 및 인터랙터 설정"""
        self.renderer = vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()


    def show_progress(self, message: str = "Loading..."):
        """프로그레스 바 표시"""
        self._progress_label.setText(message)
        self._progress_container.show()

    def update_progress(self, message: str):
        """프로그레스 메시지 업데이트"""
        self._progress_label.setText(message)

    def hide_progress(self):
        """프로그레스 바 숨김"""
        self._progress_container.hide()

    def _setup_tools(self):
        """VTK 도구 초기화"""
        self.camera = Camera(self)
        self.camera.init()

        self.colors = vtkNamedColors()
        self.axes = AxesTool(self)

    def _build_toolbar(self):
        """툴바 구성"""
        refresh = self._add_action("\u21BB", "", lambda: self.load_foam_file())
        refresh.setToolTip("Refresh")
        self.toolbar.addSeparator()

        home = self._add_action("\u2302", "", self.camera.home)
        home.setToolTip("Home")

        for name in ["Front", "Back", "Left", "Right", "Top", "Bottom"]:
            self._add_action(name, f"{name.lower()}.png",
                           partial(self.camera.set_view, name.lower()))

        self.toolbar.addSeparator()

        self._add_action("Zoom In", "zoom_in.png", lambda: self.camera.zoom_in())
        self._add_action("Zoom Out", "zoom_out.png", lambda: self.camera.zoom_out())
        self._add_action("Fit", "fit.png", self.fit_to_scene)

        self._projection_action = self._add_toggle_action(
            "Projection", "perspective.png", "parallel.png",
            self._on_projection_toggled, checked=False
        )

        self.toolbar.addSeparator()

        self._axes_action = self._add_toggle_action(
            "Axes", "axes_on.png", "axes_off.png",
            self._on_axes_toggled, checked=True
        )

        self._scalar_bar_action = self._add_toggle_action(
            "Scalar Bar", "scalar_bar_off.png", "scalar_bar_on.png",
            self._on_scalar_bar_toggled, checked=True
        )

    def _build_control_panel(self):
        """필드 선택 및 슬라이스 컨트롤 툴바 (하단 영역)"""
        ctrl_toolbar = QToolBar("Controls", self)
        ctrl_toolbar.setObjectName("vtkBottomBar")
        ctrl_toolbar.setFloatable(True)
        ctrl_toolbar.setMovable(True)

        ctrl_toolbar.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.setMinimumWidth(120)
        self.field_combo.currentIndexChanged.connect(self._on_field_changed)
        ctrl_toolbar.addWidget(self.field_combo)

        ctrl_toolbar.addSeparator()

        self.slice_check = QCheckBox("Slice")
        self.slice_check.setChecked(False)
        self.slice_check.toggled.connect(self._on_slice_toggled)
        ctrl_toolbar.addWidget(self.slice_check)

        self.axis_combo = QComboBox()
        self.axis_combo.addItems(["X", "Y", "Z"])
        self.axis_combo.setCurrentText("Z")
        self.axis_combo.currentTextChanged.connect(self._on_axis_changed)
        self.axis_combo.setEnabled(False)
        ctrl_toolbar.addWidget(self.axis_combo)

        self.axis_label = QLabel("Z:")
        ctrl_toolbar.addWidget(self.axis_label)

        self.pos_slider = QSlider(Qt.Horizontal)
        self.pos_slider.setRange(0, 1000)
        self.pos_slider.setMinimumWidth(200)
        self.pos_slider.valueChanged.connect(self._on_slider_changed)
        self.pos_slider.setEnabled(False)
        ctrl_toolbar.addWidget(self.pos_slider)

        self.pos_edit = QLineEdit("0.0")
        self.pos_edit.setFixedWidth(80)
        self.pos_edit.setValidator(QDoubleValidator())
        self.pos_edit.editingFinished.connect(self._on_pos_edit_finished)
        self.pos_edit.setEnabled(False)
        ctrl_toolbar.addWidget(self.pos_edit)

        self.addToolBar(Qt.BottomToolBarArea, ctrl_toolbar)

    def _build_anim_toolbar(self):
        """타임스텝 애니메이션 컨트롤 툴바"""
        anim_toolbar = QToolBar("Animation", self)
        anim_toolbar.setObjectName("vtkAnimBar")
        anim_toolbar.setFloatable(True)
        anim_toolbar.setMovable(True)

        self._anim_prev_action = QAction("◀", self)
        self._anim_prev_action.setToolTip("Previous Time Step")
        self._anim_prev_action.triggered.connect(self._on_anim_prev)
        self._anim_prev_action.setEnabled(False)
        anim_toolbar.addAction(self._anim_prev_action)

        self._anim_play_action = QAction("▶", self)
        self._anim_play_action.setToolTip("Play / Pause")
        self._anim_play_action.triggered.connect(self._on_anim_play_pause)
        self._anim_play_action.setEnabled(False)
        anim_toolbar.addAction(self._anim_play_action)

        self._anim_next_action = QAction("▶|", self)
        self._anim_next_action.setToolTip("Next Time Step")
        self._anim_next_action.triggered.connect(self._on_anim_next)
        self._anim_next_action.setEnabled(False)
        anim_toolbar.addAction(self._anim_next_action)

        anim_toolbar.addSeparator()

        self._anim_slider = QSlider(Qt.Horizontal)
        self._anim_slider.setRange(0, 0)
        self._anim_slider.setMinimumWidth(80)
        self._anim_slider.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._anim_slider.setEnabled(False)
        self._anim_slider.valueChanged.connect(self._on_anim_slider_changed)
        anim_toolbar.addWidget(self._anim_slider)

        self._anim_time_combo = QComboBox()
        self._anim_time_combo.setEditable(True)
        self._anim_time_combo.setMinimumWidth(110)
        self._anim_time_combo.setToolTip("Current Time / Select Time Step")
        self._anim_time_combo.setEnabled(False)
        self._anim_time_combo.activated.connect(self._on_anim_time_combo_activated)
        self._anim_time_combo.lineEdit().editingFinished.connect(self._on_anim_time_combo_edited)
        anim_toolbar.addWidget(self._anim_time_combo)

        self._anim_frame_label = QLabel("0 / 0")
        self._anim_frame_label.setMinimumWidth(60)
        anim_toolbar.addWidget(self._anim_frame_label)

        anim_toolbar.addSeparator()

        anim_toolbar.addWidget(QLabel("FPS:"))
        self._anim_fps_spin = QSpinBox()
        self._anim_fps_spin.setRange(1, 60)
        self._anim_fps_spin.setValue(10)
        self._anim_fps_spin.setFixedWidth(65)
        self._anim_fps_spin.setToolTip("Animation Speed (frames per second)")
        anim_toolbar.addWidget(self._anim_fps_spin)

        self.addToolBar(Qt.BottomToolBarArea, anim_toolbar)

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
        """배경색 설정 - Fusion 360 스타일 화이트 그라데이션"""
        self.renderer.SetBackground(0.75, 0.78, 0.82)
        self.renderer.SetBackground2(0.98, 0.98, 1.0)
        self.renderer.GradientBackgroundOn()


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
        """OpenFOAM 케이스 비동기 로드 (.foam 파일 또는 케이스 폴더)"""
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

        path = Path(file_path)
        if path.is_dir() and not OpenFOAMReader.is_openfoam_case(path):
            found = None
            for sub in ("5.CHTFCase", "CHTFCase", "fluid", "run"):
                sp = path / sub
                if sp.is_dir() and OpenFOAMReader.is_openfoam_case(sp):
                    found = sp
                    break
            if found is None:
                try:
                    for child in sorted(path.iterdir()):
                        if child.is_dir() and OpenFOAMReader.is_openfoam_case(child):
                            found = child
                            break
                except Exception:
                    pass
            if found is not None:
                file_path = str(found)
                path = found
            else:
                QMessageBox.warning(
                    self, "Invalid Case",
                    f"유효한 OpenFOAM 케이스 폴더를 찾을 수 없습니다:\n{file_path}\n\n"
                    "다음 중 하나가 필요합니다:\n"
                    "- constant/polyMesh 폴더\n"
                    "- constant 및 system 폴더\n"
                    "- .foam 파일"
                )
                return

        if self._loading:
            return
        self._loading = True

        self.show_progress("Loading case...")
        QApplication.setOverrideCursor(Qt.WaitCursor)

        self._foam_loader_worker = FoamLoaderWorker(file_path)
        self._foam_loader_thread = QThread(self)
        self._foam_loader_worker.moveToThread(self._foam_loader_thread)

        self._foam_loader_thread.started.connect(self._foam_loader_worker.run)
        self._foam_loader_worker.finished.connect(self._on_foam_loaded)
        self._foam_loader_worker.finished.connect(self._foam_loader_thread.quit)
        self._foam_loader_thread.finished.connect(self._foam_loader_thread.deleteLater)

        self._foam_loader_thread.start()

    def _cancel_loading(self):
        """로딩 상태 초기화"""
        self._loading = False

    def _on_foam_loaded(self, success: bool, error_msg: str):
        """백그라운드 로딩 완료 콜백 (메인 스레드에서 실행)"""
        QApplication.restoreOverrideCursor()
        self.hide_progress()
        self._loading = False

        worker = getattr(self, '_foam_loader_worker', None)
        self._foam_loader_worker = None
        self._foam_loader_thread = None

        if not success:
            QMessageBox.warning(self, "Load Failed", f"OpenFOAM 케이스 로드 실패:\n{error_msg}")
            return

        if worker is None or worker.foam_reader is None:
            return

        self.foam_reader = worker.foam_reader
        self._finalize_foam_load()

    def _finalize_foam_load(self):
        """OpenFOAM 케이스 로드 완료 처리"""
        self.hide_progress()

        self.reader = self.foam_reader.get_reader()

        self.field_names = self.foam_reader.get_field_names()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        bounds = self.foam_reader.get_bounds()
        if bounds:
            self.bounds = bounds
        else:
            self.bounds = (0, 1, 0, 1, 0, 1)

        self._update_axis_range()

        self.pos_slider.setEnabled(True)
        self.pos_edit.setEnabled(True)
        self.axis_combo.setEnabled(True)
        self.slice_pos = (self.axis_min + self.axis_max) / 2.0
        self._update_slider_position()

        self._anim_time_values = self.foam_reader.get_time_values()
        self._anim_current_idx = len(self._anim_time_values) - 1 if self._anim_time_values else 0
        self._anim_is_playing = False
        self._anim_timer.stop()
        self._update_anim_ui()

        if self.field_names:
            self._display_field()

        self.fit_to_scene()

        case_path = self.foam_reader._case_path if hasattr(self.foam_reader, '_case_path') else None
        self.case_loaded.emit(str(case_path) if case_path else "")

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


    def _update_anim_ui(self):
        """애니메이션 컨트롤 UI 상태 갱신"""
        n = len(self._anim_time_values)
        has_anim = n > 1

        self._anim_prev_action.setEnabled(has_anim)
        self._anim_play_action.setEnabled(has_anim)
        self._anim_next_action.setEnabled(has_anim)
        self._anim_slider.setEnabled(has_anim)
        self._anim_time_combo.setEnabled(n > 0)

        if n == 0:
            self._anim_slider.setRange(0, 0)
            self._anim_time_combo.blockSignals(True)
            self._anim_time_combo.clear()
            self._anim_time_combo.lineEdit().setText("T: -")
            self._anim_time_combo.blockSignals(False)
            self._anim_frame_label.setText("0 / 0")
            return

        self._anim_slider.blockSignals(True)
        self._anim_slider.setRange(0, n - 1)
        self._anim_slider.setValue(self._anim_current_idx)
        self._anim_slider.blockSignals(False)

        self._anim_time_combo.blockSignals(True)
        self._anim_time_combo.clear()
        for tv in self._anim_time_values:
            self._anim_time_combo.addItem(f"{tv:.6g}")
        self._anim_time_combo.setCurrentIndex(self._anim_current_idx)
        self._anim_time_combo.blockSignals(False)

        self._anim_frame_label.setText(f"{self._anim_current_idx + 1} / {n}")

        play_symbol = "⏸" if self._anim_is_playing else "▶"
        self._anim_play_action.setText(play_symbol)

    def _goto_time_index(self, idx: int):
        """지정 인덱스의 타임스텝으로 이동하고 화면 갱신"""
        if not self._anim_time_values or self.foam_reader is None:
            return
        idx = max(0, min(len(self._anim_time_values) - 1, idx))
        self._anim_current_idx = idx

        t = self._anim_time_values[idx]
        self.foam_reader.update_time(t)

        new_fields = self.foam_reader.get_field_names()
        if new_fields != self.field_names:
            self.field_names = new_fields
            current = self.field_combo.currentText()
            self.field_combo.blockSignals(True)
            self.field_combo.clear()
            self.field_combo.addItems(self.field_names)
            if current in self.field_names:
                self.field_combo.setCurrentText(current)
            self.field_combo.blockSignals(False)

        self._display_field()
        self._update_anim_ui()

    def _on_anim_prev(self):
        self._stop_anim()
        self._goto_time_index(self._anim_current_idx - 1)

    def _on_anim_next(self):
        self._stop_anim()
        self._goto_time_index(self._anim_current_idx + 1)

    def _on_anim_play_pause(self):
        if self._anim_is_playing:
            self._stop_anim()
        else:
            self._start_anim()

    def _start_anim(self):
        if not self._anim_time_values or len(self._anim_time_values) <= 1:
            return
        self._anim_is_playing = True
        fps = self._anim_fps_spin.value()
        self._anim_timer.start(max(1, 1000 // fps))
        self._update_anim_ui()

    def _stop_anim(self):
        self._anim_is_playing = False
        self._anim_timer.stop()
        self._update_anim_ui()

    def _on_anim_tick(self):
        """타이머 틱: 다음 프레임으로 이동, 마지막 도달 시 정지"""
        next_idx = self._anim_current_idx + 1
        if next_idx >= len(self._anim_time_values):
            self._stop_anim()
            return
        self._goto_time_index(next_idx)

    def _on_anim_slider_changed(self, value: int):
        if self._anim_is_playing:
            self._stop_anim()
        self._goto_time_index(value)

    def _on_anim_time_combo_activated(self, index: int):
        """콤보박스에서 항목 선택 시 해당 타임스텝으로 이동"""
        if self._anim_is_playing:
            self._stop_anim()
        self._goto_time_index(index)

    def _on_anim_time_combo_edited(self):
        """콤보박스 직접 입력 후 Enter 시 가장 가까운 타임스텝으로 이동"""
        if not self._anim_time_values:
            return
        text = self._anim_time_combo.lineEdit().text().strip()
        try:
            val = float(text)
        except ValueError:
            return
        closest = min(range(len(self._anim_time_values)),
                      key=lambda i: abs(self._anim_time_values[i] - val))
        if self._anim_is_playing:
            self._stop_anim()
        self._goto_time_index(closest)


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
            self._reapply_overlay_actors()
            self._remove_scalar_bar()
            self._render()
            return

        append.Update()
        ug = append.GetOutput()

        if ug is None or ug.GetNumberOfPoints() == 0:
            self.renderer.RemoveAllViewProps()
            self._reapply_overlay_actors()
            self._remove_scalar_bar()
            self._render()
            return

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
            self._reapply_overlay_actors()
            self._remove_scalar_bar()
            self._render()
            return

        self.renderer.RemoveAllViewProps()
        self._reapply_overlay_actors()

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

            lut = self._create_blue_to_red_lut(data_range)
            mapper.SetLookupTable(lut)

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

        ug = self._build_field_dataset(field)
        if ug is None:
            self.renderer.RemoveAllViewProps()
            self._reapply_overlay_actors()
            self._remove_scalar_bar()
            self._render()
            return

        plane = vtk.vtkPlane()
        if self.slice_axis == "X":
            plane.SetNormal(1, 0, 0)
            plane.SetOrigin(self.slice_pos, 0, 0)
        elif self.slice_axis == "Y":
            plane.SetNormal(0, 1, 0)
            plane.SetOrigin(0, self.slice_pos, 0)
        else:
            plane.SetNormal(0, 0, 1)
            plane.SetOrigin(0, 0, self.slice_pos)

        cutter = vtk.vtkCutter()
        cutter.SetInputData(ug)
        cutter.SetCutFunction(plane)
        cutter.Update()

        poly = cutter.GetOutput()
        if poly is None or poly.GetNumberOfPoints() == 0:
            self.renderer.RemoveAllViewProps()
            self._reapply_overlay_actors()
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
            self._reapply_overlay_actors()
            self._remove_scalar_bar()
            self._render()
            return

        data_range = arr.GetRange()

        self.renderer.RemoveAllViewProps()
        self._reapply_overlay_actors()

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

        lut = self._create_blue_to_red_lut(data_range)
        mapper.SetLookupTable(lut)

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
        else:
            self.axis_min = self.bounds[4]
            self.axis_max = self.bounds[5]

    def _on_slider_changed(self, value: int):
        """슬라이더 값 변경"""
        if self.axis_max == self.axis_min:
            return
        ratio = value / 1000.0
        self.slice_pos = self.axis_min + (self.axis_max - self.axis_min) * ratio

        self.pos_edit.blockSignals(True)
        self.pos_edit.setText(f"{self.slice_pos:.4f}")
        self.pos_edit.blockSignals(False)

        if self.slice_enabled:
            self._display_field()

    def _on_pos_edit_finished(self):
        """위치 직접 입력 완료"""
        try:
            value = float(self.pos_edit.text())
            value = max(self.axis_min, min(self.axis_max, value))
            self.slice_pos = value
            self._update_slider_position()
            if self.slice_enabled:
                self._display_field()
        except ValueError:
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


    def _create_blue_to_red_lut(self, data_range: tuple):
        """파란색(낮음) → 빨간색(높음) 컬러맵 룩업테이블 생성"""
        lut = vtk.vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.SetRange(data_range)

        lut.SetHueRange(0.667, 0.0)
        lut.SetSaturationRange(1.0, 1.0)
        lut.SetValueRange(1.0, 1.0)
        lut.Build()

        return lut

    def _create_scalar_bar(self, mapper, title: str, data_range: tuple):
        """스칼라 바 생성 (ParaView 스타일, 드래그 이동/리사이즈 가능)"""
        self._remove_scalar_bar()

        scalar_bar = vtk.vtkScalarBarActor()
        scalar_bar.SetLookupTable(mapper.GetLookupTable())
        scalar_bar.SetTitle(title)
        scalar_bar.SetNumberOfLabels(7)

        scalar_bar.SetTextPositionToPrecedeScalarBar()
        scalar_bar.SetBarRatio(0.25)
        scalar_bar.SetTitleRatio(0.35)
        scalar_bar.SetLabelFormat("%-#6.4g")
        scalar_bar.SetUnconstrainedFontSize(True)
        scalar_bar.SetFixedAnnotationLeaderLineColor(True)

        scalar_bar.SetDrawBackground(False)
        scalar_bar.SetDrawFrame(False)

        title_prop = scalar_bar.GetTitleTextProperty()
        title_prop.SetFontFamilyToArial()
        title_prop.SetFontSize(24)
        title_prop.SetBold(True)
        title_prop.SetItalic(False)
        title_prop.SetColor(0.2, 0.2, 0.25)
        title_prop.SetShadow(False)

        label_prop = scalar_bar.GetLabelTextProperty()
        label_prop.SetFontFamilyToArial()
        label_prop.SetFontSize(16)
        label_prop.SetBold(False)
        label_prop.SetItalic(False)
        label_prop.SetColor(0.2, 0.2, 0.25)
        label_prop.SetShadow(False)
        label_prop.SetJustificationToLeft()

        ann_prop = scalar_bar.GetAnnotationTextProperty()
        ann_prop.SetFontFamilyToArial()
        ann_prop.SetFontSize(10)
        ann_prop.SetColor(0.2, 0.2, 0.25)
        ann_prop.SetShadow(False)

        self.scalar_bar_actor = scalar_bar

        widget = vtk.vtkScalarBarWidget()
        widget.SetInteractor(self.interactor)
        widget.SetScalarBarActor(scalar_bar)
        widget.SetRepositionable(True)
        widget.SetResizable(True)

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


    def add_overlay_actor(self, actor):
        """슬라이스/필드 변경 후에도 유지되는 오버레이 액터 추가."""
        if actor not in self._overlay_actors:
            self._overlay_actors.append(actor)
        self.renderer.AddActor(actor)

    def clear_overlay_actors(self):
        """모든 오버레이 액터 제거."""
        for actor in self._overlay_actors:
            self.renderer.RemoveActor(actor)
        self._overlay_actors.clear()

    def _reapply_overlay_actors(self):
        """RemoveAllViewProps 이후 오버레이 액터 재추가."""
        for actor in self._overlay_actors:
            self.renderer.AddActor(actor)

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


    def cleanup(self):
        """리소스 정리"""
        self._stop_anim()
        self._cancel_loading()
        thread = getattr(self, '_foam_loader_thread', None)
        if thread is not None and thread.isRunning():
            thread.quit()
            thread.wait(2000)

        try:
            if self.interactor:
                self.interactor.Disable()
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
        """닫기 이벤트 - dock에 embed된 경우 앱 종료 방지"""
        if self.parent() is not None:
            event.ignore()
            return
        self.cleanup()
        super().closeEvent(event)
