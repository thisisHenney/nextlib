from pathlib import Path
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor
from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkFiltersCore import (
    vtkPolyDataConnectivityFilter, vtkCleanPolyData
)


class MeshLoader:
    def __init__(self):
        self.colors = vtkNamedColors()

    def check_file(self, file_path: str | Path):
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            print(f"[!!] File not found: {path}")
            return False
        return True

    def load_stl(self, file_path: str | Path, solid_split: bool = False):
        if not self.check_file(file_path):
            return None

        reader = vtkSTLReader()
        reader.SetFileName(str(file_path))
        reader.Update()

        poly = reader.GetOutput()
        if not solid_split:
            actor = self._load_stl_dump(poly)
            return actor
        else:
            actors = self._load_stl_as_separate_objects(poly)
            return actors

    def _load_stl_dump(self, poly):
        mapper = vtkPolyDataMapper()
        mapper.SetInputData(poly)

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.colors.GetColor3d("Gainsboro"))

        return actor

    def _load_stl_as_separate_objects(self, poly):
        conn = vtkPolyDataConnectivityFilter()
        conn.SetInputData(poly)
        conn.SetExtractionModeToAllRegions()
        conn.ColorRegionsOn()
        conn.Update()

        num_regions = conn.GetNumberOfExtractedRegions()

        actors = []

        for region_id in range(num_regions):
            single = vtkPolyDataConnectivityFilter()
            single.SetInputData(poly)
            single.SetExtractionModeToSpecifiedRegions()
            single.AddSpecifiedRegion(region_id)
            single.Update()

            clean = vtkCleanPolyData()
            clean.SetInputData(single.GetOutput())
            clean.Update()

            mapper = vtkPolyDataMapper()
            mapper.SetInputData(clean.GetOutput())

            actor = vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(self.colors.GetColor3d("Gainsboro"))

            actors.append(actor)

        return actors
