"""Forward observation returns, never fills or trading P&L. Legacy files untouched."""
import datetime as dt
import json
import math
from pathlib import Path
from scanner import bars
from market_data import UTC, NY, valid_candles, session_bounds
from storage import write_json

HORIZONS = (30, 60, 120)
# Illustrative round trip: 5 bps commission/fees + 5 bps slippage each side.
ROUND_TRIP_COST_BPS = 20

def evaluate(records, candles, now):
    valid = valid_candles(candles, now)
    for item in records:
        if item.get('signal') != 'BREAKOUT_WATCH' or item.get('strategy_id') != 'breakout_v2':
            continue
        entry = item.get('last')
        if not isinstance(entry, (int, float)) or not math.isfinite(entry) or entry <= 0:
            continue
        # Actual scan observation is the earliest time the signal was known.
        observed = dt.datetime.fromisoformat(item['observed_at_utc'])
        if observed.tzinfo is None:
            raise ValueError('Timezone-aware observation required')
        bounds = session_bounds(observed.astimezone(NY).date())
        if not bounds or not bounds[0] <= observed < bounds[1]:
            continue
        for minutes in HORIZONS:
            key = f'return_{minutes}m_pct'
            if key in item:
                continue
            target = observed + dt.timedelta(minutes=minutes)
            if target > bounds[1]:
                item[f'status_{minutes}m'] = 'OUTSIDE_SESSION'
                continue
            if now < target:
                continue
            # Close timestamp, not candle start: no incomplete/future prices.
            future = [(t,c) for t,c,v in valid
                      if target.timestamp() <= t+300 <= min(now.timestamp(), bounds[1].timestamp())
                      and t+300 <= target.timestamp()+300 and t >= bounds[0].timestamp()]
            if not future:
                item[f'status_{minutes}m'] = 'MISSING_DATA'
                continue
            t, close = future[0]
            gross = (close/entry-1)*100
            item[key] = round(gross, 6)
            item[f'net_return_{minutes}m_pct'] = round(gross-ROUND_TRIP_COST_BPS/100, 6)
            item[f'price_{minutes}m'] = close
            item[f'bar_{minutes}m_utc'] = dt.datetime.fromtimestamp(t,UTC).isoformat()
            item[f'price_time_{minutes}m_utc'] = dt.datetime.fromtimestamp(t+300,UTC).isoformat()
            item[f'status_{minutes}m'] = 'EVALUATED'
            item['round_trip_cost_bps'] = ROUND_TRIP_COST_BPS
    return records

def main():
    history = Path('results/v2/history')
    paths = sorted(history.glob('*/*.json'))
    now = dt.datetime.now(UTC)
    payloads = [(path, json.loads(path.read_text())) for path in paths]
    symbols = {row['ticker'] for _,payload in payloads for row in payload.get('signals', [])
               if row.get('signal') == 'BREAKOUT_WATCH'
               and any(f'return_{m}m_pct' not in row and row.get(f'status_{m}m') != 'OUTSIDE_SESSION' for m in HORIZONS)
               and now-dt.datetime.fromisoformat(row['observed_at_utc']) < dt.timedelta(days=5)}
    candles = {}
    errors = []
    for symbol in sorted(symbols):
        try:
            candles[symbol] = bars(symbol)
        except Exception:
            errors.append({'ticker':symbol, 'error':'evaluation feed unavailable'})
    changes = 0
    for path, payload in payloads:
        before = json.dumps(payload, sort_keys=True)
        for row in payload.get('signals', []):
            if row.get('ticker') in candles:
                evaluate([row], candles[row['ticker']], now)
        if json.dumps(payload, sort_keys=True) != before:
            write_json(path, payload)
            changes += 1
    write_json(Path('results/v2/evaluation_status.json'), {'generated_at_utc':now.isoformat(), 'errors':errors})
    print(f'Evaluated v2 observations; updated {changes} history files; feed errors: {len(errors)}')
    if errors:
        raise SystemExit('Evaluation feed unavailable; see evaluation_status.json')

if __name__ == '__main__':
    main()
