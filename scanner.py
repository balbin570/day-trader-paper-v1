"""US equity paper scanner. No broker or order execution."""
import datetime as dt
import json
import urllib.request
from pathlib import Path
from market_data import NY, UTC, valid_candles, market_open, session_bounds
from storage import write_json, deduplicate

SYMBOLS = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","AVGO","PLTR","SPY","QQQ"]

def bars(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
    request = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    if data.get("chart", {}).get("error"):
        raise ValueError("Yahoo chart API returned an error")
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    timestamps = result["timestamp"]
    columns = [quote[name] for name in ("open", "high", "low", "close", "volume")]
    if any(len(column) != len(timestamps) for column in columns):
        raise ValueError("Yahoo candle arrays have inconsistent lengths")
    import math
    rows = []
    for t, o, h, l, c, v in zip(timestamps, *columns):
        values = (o, h, l, c, v)
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in values):
            continue
        if min(o, h, l, c) <= 0 or v <= 0 or not (l <= min(o,c) <= max(o,c) <= h):
            continue
        rows.append((t, c, v))
    return rows

def scan(symbol, now=None):
    now = now or dt.datetime.now(UTC)
    if not market_open(now):
        return {"ticker":symbol,"signal":"MARKET_CLOSED"}
    raw = bars(symbol)
    valid = [(t,c,v,dt.datetime.fromtimestamp(t,UTC).astimezone(NY).date().isoformat())
             for t,c,v in valid_candles(raw, now)]
    if not valid:
        return {"ticker":symbol,"signal":"DATA_UNAVAILABLE","reason":"no completed positive-volume regular-session bars"}
    session = now.astimezone(NY).date().isoformat()
    today = [x for x in valid if x[3] == session]
    if len(today) < 21:
        warmup = now < session_bounds(now.astimezone(NY).date())[0] + dt.timedelta(minutes=105)
        return {"ticker":symbol,"signal":"INSUFFICIENT_DATA" if warmup else "DATA_UNAVAILABLE",
                "session_date":session,"valid_bars":len(today)}
    if any(b[0]-a[0] != 300 for a,b in zip(today[-21:-1], today[-20:])):
        return {"ticker":symbol,"signal":"DATA_UNAVAILABLE","reason":"gap in 21-bar window"}
    prior = today[-21:-1]
    last = today[-1]
    high = max(x[1] for x in prior)
    avg_volume = sum(x[2] for x in prior) / len(prior)
    ratio = last[2] / avg_volume
    signal = "BREAKOUT_WATCH" if last[1] > high and ratio >= 1.2 else "NO_SIGNAL"
    age_minutes = (now.timestamp() - (last[0]+300)) / 60
    if age_minutes > 10:
        signal = "STALE_DATA"
    return {"ticker":symbol,"signal":signal,"last":last[1],"strategy_id":"breakout_v2",
            "observed_at_utc":now.isoformat(),
            "available_at_utc":dt.datetime.fromtimestamp(last[0]+300,UTC).isoformat(),
            "prior_20_bar_high":round(high,3),"volume_ratio":round(ratio,2),
            "volume_data_valid":True,"session_date":session,
            "timestamp_utc":dt.datetime.fromtimestamp(last[0],UTC).isoformat(),
            "age_minutes":round(age_minutes,1)}

def main():
    now = dt.datetime.now(UTC)
    output=[]
    for symbol in SYMBOLS:
        try:
            row = scan(symbol, now)
            if 'observed_at_utc' in row:
                row['observed_at_utc'] = dt.datetime.now(UTC).isoformat()
            output.append(row)
        except Exception as exc:
            output.append({"ticker":symbol,"signal":"DATA_ERROR","reason":str(exc)[:160]})
    deduplicate(output, Path("results/v2/history"))
    payload={"schema_version":2,"evaluation_version":2,"generated_at_utc":now.isoformat(),"paper_only":True,"orders":False,"signals":output,
             "feed_healthy":any(row["signal"] in ("NO_SIGNAL","BREAKOUT_WATCH","DUPLICATE_SIGNAL","INSUFFICIENT_DATA") for row in output)}
    folder=Path("results/v2")
    folder.mkdir(parents=True,exist_ok=True)
    write_json(folder/"latest.json", payload)
    archive=folder/"history"/now.strftime("%Y-%m-%d")
    archive.mkdir(parents=True,exist_ok=True)
    write_json(archive/(now.strftime("%H%M%S%f")+".json"), payload)
    for row in output: print(row)
    market_hours = market_open(now)
    if market_hours and not any(row["signal"] in ("NO_SIGNAL","BREAKOUT_WATCH","DUPLICATE_SIGNAL","INSUFFICIENT_DATA") for row in output):
        raise SystemExit("Market open but no fresh, usable scan data; check feed/session")
if __name__=="__main__":
    main()
