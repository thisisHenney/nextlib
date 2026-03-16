class Singleton:
    def __init__(self):
        self.value = 1

    def add_value(self, name):
        print(name)

    def remove_value(self, index):
        print(index)

singleton = Singleton()
singleton.add_value('temp')
print(a.temp)
singleton.remove_value(12)



from singleton_test import singleton

print(singleton.value)

