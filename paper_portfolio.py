"""Forward-only paper ledger. No broker, no orders."""
import datetime as dt
import json
import math
from pathlib import Path
from scanner import bars
from market_data import UTC, NY, session_bounds, valid_candles, market_open
from storage import write_json

FEE=.0005
SLIP=.0005
ROOT=Path("results/portfolio_v1")
def initial(now):
    return dict(version=1,paper_only=True,orders=False,started_at=now.isoformat(),cash=10000.,positions={},pending={},trades=[],seen=[],day=None,day_equity=10000.,equity=10000.,events=[],blocked=False)

def advance(s, signals, feeds, now):
    stamp=now.isoformat()
    day=now.astimezone(NY).date().isoformat()
    bounds=session_bounds(now.astimezone(NY).date())
    if s["day"]!=day:
        s["day"]=day
        s["day_equity"]=s["equity"]
        s["blocked"]=False
    def event(kind, symbol, **kw):
        s["events"].append(dict(kind=kind,symbol=symbol,at=stamp,**kw))
    # Close-only execution model; no invented intrabar stops.
    for sym,p in list(s["positions"].items()):
        rows=feeds.get(sym,[])
        eligible=[(t,c) for t,c,v in rows if t+300>p["bar_end"]]
        if not eligible:
            p["data_stale"]=True
            continue
        t,c=eligible[-1]
        end=t+300
        p["mark"]=c
        p["data_stale"]=now.timestamp()-end>600
        elapsed=(end-p["bar_end"])/60
        reason=("STOP_CLOSE" if c<=p["entry"]*.99 else "TARGET_CLOSE" if c>=p["entry"]*1.02 else "TIME_CLOSE" if elapsed>=120 else None)
        if bounds and end>=bounds[1].timestamp(): reason=reason or "SESSION_CLOSE"
        if day!=p["session"]: reason=reason or "OVERNIGHT_RECOVERY"
        if reason:
            # Only use a fresh observed close; stale exits remain pending.
            if p["data_stale"]:
                p["exit_pending"]=True
                continue
            price=c*(1-SLIP)
            proceeds=p["qty"]*price*(1-FEE)
            s["cash"]+=proceeds
            trade=dict(symbol=sym,entry=p["entry"],exit=price,qty=p["qty"],pnl=round(proceeds-p["cost"],6),reason=reason,opened_at=p["opened_at"],closed_at=stamp,exit_bar_end=end)
            s["trades"].append(trade)
            event("EXIT",sym,**{k:v for k,v in trade.items() if k!="symbol"})
            del s["positions"][sym]
    s["equity"]=s["cash"]+sum(p["qty"]*p["mark"] for p in s["positions"].values())
    if s["equity"]<=s["day_equity"]*.98: s["blocked"]=True
    unsafe=any(p.get("data_stale") or p.get("exit_pending") for p in s["positions"].values())
    for sym,p in list(s["pending"].items()):
        observed=dt.datetime.fromisoformat(p["observed"])
        if (now-observed).total_seconds()>1200 or not market_open(now):
            del s["pending"][sym]; event("CANCEL",sym); continue
        if s["blocked"] or unsafe or len(s["positions"])>=5 or sym in s["positions"]: continue
        rows=[(t,c) for t,c,v in feeds.get(sym,[]) if t>=observed.timestamp() and 0<=now.timestamp()-(t+300)<=300]
        if not rows: continue
        t,c=rows[-1]
        price=c*(1+SLIP)
        equity=s["equity"]
        qty=math.floor(min(equity*.2/price,equity*.005/(price*.012),s["cash"]/(price*(1+FEE))))
        if qty<1: continue
        cost=qty*price*(1+FEE)
        s["cash"]-=cost
        s["positions"][sym]=dict(qty=qty,entry=price,cost=cost,mark=c,bar_end=t+300,opened_at=stamp,session=day,data_stale=False)
        del s["pending"][sym]
        event("ENTRY",sym,qty=qty,price=price,signal_id=p["id"])
    if market_open(now) and not s["blocked"] and not unsafe:
        for row in sorted(signals,key=lambda r:r["ticker"]):
            if row.get("signal")!="BREAKOUT_WATCH": continue
            key=row["signal_id"]; sym=row["ticker"]
            if key in s["seen"]: continue
            s["seen"].append(key)
            observed=dt.datetime.fromisoformat(row["observed_at_utc"])
            if observed<dt.datetime.fromisoformat(s["started_at"]) or not 0<=(now-observed).total_seconds()<=600: continue
            if sym not in s["positions"] and sym not in s["pending"]:
                s["pending"][sym]=dict(id=key,observed=observed.isoformat())
                event("CANDIDATE",sym,signal_id=key)
    s["equity"]=s["cash"]+sum(p["qty"]*p["mark"] for p in s["positions"].values())
    s["updated_at"]=stamp
    s["realized_pnl"]=round(sum(t["pnl"] for t in s["trades"]),6)
    return s

def main():
    now=dt.datetime.now(UTC)
    path=ROOT/"state.json"
    s=json.loads(path.read_text()) if path.exists() else initial(now)
    if s.get("version")!=1 or s.get("orders") is not False: raise ValueError("Invalid paper state")
    latest=json.loads(Path("results/v2/latest.json").read_text())
    feeds={}
    for sym in sorted(set(s["positions"])|set(s["pending"])):
        try: feeds[sym]=valid_candles(bars(sym),now)
        except Exception: feeds[sym]=[]
    advance(s,latest["signals"],feeds,now)
    write_json(path,s)
    print(f"PAPER ONLY cash={s['cash']:.2f} equity={s['equity']:.2f} open={len(s['positions'])} closed={len(s['trades'])} realized={s['realized_pnl']:.2f}")
if __name__=="__main__": main()
