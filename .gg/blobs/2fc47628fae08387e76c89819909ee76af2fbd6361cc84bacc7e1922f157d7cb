# 객체 클래스 정의(기본)
# - 여러 파일에서 초기화하거나 선언하면 새로 클래스가 생성됨

class InstanceClass:
    _instance = None

    # Declare variables here
    _count = 0

    def __init__(self):
        self._number = InstanceClass._count     # cls가 아닌 클래스명으로 적어야함
        InstanceClass._count += 1


    def get_number(self):
        return self._number
