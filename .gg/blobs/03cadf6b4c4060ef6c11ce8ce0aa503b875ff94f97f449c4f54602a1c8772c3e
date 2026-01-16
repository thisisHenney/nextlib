# unittest는 같은 클래스 내 여러개 메서드가 존재하면 테스트 신뢰성이 떨어지기 때문에
#   같은 변수 또는 함수를 공유하지 말고, 메서드들이 독립적으로 실행되게 해야함

import unittest

class MyUnitTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # 반드시 부모 생성자 호출!
        ...
    
    # 사전 정의 클래스 메서드
    @classmethod
    def setUpClass(cls):    # unittest 클래스에서 최초 한 번만 실행
        print('setUpClass')

    @classmethod            # unittest 클래스에서 마지막에 한 번만 실행
    def tearDownClass(cls):
        print("tearDownClass")

    # 아래 함수는 각 test_*** 메서드들마다 실행됨
    def setUp(self):        # 각 테스트 메서드 실행 직전마다 실행
        print('setUp')
        
        self.value = 0
        self.is_started = False

    def tearDown(self):     # 각 테스트 메서드의 실행 완료 후 실행
        print('tearDown')
    
    # 테스트할 함수들
    def test_01(self):
        print(test_01)

    def test_02(self):
        print(test_02)

    def test_03(self):
        print(test_03)

# Test
if __name__ == '__main__':
    unittest.main()


# 클래스명은 사용자에 맞게 설정가능함
# def __init__(self) 함수는 사용하기 불편하므로 다른 이름으로
# class 내 실행되는 여러 test_*** 함수들이 있을 때, 함수 이름의 알파벳 순서로 실행됨





