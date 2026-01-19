from dataclasses import dataclass, field
from typing import Any
from vtkmodules.vtkRenderingCore import vtkActor


@dataclass
class ObjectData:
    """VTK 객체의 메타데이터를 저장하는 클래스"""
    id: int
    actor: vtkActor
    group: str = "default"
    name: str = ""
    path: str = ""
    visible: bool = True
    opacity: float = 1.0
    color: tuple = (220, 220, 220)  # RGB 0-255
    view_style: str = "surface"
    removed: bool = False
    metadata: dict = field(default_factory=dict)
