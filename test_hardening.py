import copy
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import scanner
from market_data import UTC, NY, session_bounds, market_open, valid_candles
from evaluate_signals import evaluate
from storage import deduplicate, write_json
from test_scanner import sample, NOW

class CalendarTests(unittest.TestCase):
    def test_holiday_weekend_and_exceptional_close(self):
        for date in ('2026-11-26', '2026-11-07', '2025-01-09'):
            self.assertIsNone(session_bounds(dt.date.fromisoformat(date)))
    def test_early_close(self):
        bounds = session_bounds(dt.date(2026,11,27))
        self.assertEqual(bounds[1].astimezone(NY).hour, 13)
        self.assertFalse(market_open(bounds[1]))
        self.assertEqual(valid_candles([(int(bounds[1].timestamp()),100,10)],bounds[1]+dt.timedelta(hours=1)), [])
    def test_dst(self):
        self.assertEqual(session_bounds(dt.date(2026,3,6))[0].hour,14)
        self.assertEqual(session_bounds(dt.date(2026,3,9))[0].hour,13)
        self.assertEqual(session_bounds(dt.date(2026,11,2))[0].hour,14)
    def test_closed_does_not_fetch(self):
        with patch.object(scanner,'bars') as fetch:
            self.assertEqual(scanner.scan('TEST',dt.datetime(2026,11,26,17,tzinfo=UTC))['signal'],'MARKET_CLOSED')
            fetch.assert_not_called()

class DataTests(unittest.TestCase):
    def test_bad_rows_conflicts_and_order(self):
        rows = sample()
        t = rows[-1][0]
        bad = [(t,float('nan'),100),(t,-1,10),(t,100,0),(t,100,float('inf')),(t+1,100,10),(True,100,10)]
        self.assertEqual(valid_candles(rows[::-1]+bad+rows,NOW), valid_candles(rows,NOW))
        self.assertEqual(len(valid_candles(rows+[(t,999,100)],NOW)),29)
    def test_incomplete_and_future(self):
        t = int(NOW.timestamp())
        self.assertEqual(valid_candles([(t,100,10),(t+300,101,10)],NOW),[])
    def test_gap_rejects_signal(self):
        rows = sample(); del rows[-5]
        with patch.object(scanner,'bars',return_value=rows):
            self.assertEqual(scanner.scan('TEST',NOW)['signal'],'DATA_UNAVAILABLE')
    def test_yahoo_bad_shape_and_ohlc(self):
        quote = {'open':[100], 'high':[99], 'low':[98], 'close':[101], 'volume':[10]}
        data = {'chart':{'result':[{'timestamp':[1],'indicators':{'quote':[quote]}}]}}
        response = MagicMock(); response.__enter__.return_value = response
        with patch('scanner.urllib.request.urlopen',return_value=response), patch('scanner.json.load',return_value=data):
            self.assertEqual(scanner.bars('TEST'),[])
            quote['volume'] = []
            with self.assertRaises(ValueError): scanner.bars('TEST')
    def test_dedup_survives_restart(self):
        row = {'ticker':'TEST','signal':'BREAKOUT_WATCH','strategy_id':'breakout_v2','timestamp_utc':NOW.isoformat()}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            first = copy.deepcopy(row); deduplicate([first],root)
            write_json(root/'2026-11-09'/'one.json',{'signals':[first]})
            again = copy.deepcopy(row); deduplicate([again],root)
            self.assertEqual(again['signal'],'DUPLICATE_SIGNAL')
            self.assertEqual(first['signal_id'],again['signal_id'])
            self.assertEqual(json.loads((root/'2026-11-09'/'one.json').read_text())['signals'][0],first)

class EvaluationTests(unittest.TestCase):
    def record(self,observed=NOW):
        return {'signal':'BREAKOUT_WATCH','strategy_id':'breakout_v2','last':100,'timestamp_utc':(observed-dt.timedelta(minutes=7)).isoformat(),'observed_at_utc':observed.isoformat()}
    def test_horizons_cost_and_idempotency(self):
        row=self.record()
        candles=[(int(NOW.timestamp())+(m-5)*60,101,10) for m in (30,60,120)]
        evaluate([row],candles,NOW+dt.timedelta(minutes=120))
        for m in (30,60,120):
            self.assertEqual(row[f'return_{m}m_pct'],1)
            self.assertEqual(row[f'net_return_{m}m_pct'],.8)
        before=copy.deepcopy(row)
        evaluate([row],[],NOW+dt.timedelta(hours=3))
        self.assertEqual(row,before)
    def test_future_close_never_used(self):
        row=self.record()
        t=int(NOW.timestamp())+30*60
        evaluate([row],[(t,999,10)],NOW+dt.timedelta(minutes=31))
        self.assertNotIn('return_30m_pct',row)
    def test_observation_time_and_missing_target(self):
        row=self.record()
        evaluate([row],[(int(NOW.timestamp())+20*60,999,10)],NOW+dt.timedelta(hours=1))
        self.assertNotIn('return_30m_pct',row)
    def test_no_overnight_and_legacy_unchanged(self):
        observed=NOW.replace(hour=20,minute=45)
        row=self.record(observed)
        evaluate([row],[],observed+dt.timedelta(hours=3))
        self.assertEqual(row['status_30m'],'OUTSIDE_SESSION')
        legacy={'signal':'BREAKOUT_WATCH','last':100,'timestamp_utc':NOW.isoformat(),'return_30m_pct':.198}
        before=copy.deepcopy(legacy)
        evaluate([legacy],sample(),NOW)
        self.assertEqual(legacy,before)

if __name__ == '__main__': unittest.main()
