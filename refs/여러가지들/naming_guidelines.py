class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._init_data()
        self._create_widgets()
        self._setup_layouts()
        self._bind_events()
        self._load_settings()
        self._check_dependencies()
        self._start_timers_and_threads()

    def _init_data(self):
        self.some_data = []
        self.model = MyModel()
