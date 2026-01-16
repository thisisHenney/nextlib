import sys
from pathlib import Path

import vtkmodules.vtkRenderingOpenGL2
from vtkmodules.vtkRenderingCore import (
    vtkRenderer, vtkDataSetMapper, vtkActor
)
from vtkmodules.vtkCommonDataModel import vtkDataSet
from vtkmodules.vtkFiltersCore import vtkAppendFilter
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from vtkmodules.vtkIOGeometry import vtkOpenFOAMReader

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QComboBox, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt


class FoamFieldViewer(QWidget):
    def __init__(self):
        super().__init__()

        self.reader: vtkOpenFOAMReader | None = None
        self.field_names: list[str] = []

        self.setWindowTitle("OpenFOAM MultiBlock Field Viewer")
        self.resize(900, 700)

        main_layout = QVBoxLayout(self)

        # --- VTK 위젯 ---
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtkRenderer()
        self.renderer.SetBackground(1, 1, 1)  # 흰 배경
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.vtk_widget.Initialize()
        self.vtk_widget.Start()

        # --- 컨트롤 영역 ---
        ctrl_layout = QHBoxLayout()
        main_layout.addLayout(ctrl_layout)

        self.load_btn = QPushButton("Load .foam")
        self.load_btn.clicked.connect(self.load_foam)
        ctrl_layout.addWidget(self.load_btn)

        ctrl_layout.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.currentIndexChanged.connect(self.display_selected_field)
        ctrl_layout.addWidget(self.field_combo)

    # ---------------------------------------------------------
    def load_foam(self):
        foam_file, _ = QFileDialog.getOpenFileName(
            self, "Select .foam File", "", "OpenFOAM Case (*.foam)"
        )
        if not foam_file:
            return

        foam_path = Path(foam_file)
        print(f"Loading: {foam_path}")

        reader = vtkOpenFOAMReader()
        reader.SetFileName(str(foam_path))
        reader.EnableAllCellArrays()
        reader.EnableAllPointArrays()
        reader.Update()

        # 타임스텝 설정 (가장 마지막 타임스텝 사용)
        ts_vtk = reader.GetTimeValues()
        if ts_vtk is not None and ts_vtk.GetNumberOfValues() > 0:
            timesteps = [ts_vtk.GetValue(i) for i in range(ts_vtk.GetNumberOfValues())]
            print("Time steps:", timesteps)
            last_t = timesteps[-1]
            reader.UpdateTimeStep(last_t)
            reader.Update()
            print(f"Use time = {last_t}")
        else:
            print("No time steps found, using default state.")

        self.reader = reader

        # 필드 목록 추출
        self.field_names = self.extract_fields_multiblock()
        self.field_combo.blockSignals(True)
        self.field_combo.clear()
        self.field_combo.addItems(self.field_names)
        self.field_combo.blockSignals(False)

        # 기본 필드 표시 (첫 번째 항목)
        if self.field_names:
            self.display_selected_field()

    # ---------------------------------------------------------
    def extract_fields_multiblock(self) -> list[str]:
        """MultiBlock 전체를 순회하여 Point/Cell 필드 이름 수집"""
        fields: set[str] = set()

        if self.reader is None:
            return []

        mb = self.reader.GetOutput()
        if mb is None:
            return []

        it = mb.NewIterator()
        # 파이썬에서 참조 카운트 문제 방지용
        it.UnRegister(None)

        print("Reading fields via composite iterator")

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
    def display_selected_field(self):
        """콤보박스에서 선택된 필드를 MultiBlock 전체에서 찾아서 시각화"""
        if self.reader is None:
            return

        field = self.field_combo.currentText()
        if not field:
            return

        print(f"Displaying field: {field}")

        mb = self.reader.GetOutput()
        if mb is None:
            print("Reader output is None.")
            return

        # --- 1단계: 이 필드를 가진 블록만 골라서 Append ---
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
            print(f"No dataset contains field '{field}'.")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        append.Update()
        ug = append.GetOutput()

        if ug is None or ug.GetNumberOfPoints() == 0:
            print("Unified grid is empty.")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        print("Unified grid points:", ug.GetNumberOfPoints())
        print("Unified PointData arrays:", ug.GetPointData().GetNumberOfArrays())
        print("Unified CellData arrays:", ug.GetCellData().GetNumberOfArrays())

        # --- 2단계: unified grid에서 field가 Point/Cell 어디에 있는지 확인 ---
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
            print(f"Field '{field}' not found in unified grid (Point/Cell).")
            self.renderer.RemoveAllViewProps()
            self.vtk_widget.GetRenderWindow().Render()
            return

        # --- 3단계: Mapper/Actor 설정 후 렌더링 ---
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
            mapper.SetScalarRange(arr.GetRange())

        actor = vtkActor()
        actor.SetMapper(mapper)

        self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.vtk_widget.GetRenderWindow().Render()


# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)

    viewer = FoamFieldViewer()
    viewer.show()

    sys.exit(app.exec())

