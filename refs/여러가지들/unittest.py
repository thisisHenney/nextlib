
import unittest

class MyUnitTest(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ...
    
    @classmethod
    def setUpClass(cls):
        print('setUpClass')

    @classmethod
    def tearDownClass(cls):
        print("tearDownClass")

    def setUp(self):
        print('setUp')
        
        self.value = 0
        self.is_started = False

    def tearDown(self):
        print('tearDown')
    
    def test_01(self):
        print(test_01)

    def test_02(self):
        print(test_02)

    def test_03(self):
        print(test_03)

if __name__ == '__main__':
    unittest.main()







