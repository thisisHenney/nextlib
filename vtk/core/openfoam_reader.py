"""
OpenFOAM 케이스 리더

vtkOpenFOAMReader를 사용하여 OpenFOAM 케이스를 로드합니다.
vtk 패키지와 vtkmodules 패키지 모두 지원합니다.

사용 예시:
    from nextlib.vtk.core import OpenFOAMReader

    reader = OpenFOAMReader()
    if reader.load("/path/to/case"):
        polydata = reader.get_surface()
        fields = reader.get_field_names()
"""
from pathlib import Path
from typing import Optional, List, Tuple
import math


def _get_openfoam_reader():
    """vtkOpenFOAMReader를 가져옵니다. vtk 또는 vtkmodules에서 시도합니다."""
    try:
        import vtk
        if hasattr(vtk, 'vtkOpenFOAMReader'):
            return vtk.vtkOpenFOAMReader
    except ImportError:
        pass

    try:
        from vtkmodules.vtkIOOpenFOAM import vtkOpenFOAMReader
        return vtkOpenFOAMReader
    except ImportError:
        pass

    return None


class OpenFOAMReader:
    """
    OpenFOAM 케이스 리더

    vtk.vtkOpenFOAMReader를 래핑하여 편리한 인터페이스를 제공합니다.
    """

    def __init__(self):
        self._reader = None
        self._case_path: Optional[Path] = None
        self._foam_file: Optional[Path] = None

        self._surface_polydata = None
        self._bounds: Optional[Tuple[float, ...]] = None
        self._center: Optional[Tuple[float, float, float]] = None
        self._diagonal_length: Optional[float] = None
        self._field_names: List[str] = []
        self._time_values: List[float] = []

    @staticmethod
    def is_available() -> bool:
        """vtkOpenFOAMReader를 사용할 수 있는지 확인합니다."""
        return _get_openfoam_reader() is not None

    @staticmethod
    def is_openfoam_case(path: Path) -> bool:
        """OpenFOAM 케이스 폴더인지 확인합니다.

        다음 조건 중 하나를 만족하면 OpenFOAM 케이스로 인식:
        - constant/polyMesh 폴더 존재
        - constant 폴더와 system 폴더 존재
        - .foam 또는 .OpenFOAM 파일 존재
        """
        if not path.is_dir():
            return False

        if list(path.glob("*.foam")) or list(path.glob("*.OpenFOAM")):
            return True

        if (path / "constant" / "polyMesh").is_dir():
            return True

        if (path / "constant").is_dir() and (path / "system").is_dir():
            return True

        return False

    def load(self, case_path: str, build_surface: bool = True) -> bool:
        """OpenFOAM 케이스를 로드합니다.

        Args:
            case_path: 케이스 폴더 경로 또는 .foam 파일 경로

        Returns:
            성공 여부
        """
        path = Path(case_path)

        if path.suffix.lower() in ('.foam', '.openfoam'):
            self._foam_file = path
            self._case_path = path.parent
        elif path.is_dir():
            if not self.is_openfoam_case(path):
                return False

            self._case_path = path
            foam_files = list(path.glob("*.foam")) + list(path.glob("*.OpenFOAM"))
            if foam_files:
                self._foam_file = foam_files[0]
            else:
                self._foam_file = path / "case.foam"
                try:
                    self._foam_file.touch()
                except Exception:
                    return False
        else:
            return False

        ReaderClass = _get_openfoam_reader()
        if ReaderClass is None:
            return False

        try:
            reader = ReaderClass()
            reader.SetFileName(str(self._foam_file))

            if hasattr(reader, 'SetCreateCellToPointOn'):
                reader.SetCreateCellToPointOn()
            elif hasattr(reader, 'SetCreateCellToPoint'):
                reader.SetCreateCellToPoint(1)

            if hasattr(reader, 'DecomposePolyhedraOn'):
                reader.DecomposePolyhedraOn()
            elif hasattr(reader, 'SetDecomposePolyhedra'):
                reader.SetDecomposePolyhedra(1)

            if hasattr(reader, 'CacheMeshOn'):
                reader.CacheMeshOn()

            reader.Update()

            if hasattr(reader, 'EnableAllCellArrays'):
                reader.EnableAllCellArrays()
            if hasattr(reader, 'EnableAllPointArrays'):
                reader.EnableAllPointArrays()
            if hasattr(reader, 'EnableAllPatchArrays'):
                reader.EnableAllPatchArrays()
            if hasattr(reader, 'EnableAllLagrangianArrays'):
                reader.EnableAllLagrangianArrays()

            self._reader = reader

            self._extract_time_values()

            if self._time_values:
                last_time = self._time_values[-1]
                try:
                    exec_ = reader.GetExecutive()
                    if hasattr(exec_, 'SetUpdateTimeStep'):
                        exec_.SetUpdateTimeStep(0, last_time)
                except Exception:
                    if hasattr(reader, 'SetTimeValue'):
                        reader.SetTimeValue(last_time)

            reader.Update()

            self._extract_field_names()

            if build_surface:
                self._create_surface()

            return True

        except Exception:
            return False

        finally:
            try:
                if self._reader is not None:
                    self._compute_bounds_fast()
            except Exception:
                pass

    def _extract_time_values(self):
        """타임스텝 값들을 추출합니다."""
        self._time_values = []
        if self._reader is None:
            return

        ts_vtk = self._reader.GetTimeValues()
        if ts_vtk is not None:
            for i in range(ts_vtk.GetNumberOfValues()):
                self._time_values.append(ts_vtk.GetValue(i))

    def _extract_field_names(self):
        """필드 이름들을 추출합니다. CHTMultiRegion 중첩 구조 지원."""
        self._field_names = []
        if self._reader is None:
            return

        mb = self._reader.GetOutput()
        if mb is None:
            return

        fields = set()

        def _collect_fields(data_obj):
            """재귀적으로 모든 leaf 데이터셋에서 필드 이름 수집."""
            if data_obj is None:
                return
            if hasattr(data_obj, 'GetPointData') and hasattr(data_obj, 'GetCellData'):
                pd = data_obj.GetPointData()
                cd = data_obj.GetCellData()
                for i in range(pd.GetNumberOfArrays()):
                    name = pd.GetArrayName(i)
                    if name:
                        fields.add(name)
                for i in range(cd.GetNumberOfArrays()):
                    name = cd.GetArrayName(i)
                    if name:
                        fields.add(name)
            if hasattr(data_obj, 'GetNumberOfBlocks'):
                for i in range(data_obj.GetNumberOfBlocks()):
                    child = data_obj.GetBlock(i)
                    _collect_fields(child)

        _collect_fields(mb)
        self._field_names = sorted(fields)

    def _compute_bounds_fast(self):
        """리프 블록 순회로 bounds 계산 (composite dataset은 GetBounds 호출 안 함)."""
        if self._reader is None:
            return

        mb = self._reader.GetOutput()
        if mb is None:
            return

        xmin = ymin = zmin = float('inf')
        xmax = ymax = zmax = float('-inf')

        def _visit(obj):
            nonlocal xmin, xmax, ymin, ymax, zmin, zmax
            if obj is None:
                return
            if hasattr(obj, 'GetNumberOfBlocks'):
                for i in range(obj.GetNumberOfBlocks()):
                    _visit(obj.GetBlock(i))
                return
            if (hasattr(obj, 'GetBounds') and hasattr(obj, 'GetNumberOfPoints')
                    and obj.GetNumberOfPoints() > 0):
                try:
                    b = obj.GetBounds()
                    if b and len(b) >= 6:
                        xmin = min(xmin, b[0]); xmax = max(xmax, b[1])
                        ymin = min(ymin, b[2]); ymax = max(ymax, b[3])
                        zmin = min(zmin, b[4]); zmax = max(zmax, b[5])
                except Exception:
                    pass

        _visit(mb)

        if xmin == float('inf'):
            return

        self._bounds = (xmin, xmax, ymin, ymax, zmin, zmax)
        self._center = (
            0.5 * (xmin + xmax),
            0.5 * (ymin + ymax),
            0.5 * (zmin + zmax),
        )
        dx, dy, dz = xmax - xmin, ymax - ymin, zmax - zmin
        self._diagonal_length = math.sqrt(dx*dx + dy*dy + dz*dz)

    def _create_surface(self):
        """외곽 surface polydata를 생성합니다."""
        if self._reader is None:
            return

        try:
            import vtk
        except ImportError:
            return

        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputConnection(self._reader.GetOutputPort())
        geom.Update()

        self._surface_polydata = geom.GetOutput()

        if self._surface_polydata:
            b = self._surface_polydata.GetBounds()
            self._bounds = b

            cx = 0.5 * (b[0] + b[1])
            cy = 0.5 * (b[2] + b[3])
            cz = 0.5 * (b[4] + b[5])
            self._center = (cx, cy, cz)

            dx = b[1] - b[0]
            dy = b[3] - b[2]
            dz = b[5] - b[4]
            self._diagonal_length = math.sqrt(dx * dx + dy * dy + dz * dz)

    def update_time(self, time_value: float):
        """애니메이션용 타임스텝 업데이트 (surface 재생성 없음, 빠른 프레임 전환).

        set_time()과 달리 surface를 재생성하지 않으므로 애니메이션에 적합합니다.
        """
        self._set_time_no_surface(time_value)
        self._extract_field_names()

    def set_time(self, time_value: float):
        """특정 타임스텝으로 이동합니다 (surface 재생성 포함)."""
        self._set_time_no_surface(time_value)
        self._create_surface()
        self._extract_field_names()

    def _set_time_no_surface(self, time_value: float):
        """타임스텝만 변경합니다 (surface 생성 없음, 배경 스레드 안전)."""
        if self._reader is None:
            return

        if hasattr(self._reader, 'UpdateTimeStep'):
            self._reader.UpdateTimeStep(time_value)
        elif hasattr(self._reader, 'SetTimeValue'):
            self._reader.SetTimeValue(time_value)

        self._reader.Update()


    def get_reader(self):
        """VTK 리더 객체를 반환합니다."""
        return self._reader

    def get_surface(self):
        """외곽 surface polydata를 반환합니다."""
        return self._surface_polydata

    def get_bounds(self) -> Optional[Tuple[float, ...]]:
        """바운딩 박스를 반환합니다. (xmin, xmax, ymin, ymax, zmin, zmax)"""
        return self._bounds

    def get_center(self) -> Optional[Tuple[float, float, float]]:
        """중심점을 반환합니다."""
        return self._center

    def get_diagonal_length(self) -> Optional[float]:
        """대각선 길이를 반환합니다."""
        return self._diagonal_length

    def get_field_names(self) -> List[str]:
        """필드 이름 목록을 반환합니다."""
        return self._field_names.copy()

    def get_time_values(self) -> List[float]:
        """타임스텝 값 목록을 반환합니다."""
        return self._time_values.copy()

    def get_case_path(self) -> Optional[Path]:
        """케이스 경로를 반환합니다."""
        return self._case_path


    def get_field_dataset(self, field_name: str):
        """특정 필드를 포함하는 통합 데이터셋을 반환합니다."""
        if self._reader is None:
            return None

        try:
            import vtk
            from vtkmodules.vtkFiltersCore import vtkAppendFilter
            from vtkmodules.vtkCommonDataModel import vtkDataSet
        except ImportError:
            return None

        mb = self._reader.GetOutput()
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
                if pd.HasArray(field_name) or cd.HasArray(field_name):
                    append.AddInputData(obj)
                    count += 1
            it.GoToNextItem()

        if count == 0:
            return None

        append.Update()
        return append.GetOutput()

    def create_slice(self, origin: Tuple[float, float, float],
                    normal: Tuple[float, float, float]):
        """슬라이스 polydata를 생성합니다.

        Args:
            origin: 평면 원점 (x, y, z)
            normal: 평면 법선 벡터 (nx, ny, nz)

        Returns:
            슬라이스 결과 polydata
        """
        if self._reader is None:
            return None

        try:
            import vtk
        except ImportError:
            return None

        plane = vtk.vtkPlane()
        plane.SetOrigin(*origin)
        plane.SetNormal(*normal)

        geom_all = vtk.vtkCompositeDataGeometryFilter()
        geom_all.SetInputConnection(self._reader.GetOutputPort())
        geom_all.Update()

        cd2pd = vtk.vtkCellDataToPointData()
        cd2pd.SetInputConnection(geom_all.GetOutputPort())
        cd2pd.Update()

        clean1 = vtk.vtkCleanPolyData()
        clean1.SetInputConnection(cd2pd.GetOutputPort())

        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputConnection(clean1.GetOutputPort())
        cutter.Update()

        clean2 = vtk.vtkCleanPolyData()
        clean2.SetInputConnection(cutter.GetOutputPort())

        tri = vtk.vtkTriangleFilter()
        tri.SetInputConnection(clean2.GetOutputPort())
        tri.Update()

        return tri.GetOutput()
