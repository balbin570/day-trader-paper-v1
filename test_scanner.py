import datetime as dt
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import scanner

NY=ZoneInfo("America/New_York")
START=dt.datetime(2026,11,9,9,30,tzinfo=NY).timestamp()
NOW=dt.datetime(2026,11,9,12,0,tzinfo=NY).astimezone(dt.timezone.utc)

def sample(last_close=102,last_volume=200):
    rows=[(int(START)+i*300,100.0,100) for i in range(30)]
    rows[-1]=(int(START)+29*300,last_close,last_volume)
    return rows

class ScannerTests(unittest.TestCase):
    def test_breakout(self):
        with patch.object(scanner,"bars",return_value=sample()):
            result=scanner.scan("TEST",NOW)
        self.assertEqual(result["signal"],"BREAKOUT_WATCH")
        self.assertEqual(result["volume_ratio"],2)
    def test_no_signal(self):
        with patch.object(scanner,"bars",return_value=sample(100)):
            self.assertEqual(scanner.scan("TEST",NOW)["signal"],"NO_SIGNAL")
    def test_zero_volume_bar_ignored(self):
        rows=sample()
        rows[-1]=(rows[-1][0],102,0)
        with patch.object(scanner,"bars",return_value=rows):
            self.assertEqual(scanner.scan("TEST",NOW)["signal"],"NO_SIGNAL")
    def test_insufficient(self):
        with patch.object(scanner,"bars",return_value=[]):
            self.assertEqual(scanner.scan("TEST",NOW)["signal"],"DATA_UNAVAILABLE")
    def test_stale(self):
        late=NOW+dt.timedelta(hours=5)
        with patch.object(scanner,"bars",return_value=sample()):
            self.assertEqual(scanner.scan("TEST",late)["signal"],"STALE_DATA")
if __name__=="__main__":
    unittest.main()
