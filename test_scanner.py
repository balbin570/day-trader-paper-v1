import unittest
from unittest.mock import patch
import scanner

class ScannerTests(unittest.TestCase):
    def test_breakout_watch(self):
        rows=[(i,100.0,100) for i in range(30)]
        rows[-1]=(30,102.0,200)
        with patch.object(scanner,"bars",return_value=rows):
            result=scanner.scan("TEST")
        self.assertEqual(result["signal"],"BREAKOUT_WATCH")
        self.assertEqual(result["volume_ratio"],2.0)

    def test_no_signal(self):
        rows=[(i,100.0,100) for i in range(30)]
        with patch.object(scanner,"bars",return_value=rows):
            result=scanner.scan("TEST")
        self.assertEqual(result["signal"],"NO_SIGNAL")

    def test_insufficient_data(self):
        with patch.object(scanner,"bars",return_value=[]):
            self.assertIsNone(scanner.scan("TEST"))

if __name__=="__main__":
    unittest.main()
