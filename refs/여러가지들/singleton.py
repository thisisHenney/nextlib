# 기본적인 Singleton 클래스 선언
class Singleton:
    _instance = None  # 클래스 변수로 인스턴스 저장

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True


# 인스턴스 변수를 동적으로 추가하거나 삭제할 수 있는 클래스
class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True

    def add_value(self, name, value):
        setattr(self, name, value)

    def remove_value(self, name):
        if hasattr(self, name):
            delattr(self, name)

# Run
a = Singleton()
a.add_value('temp', 42)
print(a.temp)  # 42

a.remove_value('temp')
print(hasattr(a, 'temp'))  # False


