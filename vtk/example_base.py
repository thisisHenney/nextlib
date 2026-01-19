"""
VtkWidgetBase 기본 사용 예제

실행: python -m nextlib.vtk.example_base
"""
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

from nextlib.vtk import VtkWidgetBase, GeometrySource, MeshLoader


class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VtkWidgetBase Demo")
        self.setGeometry(100, 100, 1200, 800)

        # 메인 위젯
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # VTK 위젯 생성
        self.vtk_widget = VtkWidgetBase(self)
        layout.addWidget(self.vtk_widget, stretch=1)

        # 사이드바 버튼들
        sidebar = QVBoxLayout()
        layout.addLayout(sidebar)

        btn_state = QPushButton("상태 출력")
        btn_state.clicked.connect(self._print_state)
        sidebar.addWidget(btn_state)

        btn_select_all = QPushButton("전체 선택")
        btn_select_all.clicked.connect(self._select_all)
        sidebar.addWidget(btn_select_all)

        btn_clear = QPushButton("선택 해제")
        btn_clear.clicked.connect(self._clear_selection)
        sidebar.addWidget(btn_clear)

        btn_hide_selected = QPushButton("선택 숨김")
        btn_hide_selected.clicked.connect(self._hide_selected)
        sidebar.addWidget(btn_hide_selected)

        btn_show_all = QPushButton("전체 표시")
        btn_show_all.clicked.connect(self._show_all)
        sidebar.addWidget(btn_show_all)

        btn_wireframe = QPushButton("Wireframe")
        btn_wireframe.clicked.connect(lambda: self._set_style("wireframe"))
        sidebar.addWidget(btn_wireframe)

        btn_surface = QPushButton("Surface")
        btn_surface.clicked.connect(lambda: self._set_style("surface with edge"))
        sidebar.addWidget(btn_surface)

        btn_group_geometry = QPushButton("geometry 그룹만")
        btn_group_geometry.clicked.connect(self._show_geometry_only)
        sidebar.addWidget(btn_group_geometry)

        sidebar.addStretch()

        # 형상 생성기 & 메쉬 로더
        self.geo = GeometrySource()
        self.loader = MeshLoader()

        # 객체 추가
        self._add_demo_objects()

        # 선택 변경 시그널 연결
        self.vtk_widget.selection_changed.connect(self._on_selection_changed)

    def _add_demo_objects(self):
        """데모 객체 추가"""
        manager = self.vtk_widget.obj_manager

        # GeometrySource를 사용하여 형상 생성
        cube = self.geo.cube(size=1.0, position=(-2, 0, 0))
        manager.add(cube, name="cube1", group="geometry")

        sphere = self.geo.sphere(radius=0.6, position=(0, 0, 0))
        manager.add(sphere, name="sphere1", group="geometry")

        cylinder = self.geo.cylinder(radius=0.4, height=1.5, position=(2, 0, 0))
        manager.add(cylinder, name="cylinder1", group="geometry")

        # 추가 형상들
        cone = self.geo.cone(radius=0.4, height=1.0, position=(-2, 2, 0))
        manager.add(cone, name="cone1", group="extra")

        plane = self.geo.plane(x_length=2.0, y_length=2.0, position=(0, 2, 0))
        manager.add(plane, name="plane1", group="extra")

        disk = self.geo.disk(inner_radius=0.2, outer_radius=0.5, position=(2, 2, 0))
        manager.add(disk, name="disk1", group="extra")

        # 씬에 맞춤
        self.vtk_widget.fit_to_scene()

        self._print_demo_info()

    def _print_demo_info(self):
        """데모 정보 출력"""
        print("\n" + "="*50)
        print("VtkWidgetBase Demo")
        print("="*50)

        # state를 사용하여 상태 출력
        state = self.vtk_widget.state
        print(f"\n[초기 상태]")
        print(f"  객체 수: {state.object_count}")
        print(f"  그룹: {state.groups}")
        print(f"  그룹별 객체 수: {state.group_counts}")
        print(f"  뷰 스타일: {state.view_style}")
        print(f"  투영 모드: {state.projection_mode}")

        print("\n[지원 메쉬 포맷]")
        print(f"  {MeshLoader.supported_formats()}")

        print("\n[조작 방법]")
        print("  - 좌클릭 드래그: 회전")
        print("  - Shift + 좌클릭: 패닝")
        print("  - Ctrl + 좌클릭: 줌")
        print("  - 휠: 줌")
        print("  - 더블클릭: 포커스")
        print("  - Ctrl + 클릭: 선택 토글")
        print("  - Delete: 삭제")
        print("="*50 + "\n")

    def _print_state(self):
        """현재 상태 출력"""
        state = self.vtk_widget.state

        print("\n[현재 씬 상태]")
        print(f"  {state}")  # SceneState(objects=6, selected=0, ...)
        print(f"  객체: {state.object_names}")
        print(f"  선택: {state.selected_names} ({state.selected_count}개)")
        print(f"  그룹: {state.group_counts}")
        print(f"  바운딩박스: center={state.center}")
        print(f"  뷰: {state.view_style}, {state.projection_mode}")
        print(f"  축: {state.axes_visible}, 눈금자: {state.ruler_visible}")

        # 선택된 객체 상세 정보
        if state.has_selection:
            print("\n  [선택된 객체 상세]")
            for obj in state.selected_objects:
                print(f"    - {obj.name}: visible={obj.visible}, "
                      f"opacity={obj.opacity}, color={obj.color}")

    def _select_all(self):
        """전체 선택"""
        self.vtk_widget.all_objects().select()

    def _clear_selection(self):
        """선택 해제"""
        self.vtk_widget.obj_manager.clear_selection()

    def _hide_selected(self):
        """선택된 객체 숨김"""
        self.vtk_widget.selected_objects().hide()

    def _show_all(self):
        """전체 표시"""
        self.vtk_widget.all_objects().show().opacity(1.0)

    def _set_style(self, style: str):
        """스타일 변경"""
        self.vtk_widget.all_objects().style(style)

    def _show_geometry_only(self):
        """geometry 그룹만 표시"""
        # extra 그룹 숨기기
        self.vtk_widget.group("extra").hide()
        # geometry 그룹 표시
        self.vtk_widget.group("geometry").show().color(100, 200, 255)

    def _on_selection_changed(self, info: dict):
        """선택 변경 이벤트 - state 사용"""
        state = self.vtk_widget.state
        if state.has_selection:
            print(f"선택: {state.selected_names}")
        else:
            print("선택 해제")

    def closeEvent(self, event):
        self.vtk_widget.cleanup()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
