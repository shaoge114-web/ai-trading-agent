# AI Trading Agent — Build 20C Ready Bundle

Built from the verified Recovery 18Q files, not regenerated formulas.

Included verified sources:
- FEATURE_ENGINE_VERIFIED.py
- TRADE_ENGINE_VERIFIED.py
- FINAL_STRATEGY.json
- OKX_LIVE_CANDLES_REFERENCE.py

Runtime integration:
- agent_runtime.py
- FinalTradingAgent
- Cloud Run app.py
- /api/analyze -> OKX public candles -> verified features -> verified decision -> paper agent state
- /webhook/whatsapp remains a clean webhook endpoint; provider credentials are required before live WhatsApp delivery.

Safety:
- REAL_ORDER_ENABLED = false
- PAPER_TRADING = true
