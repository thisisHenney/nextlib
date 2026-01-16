from __future__ import annotations

from pathlib import Path
import re

import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
)


# ------------------------------------------------------
# 공통: OpenFOAM 리스트 파일 파서 (points, faces, owner, neighbour)
# ------------------------------------------------------
def _find_count_and_start_index(lines):
    """
    OpenFOAM 리스트 파일에서
    - 개수(n) 있는 줄
    - 실제 데이터가 시작되는 '(' 다음 인덱스
    를 찾는다.
    """
    n = None
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s or s.startswith("//") or s.startswith("/*"):
            i += 1
            continue
        if s[0].isdigit() and "(" not in s and ")" not in s:
            try:
                n = int(s.split()[0])
                break
            except ValueError:
                pass
        i += 1

    if n is None:
        raise RuntimeError("count line not found")

    # '(' 나오는 줄까지 이동
    while i < len(lines) and "(" not in lines[i]:
        i += 1
    i += 1  # '(' 다음 줄부터 데이터 시작

    return n, i


def read_points(points_path: Path):
    with points_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    n_points, i = _find_count_and_start_index(lines)

    pts = []
    while i < len(lines) and len(pts) < n_points:
        s = lines[i].strip()
        if not s or s.startswith("//"):
            i += 1
            continue
        if s.startswith(")"):
            break

        m = re.search(r"\(([^)]+)\)", s)
        if m:
            nums = [float(x) for x in m.group(1).split()]
            if len(nums) == 3:
                pts.append(nums)
        i += 1

    return pts


def read_faces(faces_path: Path):
    with faces_path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    n_faces, i = _find_count_and_start_index(lines)

    faces = []
    while i < len(lines) and len(faces) < n_faces:
        s = lines[i].strip()
        if not s or s.startswith("//"):
            i += 1
            continue
        if s.startswith(")"):
            break

        m = re.match(r"(\d+)\s*\(([^)]+)\)", s)
        if m:
            n = int(m.group(1))
            idx = [int(x) for x in m.group(2).replace(",", " ").split()]
            if len(idx) == n:
                faces.append(idx)
        i += 1

    return faces


def read_int_list(path: Path):
    """owner, neighbour 같이 정수 리스트인 파일 읽기."""
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    n_vals, i = _find_count_and_start_index(lines)

    vals = []
    while i < len(lines) and len(vals) < n_vals:
        s = lines[i].strip()
        if not s or s.startswith("//"):
            i += 1
            continue
        if s.startswith(")"):
            break
        # 공백으로 구분된 정수들
        for tok in s.replace(";", " ").split():
            if tok[0] in "+-" or tok[0].isdigit():
                try:
                    vals.append(int(tok))
                except ValueError:
                    pass
        i += 1

    return vals


# ------------------------------------------------------
# polyMesh 디렉터리 찾기 (single + multi region)
# ------------------------------------------------------
def find_polymesh_dirs(case_dir: Path) -> list[Path]:
    result: list[Path] = []
    const = case_dir / "constant"
    if not const.exists():
        return result

    # single region
    pm = const / "polyMesh"
    if pm.exists():
        result.append(pm)

    # multi region
    for sub in const.iterdir():
        if sub.is_dir():
            pm = sub / "polyMesh"
            if pm.exists():
                result.append(pm)

    return result


# ------------------------------------------------------
# internal faces만 polydata로 구성
# ------------------------------------------------------
def build_internal_faces_polydata(poly_mesh_dir: Path) -> vtk.vtkPolyData:
    points_path = poly_mesh_dir / "points"
    faces_path = poly_mesh_dir / "faces"
    owner_path = poly_mesh_dir / "owner"
    neighbour_path = poly_mesh_dir / "neighbour"

    if not (points_path.exists() and faces_path.exists()
            and owner_path.exists() and neighbour_path.exists()):
        raise FileNotFoundError(f"polyMesh 4개 파일(pts,faces,owner,neighbour) 중 일부가 없습니다: {poly_mesh_dir}")

    pts_list = read_points(points_path)
    faces = read_faces(faces_path)
    owner = read_int_list(owner_path)
    neighbour = read_int_list(neighbour_path)

    n_faces = len(faces)
    n_owner = len(owner)
    n_internal = len(neighbour)  # 내부 face 개수

    print(f"  [polyMesh={poly_mesh_dir.name}] points={len(pts_list)}, faces={n_faces}, "
          f"owner={n_owner}, neighbour={n_internal}")

    vtk_points = vtk.vtkPoints()
    for x, y, z in pts_list:
        vtk_points.InsertNextPoint(x, y, z)

    polys = vtk.vtkCellArray()

    # 내부 face는 index < n_internal
    for fi in range(min(n_internal, n_faces)):
        face = faces[fi]
        n = len(face)
        polys.InsertNextCell(n)
        for pid in face:
            polys.InsertCellPoint(pid)

    poly = vtk.vtkPolyData()
    poly.SetPoints(vtk_points)
    poly.SetPolys(polys)
    poly.BuildCells()

    return poly


