"""
3D 눈금자 도구

객체 주변에 XYZ 축 눈금과 그리드를 표시
"""
from typing import List
import numpy as np
from PySide6.QtCore import QObject, Signal
from vtkmodules.vtkRenderingAnnotation import vtkCubeAxesActor
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingCore import vtkActor


class RulerTool(QObject):
    visibility_changed = Signal(bool)

    def __init__(self, widget):
        """
        Args:
            widget: VtkWidgetBase 인스턴스 (renderer, interactor 속성 필요)
        """
        super().__init__(widget)

        self._widget = widget
        self._renderer = widget.renderer
        self._interactor = widget.interactor
        self._visible = False
        self._actor = None

        # 축 색상 초기화
        colors = vtkNamedColors()
        self._axis_x_color = colors.GetColor3d("orangered")
        self._axis_y_color = colors.GetColor3d("green_yellow")
        self._axis_z_color = colors.GetColor3d("deepskyblue")

    def show(self, actors: List[vtkActor] = None, scale: float = 1.05):
        """눈금자 표시

        Args:
            actors: 바운딩 박스 계산에 사용할 액터 리스트 (None이면 씬 전체)
            scale: 바운딩 박스 확장 비율
        """
        # 기존 액터 제거
        if self._actor:
            self._renderer.RemoveActor(self._actor)
            self._actor = None

        # bounds 계산
        bounds = self._calculate_bounds(actors, scale)

        # CubeAxesActor 생성
        actor = vtkCubeAxesActor()
        actor.SetCamera(self._renderer.GetActiveCamera())
        actor.SetBounds(bounds)
        self._apply_style(actor)

        self._renderer.AddActor(actor)
        self._actor = actor
        self._interactor.Render()

        if not self._visible:
            self._visible = True
            self.visibility_changed.emit(True)

    def hide(self):
        """눈금자 숨김"""
        if not self._visible:
            return

        if self._actor:
            self._renderer.RemoveActor(self._actor)
            self._actor = None

        self._interactor.Render()
        self._visible = False
        self.visibility_changed.emit(False)

    def toggle(self, actors: List[vtkActor] = None) -> bool:
        """토글 (반환: 현재 상태)"""
        if self._visible:
            self.hide()
        else:
            self.show(actors)
        return self._visible

    def is_visible(self) -> bool:
        """현재 가시성"""
        return self._visible

    def update(self, actors: List[vtkActor] = None, scale: float = 1.05):
        """눈금자 업데이트 (현재 표시 중일 때만)"""
        if self._visible:
            self.show(actors, scale)

    def _calculate_bounds(self, actors: List[vtkActor], scale: float) -> List[float]:
        """바운딩 박스 계산"""
        if not actors:
            return [-0.5, 0.5, -0.5, 0.5, -0.5, 0.5]

        all_bounds = np.array([actor.GetBounds() for actor in actors])
        xmin, ymin, zmin = np.min(all_bounds[:, [0, 2, 4]], axis=0)
        xmax, ymax, zmax = np.max(all_bounds[:, [1, 3, 5]], axis=0)

        # 중심점
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2

        # 스케일 적용
        sx = (xmax - xmin) * scale / 2
        sy = (ymax - ymin) * scale / 2
        sz = (zmax - zmin) * scale / 2

        # 최소 크기 보장
        if sx == 0 and sy == 0 and sz == 0:
            sx = sy = sz = 0.5

        return [
            cx - sx, cx + sx,
            cy - sy, cy + sy,
            cz - sz, cz + sz,
        ]

    def _apply_style(self, actor: vtkCubeAxesActor):
        """스타일 적용"""
        actor.SetUseTextActor3D(False)

        # 축별 색상 설정
        colors = [self._axis_x_color, self._axis_y_color, self._axis_z_color]
        for i, color in enumerate(colors):
            actor.GetTitleTextProperty(i).SetColor(color)
            actor.GetTitleTextProperty(i).SetFontSize(64)
            actor.GetLabelTextProperty(i).SetColor(color)

        # 그리드 라인 설정
        actor.DrawXGridlinesOn()
        actor.DrawYGridlinesOn()
        actor.DrawZGridlinesOn()
        actor.SetGridLineLocation(actor.VTK_GRID_LINES_FURTHEST)

        # 마이너 틱 설정
        actor.XAxisMinorTickVisibilityOn()
        actor.YAxisMinorTickVisibilityOn()
        actor.ZAxisMinorTickVisibilityOn()

        # 외곽 모드
        actor.SetFlyModeToOuterEdges()

    def set_axis_colors(self, x_color: str, y_color: str, z_color: str):
        """축 색상 설정

        Args:
            x_color, y_color, z_color: vtkNamedColors에서 지원하는 색상 이름
        """
        colors = vtkNamedColors()
        self._axis_x_color = colors.GetColor3d(x_color)
        self._axis_y_color = colors.GetColor3d(y_color)
        self._axis_z_color = colors.GetColor3d(z_color)

        if self._visible and self._actor:
            self._apply_style(self._actor)
            self._interactor.Render()
