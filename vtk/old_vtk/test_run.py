from PySide6.QtWidgets import QApplication
from nextlib.vtk.vtk_widget import VtkWidget
from nextlib.vtk.vtk_manager import vtk_manager

from nextlib.vtk.sources.geometry_source import GeometrySource
from nextlib.vtk.sources.mesh_loader import MeshLoader

if __name__ == "__main__":
    app = QApplication([])

    vtk1 = VtkWidget(registry=vtk_manager)
    vtk2 = VtkWidget(registry=vtk_manager)

    vtk1.set_defaults()
    vtk1.camera.setup_camera_sync()

    vtk_manager.register("pre", vtk1)
    vtk_manager.register("post", vtk2)

    vtk1.setWindowTitle("VTK Widget_1")
    vtk1.resize(1000, 700)
    vtk1.show()

    # vtk2.setWindowTitle("VTK Widget_2")
    # vtk2.resize(600, 400)
    # vtk2.show()

    actor = GeometrySource().make_cube()
    obj_id = vtk1.obj_manager.add(actor)
    vtk1.fit_to_scene()


    def on_box_center(x, y, z):
        print("box center:", x, y, z)

    # vtk_manager.sync_cameras("pre")

    path = rf"D:\resources\stl"
    names = ["ccNimonic.stl", "copperRing.stl", "header.stl"]
    # names = ["dumbbell.stl"]
    for n in names:
        file_path = rf"{path}\{n}"
        actors = MeshLoader().load_stl(file_path, True)
        for act in actors:
            vtk1.obj_manager.add(act, group=0)
    result = vtk1.obj_manager.get_all_objects()
    print(result)

    vtk1.obj_manager.apply("opacity", 0.5, obj_id=0)
    vtk1.fit_to_scene()
    app.exec()
