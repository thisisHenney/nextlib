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
    # 방법 1: vtk 패키지에서 직접 import
    try:
        import vtk
        if hasattr(vtk, 'vtkOpenFOAMReader'):
            return vtk.vtkOpenFOAMReader
    except ImportError:
        pass

    # 방법 2: vtkmodules에서 import
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

        # 캐시된 데이터
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

        # .foam 파일 존재
        if list(path.glob("*.foam")) or list(path.glob("*.OpenFOAM")):
            return True

        # constant/polyMesh 폴더 존재
        if (path / "constant" / "polyMesh").is_dir():
            return True

        # constant와 system 폴더 존재
        if (path / "constant").is_dir() and (path / "system").is_dir():
            return True

        return False

    def load(self, case_path: str) -> bool:
        """OpenFOAM 케이스를 로드합니다.

        Args:
            case_path: 케이스 폴더 경로 또는 .foam 파일 경로

        Returns:
            성공 여부
        """
        path = Path(case_path)

        # .foam 파일인지 폴더인지 확인
        if path.suffix.lower() in ('.foam', '.openfoam'):
            self._foam_file = path
            self._case_path = path.parent
        elif path.is_dir():
            # OpenFOAM 케이스 폴더인지 검증
            if not self.is_openfoam_case(path):
                return False

            self._case_path = path
            # .foam 파일 찾기 또는 생성
            foam_files = list(path.glob("*.foam")) + list(path.glob("*.OpenFOAM"))
            if foam_files:
                self._foam_file = foam_files[0]
            else:
                # case.foam 파일 생성
                self._foam_file = path / "case.foam"
                try:
                    self._foam_file.touch()
                except Exception:
                    return False
        else:
            return False

        # vtkOpenFOAMReader 가져오기
        ReaderClass = _get_openfoam_reader()
        if ReaderClass is None:
            return False

        try:
            reader = ReaderClass()
            reader.SetFileName(str(self._foam_file))

            # 옵션 설정
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

            # 모든 배열 활성화
            if hasattr(reader, 'EnableAllCellArrays'):
                reader.EnableAllCellArrays()
            if hasattr(reader, 'EnableAllPointArrays'):
                reader.EnableAllPointArrays()

            reader.Update()
            self._reader = reader

            # 타임스텝 정보 추출
            self._extract_time_values()

            # 마지막 타임스텝으로 이동
            if self._time_values:
                self.set_time(self._time_values[-1])

            # 필드 이름 추출
            self._extract_field_names()

            # Surface polydata 생성
            self._create_surface()

            return True

        except Exception:
            return False

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
        """필드 이름들을 추출합니다."""
        self._field_names = []
        if self._reader is None:
            return

        try:
            import vtk
        except ImportError:
            return

        mb = self._reader.GetOutput()
        if mb is None:
            return

        it = mb.NewIterator()
        it.UnRegister(None)

        fields = set()

        while not it.IsDoneWithTraversal():
            obj = it.GetCurrentDataObject()
            if hasattr(obj, 'GetPointData') and hasattr(obj, 'GetCellData'):
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

        self._field_names = sorted(fields)

    def _create_surface(self):
        """외곽 surface polydata를 생성합니다."""
        if self._reader is None:
            return

        try:
            import vtk
        except ImportError:
            return

        # MultiBlock → PolyData 변환
        geom = vtk.vtkCompositeDataGeometryFilter()
        geom.SetInputConnection(self._reader.GetOutputPort())
        geom.Update()

        self._surface_polydata = geom.GetOutput()

        # bounds 계산
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

    def set_time(self, time_value: float):
        """특정 타임스텝으로 이동합니다."""
        if self._reader is None:
            return

        if hasattr(self._reader, 'UpdateTimeStep'):
            self._reader.UpdateTimeStep(time_value)
        elif hasattr(self._reader, 'SetTimeValue'):
            self._reader.SetTimeValue(time_value)

        self._reader.Update()

        # Surface 재생성
        self._create_surface()
        self._extract_field_names()

    # ===== 데이터 접근 =====

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

    # ===== 필드 데이터 =====

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

        # 평면 생성
        plane = vtk.vtkPlane()
        plane.SetOrigin(*origin)
        plane.SetNormal(*normal)

        # ParaView 스타일 파이프라인
        # 1. MultiBlock → PolyData
        geom_all = vtk.vtkCompositeDataGeometryFilter()
        geom_all.SetInputConnection(self._reader.GetOutputPort())
        geom_all.Update()

        # 2. Cell → Point interpolation
        cd2pd = vtk.vtkCellDataToPointData()
        cd2pd.SetInputConnection(geom_all.GetOutputPort())
        cd2pd.Update()

        # 3. Clean polydata
        clean1 = vtk.vtkCleanPolyData()
        clean1.SetInputConnection(cd2pd.GetOutputPort())

        # 4. Slice
        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputConnection(clean1.GetOutputPort())
        cutter.Update()

        # 5. Clean slice result
        clean2 = vtk.vtkCleanPolyData()
        clean2.SetInputConnection(cutter.GetOutputPort())

        # 6. Triangulate
        tri = vtk.vtkTriangleFilter()
        tri.SetInputConnection(clean2.GetOutputPort())
        tri.Update()

        return tri.GetOutput()
