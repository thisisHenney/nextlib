class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True


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

a = Singleton()
a.add_value('temp', 42)
print(a.temp)

a.remove_value('temp')
print(hasattr(a, 'temp'))


