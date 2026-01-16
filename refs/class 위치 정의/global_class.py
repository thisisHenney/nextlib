# 전역 클래스 정의(기본)
# - 여러 파일에서 초기화하거나 선언해도 같은 클래스가 반환됨

class GlobalClass:
    _instance = None

    # Declare variables here

    
    # Declare functions here
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
