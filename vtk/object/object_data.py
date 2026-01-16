from dataclasses import dataclass
from vtkmodules.vtkRenderingCore import vtkActor

@dataclass
class ObjectData:
    id: int
    actor: vtkActor
    group: int = 0
    name: str = ""
    path: str = ""
    visible: bool = True
    transparent: bool = False
    opacity: float = 1.0
    view_style: str = "surface"
    removed: bool = False
