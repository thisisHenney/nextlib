"""
기본 형상 생성 클래스

사용 예시:
    from nextlib.vtk.core import GeometrySource

    geo = GeometrySource()
    cube = geo.cube(size=1.0, color=(200, 200, 200))
    sphere = geo.sphere(radius=0.5)
    cylinder = geo.cylinder(radius=0.3, height=1.0)
"""
from typing import Tuple

from vtkmodules.vtkFiltersSources import (
    vtkCubeSource,
    vtkSphereSource,
    vtkCylinderSource,
    vtkConeSource,
    vtkPlaneSource,
    vtkLineSource,
    vtkArcSource,
    vtkDiskSource,
)
from vtkmodules.vtkRenderingCore import vtkPolyDataMapper, vtkActor


class GeometrySource:
    """기본 VTK 형상 생성기"""

    # 기본 색상 - Fusion 360 스타일 미디엄 그레이
    DEFAULT_COLOR = (153, 166, 179)

    @staticmethod
    def _create_actor(source, color: Tuple[int, int, int]) -> vtkActor:
        """소스에서 Actor 생성"""
        mapper = vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())

        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color[0]/255, color[1]/255, color[2]/255)
        return actor

    def cube(
        self,
        size: float = 1.0,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None
    ) -> vtkActor:
        """큐브 생성

        Args:
            size: 한 변의 길이
            color: RGB (0-255)
            position: (x, y, z) 위치
        """
        source = vtkCubeSource()
        source.SetXLength(size)
        source.SetYLength(size)
        source.SetZLength(size)

        actor = self._create_actor(source, color or self.DEFAULT_COLOR)
        if position:
            actor.SetPosition(*position)
        return actor

    def box(
        self,
        x_length: float = 1.0,
        y_length: float = 1.0,
        z_length: float = 1.0,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None
    ) -> vtkActor:
        """박스 생성 (각 축 길이 지정)

        Args:
            x_length, y_length, z_length: 각 축의 길이
            color: RGB (0-255)
            position: (x, y, z) 위치
        """
        source = vtkCubeSource()
        source.SetXLength(x_length)
        source.SetYLength(y_length)
        source.SetZLength(z_length)

        actor = self._create_actor(source, color or self.DEFAULT_COLOR)
        if position:
            actor.SetPosition(*position)
        return actor

    def sphere(
        self,
        radius: float = 0.5,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None,
        resolution: int = 32
    ) -> vtkActor:
        """구 생성

        Args:
            radius: 반지름
            color: RGB (0-255)
            position: (x, y, z) 위치
            resolution: 해상도 (높을수록 부드러움)
        """
        source = vtkSphereSource()
        source.SetRadius(radius)
        source.SetThetaResolution(resolution)
        source.SetPhiResolution(resolution)

        actor = self._create_actor(source, color or (100, 150, 255))
        if position:
            actor.SetPosition(*position)
        return actor

    def cylinder(
        self,
        radius: float = 0.5,
        height: float = 1.0,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None,
        resolution: int = 32
    ) -> vtkActor:
        """실린더 생성

        Args:
            radius: 반지름
            height: 높이
            color: RGB (0-255)
            position: (x, y, z) 위치
            resolution: 해상도
        """
        source = vtkCylinderSource()
        source.SetRadius(radius)
        source.SetHeight(height)
        source.SetResolution(resolution)

        actor = self._create_actor(source, color or (255, 150, 100))
        if position:
            actor.SetPosition(*position)
        return actor

    def cone(
        self,
        radius: float = 0.5,
        height: float = 1.0,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None,
        resolution: int = 32
    ) -> vtkActor:
        """원뿔 생성

        Args:
            radius: 밑면 반지름
            height: 높이
            color: RGB (0-255)
            position: (x, y, z) 위치
            resolution: 해상도
        """
        source = vtkConeSource()
        source.SetRadius(radius)
        source.SetHeight(height)
        source.SetResolution(resolution)

        actor = self._create_actor(source, color or (150, 255, 100))
        if position:
            actor.SetPosition(*position)
        return actor

    def plane(
        self,
        x_length: float = 1.0,
        y_length: float = 1.0,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None,
        x_resolution: int = 1,
        y_resolution: int = 1
    ) -> vtkActor:
        """평면 생성

        Args:
            x_length, y_length: 평면 크기
            color: RGB (0-255)
            position: (x, y, z) 위치
            x_resolution, y_resolution: 분할 수
        """
        source = vtkPlaneSource()
        source.SetXResolution(x_resolution)
        source.SetYResolution(y_resolution)
        # PlaneSource는 기본 크기가 1x1이므로 스케일로 조정
        source.SetOrigin(-x_length/2, -y_length/2, 0)
        source.SetPoint1(x_length/2, -y_length/2, 0)
        source.SetPoint2(-x_length/2, y_length/2, 0)

        actor = self._create_actor(source, color or (180, 180, 180))
        if position:
            actor.SetPosition(*position)
        return actor

    def disk(
        self,
        inner_radius: float = 0.0,
        outer_radius: float = 0.5,
        color: Tuple[int, int, int] = None,
        position: Tuple[float, float, float] = None,
        radial_resolution: int = 1,
        circumferential_resolution: int = 32
    ) -> vtkActor:
        """디스크(원판) 생성

        Args:
            inner_radius: 내부 반지름 (0이면 원판, >0이면 링)
            outer_radius: 외부 반지름
            color: RGB (0-255)
            position: (x, y, z) 위치
        """
        source = vtkDiskSource()
        source.SetInnerRadius(inner_radius)
        source.SetOuterRadius(outer_radius)
        source.SetRadialResolution(radial_resolution)
        source.SetCircumferentialResolution(circumferential_resolution)

        actor = self._create_actor(source, color or (200, 200, 100))
        if position:
            actor.SetPosition(*position)
        return actor

    def line(
        self,
        point1: Tuple[float, float, float] = (0, 0, 0),
        point2: Tuple[float, float, float] = (1, 0, 0),
        color: Tuple[int, int, int] = None,
        line_width: float = 1.0
    ) -> vtkActor:
        """선 생성

        Args:
            point1: 시작점 (x, y, z)
            point2: 끝점 (x, y, z)
            color: RGB (0-255)
            line_width: 선 두께
        """
        source = vtkLineSource()
        source.SetPoint1(*point1)
        source.SetPoint2(*point2)

        actor = self._create_actor(source, color or (255, 255, 255))
        actor.GetProperty().SetLineWidth(line_width)
        return actor

    def arc(
        self,
        center: Tuple[float, float, float] = (0, 0, 0),
        point1: Tuple[float, float, float] = (1, 0, 0),
        point2: Tuple[float, float, float] = (0, 1, 0),
        color: Tuple[int, int, int] = None,
        resolution: int = 32,
        line_width: float = 1.0
    ) -> vtkActor:
        """호 생성

        Args:
            center: 중심점
            point1: 시작점
            point2: 끝점
            color: RGB (0-255)
            resolution: 해상도
            line_width: 선 두께
        """
        source = vtkArcSource()
        source.SetCenter(*center)
        source.SetPoint1(*point1)
        source.SetPoint2(*point2)
        source.SetResolution(resolution)

        actor = self._create_actor(source, color or (255, 255, 255))
        actor.GetProperty().SetLineWidth(line_width)
        return actor

    def axes(
        self,
        length: float = 1.0,
        line_width: float = 2.0
    ) -> list:
        """XYZ 축 생성 (3개의 선 반환)

        Args:
            length: 축 길이
            line_width: 선 두께

        Returns:
            [x_axis, y_axis, z_axis] Actor 리스트
        """
        origin = (0, 0, 0)
        x_axis = self.line(origin, (length, 0, 0), (255, 0, 0), line_width)
        y_axis = self.line(origin, (0, length, 0), (0, 255, 0), line_width)
        z_axis = self.line(origin, (0, 0, length), (0, 0, 255), line_width)
        return [x_axis, y_axis, z_axis]
