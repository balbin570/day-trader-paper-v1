"""Validated completed five-minute XNYS candles; fail closed on unknown dates."""
import datetime as dt
import math
from functools import lru_cache
from zoneinfo import ZoneInfo
import exchange_calendars as xcals

UTC = dt.timezone.utc
NY = ZoneInfo('America/New_York')

@lru_cache(maxsize=16)
def session_bounds(date):
    calendar = xcals.get_calendar('XNYS', start=f'{date.year-1}-01-01', end=f'{date.year+1}-12-31')
    label = date.isoformat()
    if not calendar.is_session(label):
        return None
    return (calendar.session_open(label).to_pydatetime(),
            calendar.session_close(label).to_pydatetime())

def market_open(now):
    bounds = session_bounds(now.astimezone(NY).date())
    return bool(bounds and bounds[0] <= now < bounds[1])

def valid_candles(rows, now):
    if now.tzinfo is None:
        raise ValueError('Timezone-aware now required')
    accepted = {}
    conflicts = set()
    for row in rows:
        try:
            t, c, v = row
            if any(isinstance(x, bool) for x in row):
                continue
            if not all(isinstance(x, (int, float)) and math.isfinite(x) for x in row):
                continue
            if t != int(t) or c <= 0 or v <= 0:
                continue
            t = int(t)
            start = dt.datetime.fromtimestamp(t, UTC)
            bounds = session_bounds(start.astimezone(NY).date())
            if not bounds or not (bounds[0] <= start and start + dt.timedelta(minutes=5) <= bounds[1]):
                continue
            if (t-int(bounds[0].timestamp())) % 300 or t+300 > now.timestamp():
                continue
            candle = (t, float(c), float(v))
            if t in accepted and accepted[t] != candle:
                conflicts.add(t)
            accepted[t] = candle
        except (TypeError, ValueError, OverflowError, OSError):
            continue
    return [accepted[t] for t in sorted(accepted) if t not in conflicts]
