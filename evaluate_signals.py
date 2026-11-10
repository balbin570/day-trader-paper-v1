"""Evaluate saved breakout-watch signals after 30 and 60 minutes; paper only."""
import datetime as dt
import json
from pathlib import Path
from scanner import bars, UTC, NY

def evaluate(records, candles, now):
    valid = sorted((int(t),float(c)) for t,c,v in candles if c is not None and v is not None and v>0)
    for item in records:
        if item.get("signal") != "BREAKOUT_WATCH" or "timestamp_utc" not in item:
            continue
        t0 = int(dt.datetime.fromisoformat(item["timestamp_utc"]).timestamp())
        entry = item.get("last")
        if not entry or entry <= 0:
            continue
        for minutes in (30,60):
            key = f"return_{minutes}m_pct"
            if key in item:
                continue
            target = t0 + minutes*60
            if now.timestamp() < target+300:
                continue
            session = dt.datetime.fromtimestamp(t0,UTC).astimezone(NY).date()
            future = [(t,c) for t,c in valid if t >= target and
                      dt.datetime.fromtimestamp(t,UTC).astimezone(NY).date()==session and
                      dt.datetime.fromtimestamp(t,UTC).astimezone(NY).time()<dt.time(16,0)]
            if not future:
                continue
            t,close = future[0]
            if t > target+600:
                continue
            item[key] = round((close/entry-1)*100,3)
            item[f"price_{minutes}m"] = round(close,3)
            item[f"bar_{minutes}m_utc"] = dt.datetime.fromtimestamp(t,UTC).isoformat()
    return records

def main():
    history=Path("results/history")
    if not history.exists():
        print("No history yet")
        return
    now=dt.datetime.now(UTC)
    paths=list(history.glob("*/*.json"))
    changes=0
    symbols=set()
    for path in paths:
        payload=json.loads(path.read_text())
        for row in payload.get("signals",[]):
            if row.get("signal")=="BREAKOUT_WATCH" and (
                "return_30m_pct" not in row or "return_60m_pct" not in row):
                symbols.add(row["ticker"])
    candles={}
    for symbol in sorted(symbols):
        try: candles[symbol]=bars(symbol)
        except Exception as e: print(f"{symbol} evaluation data error: {e}")
    for path in paths:
        payload=json.loads(path.read_text())
        before=json.dumps(payload,sort_keys=True)
        for row in payload.get("signals",[]):
            if row.get("ticker") in candles:
                evaluate([row],candles[row["ticker"]],now)
        if json.dumps(payload,sort_keys=True)!=before:
            path.write_text(json.dumps(payload,indent=2)+"\n")
            changes+=1
    print(f"Evaluated signals; updated {changes} history files")
if __name__=="__main__": main()
