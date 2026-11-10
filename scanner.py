"""US equity paper scanner. No broker or order execution."""
import datetime as dt
import json
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

SYMBOLS = ["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","AVGO","PLTR","SPY","QQQ"]
NY = ZoneInfo("America/New_York")
UTC = dt.timezone.utc

def bars(symbol):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
    request = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = json.load(response)
    result = data["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    return [(t, c, v) for t,c,v in zip(result["timestamp"], quote["close"], quote["volume"])
            if c is not None and v is not None]

def scan(symbol, now=None):
    now = now or dt.datetime.now(UTC)
    raw = bars(symbol)
    # Use completed regular-session candles with real positive volume.
    valid = []
    for timestamp, close, volume in raw:
        local = dt.datetime.fromtimestamp(timestamp, UTC).astimezone(NY)
        if local.weekday() >= 5 or not (dt.time(9,30) <= local.time() < dt.time(16,0)):
            continue
        if timestamp + 300 > now.timestamp() or volume <= 0:
            continue
        valid.append((timestamp, close, volume, local.date().isoformat()))
    if not valid:
        return {"ticker":symbol,"signal":"DATA_UNAVAILABLE","reason":"no completed positive-volume regular-session bars"}
    session = valid[-1][3]
    today = [x for x in valid if x[3] == session]
    if len(today) < 21:
        return {"ticker":symbol,"signal":"INSUFFICIENT_DATA","session_date":session,"valid_bars":len(today)}
    prior = today[-21:-1]
    last = today[-1]
    high = max(x[1] for x in prior)
    avg_volume = sum(x[2] for x in prior) / len(prior)
    ratio = last[2] / avg_volume
    signal = "BREAKOUT_WATCH" if last[1] > high and ratio >= 1.2 else "NO_SIGNAL"
    age_minutes = (now.timestamp() - (last[0]+300)) / 60
    if age_minutes > 45:
        signal = "STALE_DATA"
    return {"ticker":symbol,"signal":signal,"last":round(last[1],3),
            "prior_20_bar_high":round(high,3),"volume_ratio":round(ratio,2),
            "volume_data_valid":True,"session_date":session,
            "timestamp_utc":dt.datetime.fromtimestamp(last[0],UTC).isoformat(),
            "age_minutes":round(age_minutes,1)}

def main():
    now = dt.datetime.now(UTC)
    output=[]
    for symbol in SYMBOLS:
        try:
            output.append(scan(symbol, now))
        except Exception as exc:
            output.append({"ticker":symbol,"signal":"DATA_ERROR","reason":str(exc)[:160]})
    payload={"generated_at_utc":now.isoformat(),"paper_only":True,"orders":False,"signals":output}
    folder=Path("results")
    folder.mkdir(exist_ok=True)
    (folder/"latest.json").write_text(json.dumps(payload,indent=2)+"\n")
    archive=folder/"history"/now.strftime("%Y-%m-%d")
    archive.mkdir(parents=True,exist_ok=True)
    (archive/(now.strftime("%H%M%S")+".json")).write_text(json.dumps(payload,indent=2)+"\n")
    for row in output: print(row)
    if not any(row["signal"] in ("NO_SIGNAL","BREAKOUT_WATCH") for row in output):
        raise SystemExit("No fresh, usable scan data; check feed/session")
if __name__=="__main__":
    main()
