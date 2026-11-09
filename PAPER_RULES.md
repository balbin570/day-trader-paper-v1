# Paper-only research
- No brokerage API, no order placement, no live trades.
- Scanner is an independent minimal prototype, NOT a port of the upstream Day Trader Skill.
- Uses Yahoo Finance unofficial 5-minute data; prices may be delayed or unavailable.
- BREAKOUT_WATCH is an observation, not an executable entry recommendation.
- Signal: latest close above preceding 20-bar close maximum and volume >=1.2 times preceding 20-bar mean.
- No profitability claims; no transaction costs or slippage modeled.
- GitHub Actions scheduled jobs may be delayed or skipped.
- The workflow saves latest observations in results/latest.json.
