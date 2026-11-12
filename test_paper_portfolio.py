import datetime as dt
import unittest
from paper_portfolio import initial, advance
from market_data import UTC
class PortfolioTests(unittest.TestCase):
    def test_forward_entry_and_no_duplicate(self):
        now=dt.datetime(2026,11,12,16,0,tzinfo=UTC)
        s=initial(now)
        row=dict(ticker="TSLA",signal="BREAKOUT_WATCH",signal_id="x",observed_at_utc=now.isoformat())
        advance(s,[row],{},now)
        self.assertEqual(len(s["pending"]),1)
        later=now+dt.timedelta(minutes=6)
        feed={"TSLA":[(int(now.timestamp()),100,1000)]}
        advance(s,[row],feed,later)
        self.assertEqual(len(s["positions"]),1)
        cash=s["cash"]
        advance(s,[row],feed,later)
        self.assertEqual(s["cash"],cash)
        self.assertFalse(s["orders"])
        end=later+dt.timedelta(minutes=5)
        advance(s,[],{"TSLA":[(int((end-dt.timedelta(minutes=5)).timestamp()),98,1000)]},end)
        self.assertEqual(len(s["positions"]),0)
        self.assertLess(s["realized_pnl"],0)
    def test_old_signal_ignored(self):
        now=dt.datetime(2026,11,12,16,0,tzinfo=UTC)
        s=initial(now)
        advance(s,[dict(ticker="TSLA",signal="BREAKOUT_WATCH",signal_id="old",observed_at_utc=(now-dt.timedelta(minutes=1)).isoformat())],{},now)
        self.assertFalse(s["pending"])
