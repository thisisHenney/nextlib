class VtkManager:
    def __init__(self):
        self._viewers = {}
        self._reverse = {}

    def register(self, name, viewer):
        self._viewers[name] = viewer
        self._reverse[viewer] = name

    def get(self, name: str):
        return self._viewers.get(name)

    def all(self):
        return self._viewers.values()

    def unregister(self, viewer):
        name = self._reverse.pop(viewer, None)
        if name:
            self._viewers.pop(name, None)

    def sync_cameras(self, master_name, target_names=None):
        master = self.get(master_name)
        if not master:
            return

        if target_names is None:
            targets = [v for k, v in self._viewers.items() if k != master_name]
        else:
            targets = [self.get(n) for n in target_names]

        master_cam = master.renderer.GetActiveCamera()

        for tgt in targets:
            if tgt:
                tgt.renderer.SetActiveCamera(master_cam)
                tgt.vtk_widget.GetRenderWindow().Render()

    def notify_camera_changed(self, viewer):
        viewer.camera_sync_lock = True
        master_cam = viewer.renderer.GetActiveCamera()

        dead = []

        for key, other in self._viewers.items():
            if other is viewer:
                continue

            other.camera_sync_lock = True
            other.renderer.SetActiveCamera(master_cam)

            rw = other.vtk_widget.GetRenderWindow()
            if rw is None or rw.GetMapped() == 0:
                dead.append(key)
                continue
            try:
                other.renderer.SetActiveCamera(master_cam)
                rw.Render()
            except RuntimeError:
                dead.append(key)
            other.camera_sync_lock = False

        for k in dead:
            self._viewers.pop(k, None)
        viewer.camera_sync_lock = False


vtk_manager = VtkManager()
