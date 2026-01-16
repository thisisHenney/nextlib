from global_data import first_data, second_data
from sub import SubClass

class MainClass:
    def __init__(self):
        super().__init__()

        self.first_data = first_data
        self.second_data = second_data

        print(id(self.first_data))
        print(id(self.second_data))
        
        sub = SubClass()

if __name__ == '__main__':
    main = MainClass()
