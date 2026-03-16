
class InstanceClass:
    _instance = None

    _count = 0

    def __init__(self):
        self._number = InstanceClass._count
        InstanceClass._count += 1


    def get_number(self):
        return self._number
