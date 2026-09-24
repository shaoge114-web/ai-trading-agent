import json
import os
from flask import Flask, request, jsonify

from agent_runtime import (
    FINAL_STRATEGY,
    FinalTradingAgent,
    calculate_verified_features,
)
from OKX_LIVE_CANDLES_REFERENCE import get_okx_live_candles

app = Flask(__name__)

REAL_ORDER_ENABLED = False
PAPER_TRADING = True

agent = FinalTradingAgent(FINAL_STRATEGY)


@app.get("/")
def health():
    return jsonify({
        "status": "OK",
        "service": "AI_Trading_Agent",
        "version": "FINAL_V2",
        "real_order_enabled": REAL_ORDER_ENABLED,
        "paper_trading": PAPER_TRADING,
    })


@app.get("/health")
def health_check():
    return jsonify({
        "status": "healthy",
        "real_order_enabled": REAL_ORDER_ENABLED,
    })


@app.get("/api/analyze")
def analyze():
    candles = get_okx_live_candles()
    features = calculate_verified_features(candles)
    row = features.iloc[-1].to_dict()
    result = agent.process_feature_row(row)
    return jsonify({
        "status": "OK",
        "market": "BTC-USDT",
        "timeframe": "15m",
        "paper_trading": PAPER_TRADING,
        "real_order_enabled": REAL_ORDER_ENABLED,
        "result": result,
    })


@app.post("/webhook/whatsapp")
def whatsapp_webhook():
    data = request.get_json(silent=True) or {}
    return jsonify({
        "status": "received",
        "message": "WhatsApp webhook ready",
        "real_order_enabled": REAL_ORDER_ENABLED,
        "received": data,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
