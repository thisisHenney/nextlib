# Main window Class
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._init_data()                           # 1. 데이터 및 상태 초기화 (가장 먼저!)
        self._create_widgets()              # 2. 위젯 생성 (데이터 참조 가능)
        self._setup_layouts()                   # 3. 레이아웃 설정
        self._bind_events()                     # 4. 시그널-슬롯 연결
        self._load_settings()                   # 5. 설정 파일 로드
        self._check_dependencies()      # 6. 외부 라이브러리 검증
        self._start_timers_and_threads()   # 7. 타이머/스레드 시작

    def _init_data(self):
        self.some_data = []
        self.model = MyModel()