# ------------------------------------------------------
# 카메라 강제 보정
# ------------------------------------------------------
def force_reset_camera(renderer: vtk.vtkRenderer, poly: vtk.vtkPolyData):
    bounds = poly.GetBounds()
    xmin, xmax, ymin, ymax, zmin, zmax = bounds

    cx = 0.5 * (xmin + xmax)
    cy = 0.5 * (ymin + ymax)
    cz = 0.5 * (zmin + zmax)

    dx = xmax - xmin
    dy = ymax - ymin
    dz = zmax - zmin
    dmax = max(dx, dy, dz, 1e-6)

    cam = renderer.GetActiveCamera()
    cam.SetFocalPoint(cx, cy, cz)
    cam.SetPosition(cx, cy, cz + dmax * 2.0)  # Z+에서 내려다보기
    cam.SetViewUp(0, 1, 0)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(dmax * 0.6)

    renderer.ResetCameraClippingRange()


# ------------------------------------------------------
# Viewer
# ------------------------------------------------------
class FoamInternalSliceViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)

        # 버튼
        row = QHBoxLayout()
        btn = QPushButton("OpenFOAM 케이스 불러오기")
        btn.clicked.connect(self.open_case_folder)
        row.addWidget(btn)
        main_layout.addLayout(row)

        # VTK 위젯
        self.vtk_widget = QVTKRenderWindowInteractor(self)
        main_layout.addWidget(self.vtk_widget)

        self.renderer = vtk.vtkRenderer()
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        self.interactor = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.interactor.Initialize()

        # 배경 (요청값)
        self.renderer.SetBackground2(0.40, 0.40, 0.50)  # Up
        self.renderer.SetBackground(0.65, 0.65, 0.70)   # Down
        self.renderer.GradientBackgroundOn()

    # --------------------------
    def open_case_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "OpenFOAM 케이스 선택")
        if folder:
            self.load_case(Path(folder))

    # --------------------------
    def load_case(self, case_dir: Path):
        print(f"\n[INFO] case: {case_dir}")
        pm_dirs = find_polymesh_dirs(case_dir)
        if not pm_dirs:
            print("[ERROR] polyMesh 디렉터리를 찾지 못했습니다.")
            return

        append = vtk.vtkAppendPolyData()

        for pm in pm_dirs:
            try:
                internal_poly = build_internal_faces_polydata(pm)
                print(f"    internal faces poly: pts={internal_poly.GetNumberOfPoints()}, "
                      f"cells={internal_poly.GetNumberOfCells()}")
                append.AddInputData(internal_poly)
            except Exception as e:
                print(f"[WARN] {pm}: {e}")

        append.Update()
        merged_internal = append.GetOutput()

        if merged_internal.GetNumberOfCells() == 0:
            print("[ERROR] internal faces가 하나도 없습니다.")
            return

        print("[INFO] merged internal faces: pts=", merged_internal.GetNumberOfPoints(),
              "cells=", merged_internal.GetNumberOfCells())
        print("[INFO] bounds:", merged_internal.GetBounds())

        # ---- 형상 중심 Z-normal 슬라이스 ----
        xmin, xmax, ymin, ymax, zmin, zmax = merged_internal.GetBounds()
        zcenter = 0.5 * (zmin + zmax)
        print("[INFO] slice z-center:", zcenter)

        plane = vtk.vtkPlane()
        plane.SetOrigin(0.0, 0.0, zcenter)
        plane.SetNormal(0.0, 0.0, 1.0)  # Z-normal

        cutter = vtk.vtkCutter()
        cutter.SetCutFunction(plane)
        cutter.SetInputData(merged_internal)
        cutter.Update()

        slice_poly = cutter.GetOutput()
        print("[INFO] slice points:", slice_poly.GetNumberOfPoints(),
              "cells:", slice_poly.GetNumberOfCells())

        # 교차선만 추출
        edges = vtk.vtkExtractEdges()
        edges.SetInputData(slice_poly)
        edges.Update()
        edge_poly = edges.GetOutput()

        print("[INFO] edge lines:", edge_poly.GetNumberOfCells())

        # ---- Mapper / Actor ----
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(edge_poly)
        mapper.ScalarVisibilityOff()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        prop = actor.GetProperty()
        prop.SetColor(0.0, 0.0, 1.0)   # 내부 격자선 색
        prop.SetLineWidth(1.0)

        # 화면 갱신
        self.renderer.RemoveAllViewProps()
        self.renderer.AddActor(actor)

        # 카메라 맞추기
        force_reset_camera(self.renderer, edge_poly)

        # 축 표시
        axes = vtk.vtkAxesActor()
        axes.SetTotalLength(0.1, 0.1, 0.1)
        om = vtk.vtkOrientationMarkerWidget()
        om.SetOrientationMarker(axes)
        om.SetInteractor(self.interactor)
        om.SetEnabled(True)
        om.InteractiveOn()

        self.vtk_widget.GetRenderWindow().Render()


# ------------------------------------------------------
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = FoamInternalSliceViewer()
    w.resize(1400, 800)
    w.show()
    sys.exit(app.exec())
