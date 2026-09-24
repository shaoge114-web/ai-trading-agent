import numpy as np
import pandas as pd


def calculate_verified_features(df):
    df = df.copy().reset_index(drop=True)

    h = pd.to_numeric(df["high"], errors="coerce")
    l = pd.to_numeric(df["low"], errors="coerce")
    c = pd.to_numeric(df["close"], errors="coerce")

    prev_close = c.shift(1)

    tr = pd.concat(
        [
            h - l,
            (h - prev_close).abs(),
            (l - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    df["ATR14"] = tr.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    change = c.diff()
    gain = change.clip(lower=0)
    loss = -change.clip(upper=0)

    avg_gain = gain.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    avg_loss = loss.ewm(
        alpha=1 / 14,
        adjust=False,
        min_periods=14,
    ).mean()

    rs = avg_gain / avg_loss
    df["RSI14"] = 100 - (100 / (1 + rs))

    up_move = h.diff()
    down_move = -l.diff()

    plus_dm = pd.Series(
        np.where(
            (up_move > down_move) & (up_move > 0),
            up_move,
            0.0,
        ),
        index=df.index,
    )

    minus_dm = pd.Series(
        np.where(
            (down_move > up_move) & (down_move > 0),
            down_move,
            0.0,
        ),
        index=df.index,
    )

    atr_rma = tr.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    plus_rma = plus_dm.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    minus_rma = minus_dm.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    plus_di = 100 * plus_rma / atr_rma
    minus_di = 100 * minus_rma / atr_rma

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)

    df["ADX"] = dx.ewm(
        alpha=1 / 14,
        adjust=False,
    ).mean()

    df["Pivot_High"] = np.where(
        h.eq(h.rolling(4).max()),
        h,
        np.nan,
    )

    df["Pivot_Low"] = np.where(
        l.eq(l.rolling(4).min()),
        l,
        np.nan,
    )

    trend_state = "UNKNOWN"
    last_pivot_high = None
    last_pivot_low = None

    structure_events = []
    trend_states = []

    for _, row in df.iterrows():
        bull_break = (
            last_pivot_high is not None
            and float(row["close"]) > float(last_pivot_high)
        )

        bear_break = (
            last_pivot_low is not None
            and float(row["close"]) < float(last_pivot_low)
        )

        event = ""

        if bull_break and not bear_break:
            if trend_state == "UNKNOWN":
                event = "BULLISH_BOS"
                trend_state = "BULLISH"
            elif trend_state in ["BULLISH", "BULLISH_TRANSITION"]:
                event = "BULLISH_BOS"
                trend_state = "BULLISH"
            else:
                event = "BULLISH_CHOCH"
                trend_state = "BULLISH_TRANSITION"
        elif bear_break and not bull_break:
            if trend_state == "UNKNOWN":
                event = "BEARISH_BOS"
                trend_state = "BEARISH"
            elif trend_state in ["BEARISH", "BEARISH_TRANSITION"]:
                event = "BEARISH_BOS"
                trend_state = "BEARISH"
            else:
                event = "BEARISH_CHOCH"
                trend_state = "BEARISH_TRANSITION"

        structure_events.append(event)
        trend_states.append(trend_state)

        if pd.notna(row["Pivot_High"]):
            last_pivot_high = float(row["Pivot_High"])

        if pd.notna(row["Pivot_Low"]):
            last_pivot_low = float(row["Pivot_Low"])

    df["Structure_Event_V2"] = structure_events
    df["Trend_State"] = trend_states

    df["Structure_Confirmation_V2"] = np.where(
        df["Trend_State"].isin(["BULLISH", "BEARISH"]),
        "CONFIRMED",
        np.where(
            df["Trend_State"].isin(
                ["BULLISH_TRANSITION", "BEARISH_TRANSITION"]
            ),
            "TRANSITION",
            "UNKNOWN",
        ),
    )

    rsi_diff = df["RSI14"].diff()

    df["RSI_Direction"] = np.where(
        rsi_diff > 0,
        "RISING",
        np.where(
            rsi_diff < 0,
            "FALLING",
            "FLAT",
        ),
    )

    df["RSI_Confirmation"] = np.where(
        (df["RSI14"] >= 50) & (df["RSI_Direction"] == "RISING"),
        "BULLISH_CONFIRMATION",
        np.where(
            (df["RSI14"] <= 50) & (df["RSI_Direction"] == "FALLING"),
            "BEARISH_CONFIRMATION",
            "NEUTRAL",
        ),
    )

    df["Signal_V1"] = np.where(
        (df["Trend_State"] == "BULLISH")
        & (df["RSI_Confirmation"] == "BULLISH_CONFIRMATION"),
        "LONG_SETUP",
        np.where(
            (df["Trend_State"] == "BEARISH")
            & (df["RSI_Confirmation"] == "BEARISH_CONFIRMATION"),
            "SHORT_SETUP",
            "WAIT",
        ),
    )

    previous_signal = df["Signal_V1"].shift(1).fillna("WAIT")

    df["Signal_V2"] = np.where(
        (df["Signal_V1"] == "LONG_SETUP")
        & (previous_signal == "WAIT"),
        "LONG_TRIGGER",
        np.where(
            (df["Signal_V1"] == "SHORT_SETUP")
            & (previous_signal == "WAIT"),
            "SHORT_TRIGGER",
            "WAIT",
        ),
    )

    return df
