"""
VtkWidgetBase 기본 사용 예제

실행: python -m nextlib.vtk.example_base
"""
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QTabWidget
)

from nextlib.vtk import VtkWidgetBase, GeometrySource, MeshLoader
from nextlib.vtk.postprocess_widget import PostprocessWidget


class PreprocessTab(QWidget):
    """전처리 탭 - 기본 형상 조작"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)

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

        # Point Probe 도구
        self.btn_probe = QPushButton("Point Probe")
        self.btn_probe.setCheckable(True)
        self.btn_probe.clicked.connect(self._toggle_point_probe)
        sidebar.addWidget(self.btn_probe)

        btn_probe_reset = QPushButton("Probe 중심")
        btn_probe_reset.clicked.connect(self._reset_probe_to_origin)
        sidebar.addWidget(btn_probe_reset)

        sidebar.addStretch()

        # 형상 생성기 & 메쉬 로더
        self.geo = GeometrySource()
        self.loader = MeshLoader()

        # 객체 추가
        self._add_demo_objects()

        # 선택 변경 시그널 연결
        self.vtk_widget.selection_changed.connect(self._on_selection_changed)

        # Point Probe 도구 추가
        self.vtk_widget.add_tool("point_probe")

        probe = self.vtk_widget.get_tool("point_probe")
        if probe:
            probe.center_moved.connect(self._on_probe_center_moved)
            probe.visibility_changed.connect(self._on_probe_visibility_changed)

    def _add_demo_objects(self):
        """데모 객체 추가"""
        manager = self.vtk_widget.obj_manager

        cube = self.geo.cube(size=1.0, position=(-2, 0, 0))
        manager.add(cube, name="cube1", group="geometry")

        sphere = self.geo.sphere(radius=0.6, position=(0, 0, 0))
        manager.add(sphere, name="sphere1", group="geometry")

        cylinder = self.geo.cylinder(radius=0.4, height=1.5, position=(2, 0, 0))
        manager.add(cylinder, name="cylinder1", group="geometry")

        cone = self.geo.cone(radius=0.4, height=1.0, position=(-2, 2, 0))
        manager.add(cone, name="cone1", group="extra")

        plane = self.geo.plane(x_length=2.0, y_length=2.0, position=(0, 2, 0))
        manager.add(plane, name="plane1", group="extra")

        disk = self.geo.disk(inner_radius=0.2, outer_radius=0.5, position=(2, 2, 0))
        manager.add(disk, name="disk1", group="extra")

        self.vtk_widget.fit_to_scene()
        self._print_demo_info()

    def _print_demo_info(self):
        """데모 정보 출력"""
        print("\n" + "="*50)
        print("VtkWidgetBase Demo - Preprocess Tab")
        print("="*50)

        state = self.vtk_widget.state
        print(f"\n[초기 상태]")
        print(f"  객체 수: {state.object_count}")
        print(f"  그룹: {state.groups}")
        print(f"  뷰 스타일: {state.view_style}")

        print("\n[지원 메쉬 포맷]")
        print(f"  {MeshLoader.supported_formats()}")

        print("\n[조작 방법]")
        print("  - 좌클릭 드래그: 회전")
        print("  - Shift + 좌클릭: 패닝")
        print("  - Ctrl + 좌클릭: 줌")
        print("  - 휠: 줌")
        print("  - 더블클릭: 선택/해제 토글")
        print("  - Delete: 삭제")
        print("="*50 + "\n")

    def _print_state(self):
        """현재 상태 출력"""
        state = self.vtk_widget.state
        print("\n[현재 씬 상태]")
        print(f"  {state}")
        print(f"  객체: {state.object_names}")
        print(f"  선택: {state.selected_names} ({state.selected_count}개)")
        print(f"  그룹: {state.group_counts}")

        if state.has_selection:
            print("\n  [선택된 객체 상세]")
            for obj in state.selected_objects:
                print(f"    - {obj.name}: visible={obj.visible}, "
                      f"opacity={obj.opacity}, color={obj.color}")

    def _select_all(self):
        self.vtk_widget.all_objects().select()

    def _clear_selection(self):
        self.vtk_widget.obj_manager.clear_selection()

    def _hide_selected(self):
        self.vtk_widget.selected_objects().hide()

    def _show_all(self):
        self.vtk_widget.all_objects().show().opacity(1.0)

    def _set_style(self, style: str):
        self.vtk_widget.all_objects().style(style)

    def _show_geometry_only(self):
        self.vtk_widget.group("extra").hide()
        self.vtk_widget.group("geometry").show().color(100, 200, 255)

    def _toggle_point_probe(self, checked: bool):
        if checked:
            self.vtk_widget.show_tool("point_probe")
        else:
            self.vtk_widget.hide_tool("point_probe")

    def _on_probe_center_moved(self, x: float, y: float, z: float):
        print(f"[Probe] Center: ({x}, {y}, {z})")

    def _on_probe_visibility_changed(self, visible: bool):
        self.btn_probe.setChecked(visible)

    def _reset_probe_to_origin(self):
        probe = self.vtk_widget.get_tool("point_probe")
        if probe:
            probe.reset_to_origin()
            print(f"[Probe] Reset to center {probe.get_center()}")

    def _on_selection_changed(self, _info: dict):
        state = self.vtk_widget.state
        if state.has_selection:
            print(f"선택: {state.selected_names}")
        else:
            print("선택 해제")

    def cleanup(self):
        self.vtk_widget.cleanup()


class PostprocessTab(QWidget):
    """후처리 탭 - OpenFOAM 결과 시각화"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 후처리 위젯
        self.post_widget = PostprocessWidget(self)
        layout.addWidget(self.post_widget)

        # 시그널 연결
        self.post_widget.case_loaded.connect(self._on_case_loaded)
        self.post_widget.field_changed.connect(self._on_field_changed)

        print("\n" + "="*50)
        print("PostprocessWidget - Postprocess Tab")
        print("="*50)
        print("\n[사용법]")
        print("  1. 'Load .foam' 버튼으로 OpenFOAM 케이스 로드")
        print("  2. Field 콤보박스에서 시각화할 필드 선택")
        print("  3. Slice 체크박스로 슬라이스 모드 활성화")
        print("  4. Z 슬라이더로 슬라이스 위치 조정")
        print("="*50 + "\n")

    def _on_case_loaded(self, path: str):
        print(f"[Postprocess] Case loaded: {path}")

    def _on_field_changed(self, field: str):
        print(f"[Postprocess] Field changed: {field}")

    def cleanup(self):
        self.post_widget.cleanup()


class DemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("VTK Widget Demo")
        self.setGeometry(100, 100, 1200, 800)

        # 탭 위젯
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 전처리 탭
        self.preprocess_tab = PreprocessTab()
        self.tabs.addTab(self.preprocess_tab, "Preprocess")

        # 후처리 탭
        self.postprocess_tab = PostprocessTab()
        self.tabs.addTab(self.postprocess_tab, "Postprocess")

    def closeEvent(self, event):
        self.preprocess_tab.cleanup()
        self.postprocess_tab.cleanup()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = DemoWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
