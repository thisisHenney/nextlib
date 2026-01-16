import unittest
from NextLib3.broadcaster.broadcaster import broadcaster


class TestBroadCaster(unittest.TestCase):
    def setUp(self):
        self.broadcaster = broadcaster

    def test_01_value(self):
        # self.broadcaster = broadcaster
        self.broadcaster.value.connect(self._on_received_value)
        self.broadcaster.value.emit(999)
        self.broadcaster.value.emit({'Dict':'test1'})

    def test_02_value(self):
        broadcaster.value.connect(self._on_received_value)
        broadcaster.value.emit(888)
        broadcaster.value.emit({'Dict': 'test2'})

    def test_03_compare(self):
        print(self.broadcaster == broadcaster)

    def _on_received_value(self, msg):
        print(msg)


# Test
if __name__ == '__main__':
    unittest.main()
