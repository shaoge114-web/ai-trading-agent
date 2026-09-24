import requests
import pandas as pd

OKX_BASE_URL = "https://www.okx.com"
OKX_INST_ID = "BTC-USDT"
OKX_BAR = "15m"
OKX_LIMIT = 100


def get_okx_live_candles(
    inst_id=OKX_INST_ID,
    bar=OKX_BAR,
    limit=OKX_LIMIT,
    timeout=15,
):
    url = f"{OKX_BASE_URL}/api/v5/market/candles"
    params = {"instId": inst_id, "bar": bar, "limit": str(limit)}
    response = requests.get(url, params=params, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != "0":
        raise RuntimeError(f"OKX API error: {payload}")
    rows = payload.get("data") or []
    if not rows:
        raise RuntimeError("OKX returned no candle data")

    columns = [
        "timestamp", "open", "high", "low", "close", "volume",
        "volume_currency", "volume_currency_quote", "confirm"
    ]
    df = pd.DataFrame(rows, columns=columns)
    df["timestamp"] = pd.to_datetime(
        pd.to_numeric(df["timestamp"], errors="coerce"),
        unit="ms",
        errors="coerce",
    )
    numeric_cols = [
        "open", "high", "low", "close", "volume",
        "volume_currency", "volume_currency_quote",
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.sort_values("timestamp").reset_index(drop=True)
