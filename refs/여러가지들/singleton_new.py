# Singleton 클래스 선언
# singleton_test.py
class Singleton:
    def __init__(self):
        self.value = 1

    def add_value(self, name):
        print(name)

    def remove_value(self, index):
        print(index)

# Run
singleton = Singleton()
singleton.add_value('temp')
print(a.temp)
singleton.remove_value(12)



# Other.py
from singleton_test import singleton

print(singleton.value)  # 1

