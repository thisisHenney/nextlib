"""
메쉬 파일 로더

지원 포맷:
- STL (.stl)
- OBJ (.obj)
- PLY (.ply)
- VTK Legacy (.vtk)
- VTU (.vtu) - Unstructured Grid
- VTP (.vtp) - PolyData
- VTM (.vtm) - MultiBlock
- OpenFOAM polyMesh (constant/polyMesh 폴더)
- OpenFOAM Case (.foam, .OpenFOAM)

사용 예시:
    from nextlib.vtk.core import MeshLoader

    loader = MeshLoader()

    # STL 파일 로드
    actor = loader.load("model.stl")
    actors = loader.load("model.stl", split_regions=True)

    # OpenFOAM 케이스 로드
    actors = loader.load_openfoam("case.foam")
"""
from pathlib import Path
from typing import List, Optional, Union, Tuple

from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor, vtkDataSetMapper
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import vtkPolyDataConnectivityFilter, vtkCleanPolyData
from vtkmodules.vtkFiltersGeometry import vtkGeometryFilter


class MeshLoader:
    """다양한 메쉬 파일 포맷 로더"""

    # 지원 확장자
    SUPPORTED_EXTENSIONS = {
        '.stl', '.obj', '.ply',
        '.vtk', '.vtu', '.vtp', '.vtm',
        '.foam', '.openfoam'
    }

    def __init__(self):
        self.colors = vtkNamedColors()
        self._default_color = self.colors.GetColor3d("Gainsboro")

    def load(
        self,
        file_path: Union[str, Path],
        split_regions: bool = False,
        color: Tuple[int, int, int] = None
    ) -> Union[vtkActor, List[vtkActor], None]:
        """파일 확장자에 따라 자동으로 로더 선택

        Args:
            file_path: 파일 경로
            split_regions: STL/OBJ에서 영역별로 분리할지 여부
            color: RGB 색상 (0-255), None이면 기본색

        Returns:
            vtkActor 또는 Actor 리스트, 실패 시 None
        """
        path = Path(file_path)
        if not self._check_file(path):
            return None

        ext = path.suffix.lower()

        if ext == '.stl':
            return self.load_stl(path, split_regions, color)
        elif ext == '.obj':
            return self.load_obj(path, color)
        elif ext == '.ply':
            return self.load_ply(path, color)
        elif ext == '.vtk':
            return self.load_vtk(path, color)
        elif ext == '.vtu':
            return self.load_vtu(path, color)
        elif ext == '.vtp':
            return self.load_vtp(path, color)
        elif ext == '.vtm':
            return self.load_vtm(path, color)
        elif ext in ('.foam', '.openfoam'):
            return self.load_openfoam(path, color)
        else:
            print(f"[MeshLoader] Unsupported format: {ext}")
            return None

    # ===== 개별 로더 =====

    def load_stl(
        self,
        file_path: Union[str, Path],
        split_regions: bool = False,
        color: Tuple[int, int, int] = None
    ) -> Union[vtkActor, List[vtkActor], None]:
        """STL 파일 로드

        Args:
            file_path: STL 파일 경로
            split_regions: 연결된 영역별로 분리할지 여부
            color: RGB 색상 (0-255)
        """
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOGeometry import vtkSTLReader

        reader = vtkSTLReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        poly = reader.GetOutput()
        if split_regions:
            return self._split_regions(poly, color)
        else:
            return self._poly_to_actor(poly, color)

    def load_obj(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> Optional[vtkActor]:
        """OBJ 파일 로드"""
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOGeometry import vtkOBJReader

        reader = vtkOBJReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        return self._poly_to_actor(reader.GetOutput(), color)

    def load_ply(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> Optional[vtkActor]:
        """PLY 파일 로드"""
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOPLY import vtkPLYReader

        reader = vtkPLYReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        return self._poly_to_actor(reader.GetOutput(), color)

    def load_vtk(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> Optional[vtkActor]:
        """VTK Legacy 파일 로드 (.vtk)"""
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOLegacy import vtkDataSetReader

        reader = vtkDataSetReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        output = reader.GetOutput()
        return self._dataset_to_actor(output, color)

    def load_vtu(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> Optional[vtkActor]:
        """VTU 파일 로드 (Unstructured Grid)"""
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader

        reader = vtkXMLUnstructuredGridReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        return self._dataset_to_actor(reader.GetOutput(), color)

    def load_vtp(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> Optional[vtkActor]:
        """VTP 파일 로드 (PolyData)"""
        if not self._check_file(file_path):
            return None

        from vtkmodules.vtkIOXML import vtkXMLPolyDataReader

        reader = vtkXMLPolyDataReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        return self._poly_to_actor(reader.GetOutput(), color)

    def load_vtm(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> List[vtkActor]:
        """VTM 파일 로드 (MultiBlock)"""
        if not self._check_file(file_path):
            return []

        from vtkmodules.vtkIOXML import vtkXMLMultiBlockDataReader

        reader = vtkXMLMultiBlockDataReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        return self._multiblock_to_actors(reader.GetOutput(), color)

    def load_openfoam(
        self,
        file_path: Union[str, Path],
        color: Tuple[int, int, int] = None,
        time_value: float = None
    ) -> List[vtkActor]:
        """OpenFOAM 케이스 로드 (.foam, .OpenFOAM)

        Args:
            file_path: .foam 또는 .OpenFOAM 파일 경로
            color: RGB 색상 (0-255)
            time_value: 특정 시간값 (None이면 최신)

        Returns:
            Actor 리스트
        """
        if not self._check_file(file_path):
            return []

        try:
            from vtkmodules.vtkIOOpenFOAM import vtkOpenFOAMReader
        except ImportError:
            print("[MeshLoader] vtkIOOpenFOAM not available")
            return []

        reader = vtkOpenFOAMReader()
        reader.SetFileName(str(file_path))
        reader.DecomposePolyhedraOn()
        reader.CacheMeshOn()
        reader.Update()

        # 시간값 설정
        time_values = reader.GetTimeValues()
        if time_values and time_values.GetNumberOfTuples() > 0:
            if time_value is not None:
                reader.SetTimeValue(time_value)
            else:
                # 마지막 시간값 사용
                last_time = time_values.GetValue(time_values.GetNumberOfTuples() - 1)
                reader.SetTimeValue(last_time)
            reader.Update()

        return self._multiblock_to_actors(reader.GetOutput(), color)

    def load_polymesh(
        self,
        case_dir: Union[str, Path],
        color: Tuple[int, int, int] = None
    ) -> List[vtkActor]:
        """OpenFOAM polyMesh 폴더 직접 로드

        Args:
            case_dir: OpenFOAM 케이스 디렉토리 (constant/polyMesh 상위)
            color: RGB 색상 (0-255)

        Returns:
            Actor 리스트
        """
        case_path = Path(case_dir)

        # .foam 파일 찾기 또는 생성
        foam_files = list(case_path.glob("*.foam")) + list(case_path.glob("*.OpenFOAM"))

        if foam_files:
            return self.load_openfoam(foam_files[0], color)

        # polyMesh 폴더 확인
        polymesh_path = case_path / "constant" / "polyMesh"
        if not polymesh_path.exists():
            print(f"[MeshLoader] polyMesh not found: {polymesh_path}")
            return []

        # 임시 .foam 파일 생성 후 로드
        temp_foam = case_path / "temp.foam"
        try:
            temp_foam.touch()
            actors = self.load_openfoam(temp_foam, color)
            return actors
        finally:
            if temp_foam.exists():
                temp_foam.unlink()

    # ===== 헬퍼 메서드 =====

    def _check_file(self, file_path: Union[str, Path]) -> bool:
        """파일 존재 확인"""
        path = Path(file_path)
        if not path.exists():
            print(f"[MeshLoader] File not found: {path}")
            return False
        return True

    def _get_color(self, color: Tuple[int, int, int] = None):
        """색상 반환 (0-1 범위)"""
        if color:
            return (color[0]/255, color[1]/255, color[2]/255)
        return self._default_color

    def _poly_to_actor(self, poly_data, color: Tuple[int, int, int] = None) -> vtkActor:
        """PolyData를 Actor로 변환"""
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(poly_data)

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self._get_color(color))

        return actor

    def _dataset_to_actor(self, dataset, color: Tuple[int, int, int] = None) -> vtkActor:
        """DataSet을 Actor로 변환 (GeometryFilter 사용)"""
        # Unstructured Grid 등을 PolyData로 변환
        geometry = vtkGeometryFilter()
        geometry.SetInputData(dataset)
        geometry.Update()

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(geometry.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self._get_color(color))

        return actor

    def _multiblock_to_actors(
        self,
        multiblock,
        color: Tuple[int, int, int] = None
    ) -> List[vtkActor]:
        """MultiBlock 데이터를 Actor 리스트로 변환"""
        actors = []

        if multiblock is None:
            return actors

        num_blocks = multiblock.GetNumberOfBlocks()

        for i in range(num_blocks):
            block = multiblock.GetBlock(i)
            if block is None:
                continue

            # 재귀적으로 처리 (중첩 MultiBlock)
            if hasattr(block, 'GetNumberOfBlocks'):
                actors.extend(self._multiblock_to_actors(block, color))
            elif hasattr(block, 'GetNumberOfCells') and block.GetNumberOfCells() > 0:
                actor = self._dataset_to_actor(block, color)
                actors.append(actor)

        return actors

    def _split_regions(
        self,
        poly_data,
        color: Tuple[int, int, int] = None
    ) -> List[vtkActor]:
        """연결된 영역별로 분리"""
        conn = vtkPolyDataConnectivityFilter()
        conn.SetInputData(poly_data)
        conn.SetExtractionModeToAllRegions()
        conn.ColorRegionsOn()
        conn.Update()

        num_regions = conn.GetNumberOfExtractedRegions()
        actors = []

        for region_id in range(num_regions):
            single = vtkPolyDataConnectivityFilter()
            single.SetInputData(poly_data)
            single.SetExtractionModeToSpecifiedRegions()
            single.AddSpecifiedRegion(region_id)
            single.Update()

            clean = vtkCleanPolyData()
            clean.SetInputData(single.GetOutput())
            clean.Update()

            actor = self._poly_to_actor(clean.GetOutput(), color)
            actors.append(actor)

        return actors

    # ===== 정보 조회 =====

    def get_info(self, file_path: Union[str, Path]) -> dict:
        """파일 정보 조회 (로드하지 않고)

        Returns:
            {
                'path': str,
                'extension': str,
                'size_mb': float,
                'supported': bool
            }
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        return {
            'path': str(path),
            'extension': ext,
            'size_mb': path.stat().st_size / (1024 * 1024) if path.exists() else 0,
            'supported': ext in self.SUPPORTED_EXTENSIONS
        }

    @classmethod
    def supported_formats(cls) -> List[str]:
        """지원하는 파일 확장자 목록"""
        return sorted(list(cls.SUPPORTED_EXTENSIONS))
