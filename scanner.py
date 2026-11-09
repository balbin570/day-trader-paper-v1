import csv, datetime as dt, json, os, urllib.request
from pathlib import Path
SYMBOLS=["AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AMD","AVGO","PLTR","SPY","QQQ"]
def bars(symbol):
    url=f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=5m"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req,timeout=20) as response: data=json.load(response)
    result=data["chart"]["result"][0]
    q=result["indicators"]["quote"][0]
    return [(t,c,v) for t,c,v in zip(result["timestamp"],q["close"],q["volume"]) if c is not None and v is not None]
def scan(symbol):
    b=bars(symbol)
    if len(b)<30:return None
    closes=[x[1] for x in b]; volumes=[x[2] for x in b]
    last=closes[-1]; prior=max(closes[-21:-1]); avg=sum(volumes[-21:-1])/20
    ratio=volumes[-1]/avg if avg else None
    signal="BREAKOUT_WATCH" if ratio is not None and last>prior and ratio>=1.2 else "NO_SIGNAL"
    return {"ticker":symbol,"signal":signal,"last":round(last,3),"prior_20_bar_high":round(prior,3),"volume_ratio":round(ratio,2) if ratio is not None else None,"volume_data_valid":avg>0 and volumes[-1]>0,"timestamp_utc":dt.datetime.fromtimestamp(b[-1][0],dt.timezone.utc).isoformat()}
def main():
    output=[]
    for s in SYMBOLS:
        try:
            result=scan(s)
            if result:output.append(result)
        except Exception as e:print(f"{s}: DATA_ERROR {type(e).__name__}: {e}")
    Path("results").mkdir(exist_ok=True)
    with open("results/latest.json","w") as f:json.dump({"generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"paper_only":True,"orders":False,"signals":output},f,indent=2)
    for x in output:print(x)
    if not output:raise SystemExit("No market data available; no signals generated")
if __name__=="__main__":main()
