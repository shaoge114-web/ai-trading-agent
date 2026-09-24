# AI Trading Agent

Current runtime package: BUILD 20E recovery baseline.

Paper trading is enabled. Real orders are disabled.

## Runtime files
- `app.py` — HTTP service
- `agent_runtime.py` — runtime logic
- `FEATURE_ENGINE_VERIFIED.py` — verified feature engine
- `TRADE_ENGINE_VERIFIED.py` — verified trade engine
- `OKX_LIVE_CANDLES_REFERENCE.py` — live candle reference
- `FINAL_STRATEGY.json` — locked strategy configuration
- `config.json` — runtime configuration
- `requirements.txt` — Python dependencies
- `Dockerfile` — container definition

## Safety
`REAL_ORDER=false` and `PAPER_TRADING=true` are the current deployment defaults.
