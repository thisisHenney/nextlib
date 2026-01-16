from pathlib import Path
from vtkmodules.vtkFiltersSources import vtkCubeSource, vtkSphereSource
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor
from vtkmodules.vtkCommonColor import vtkNamedColors

class GeometrySource:
    def __init__(self):
        self.colors = vtkNamedColors()

    def make_cube(self, size: float = 1.0) -> vtkActor:
        cube = vtkCubeSource()
        cube.SetXLength(size)
        cube.SetYLength(size)
        cube.SetZLength(size)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(cube.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.colors.GetColor3d("Gray"))

        return actor

    def make_sphere(self, radius: float = 0.5) -> vtkActor:
        sphere = vtkSphereSource()
        sphere.SetRadius(radius)
        sphere.SetPhiResolution(50)
        sphere.SetThetaResolution(50)

        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(sphere.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(self.colors.GetColor3d("LightBlue"))
        return actor
