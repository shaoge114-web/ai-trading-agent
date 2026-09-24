
import numpy as np

def agent_core_decision_v2(row, strategy=None):
    if strategy is None:
        strategy = FINAL_STRATEGY
    required_cols = ["timestamp", "Signal_V2", "ADX", "RSI14", "ATR14", "close"]
    missing = [col for col in required_cols if col not in row.index]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    timestamp = row["timestamp"]
    raw_signal = row["Signal_V2"]
    adx = float(row["ADX"])
    rsi = float(row["RSI14"])
    atr = float(row["ATR14"])
    close = float(row["close"])
    if not all(np.isfinite(x) for x in [adx, rsi, atr, close]):
        raise ValueError("Non-finite market values detected")
    if atr <= 0:
        raise ValueError("ATR must be greater than zero")
    signal_map = {"LONG_TRIGGER": "LONG", "SHORT_TRIGGER": "SHORT", "WAIT": "WAIT"}
    decision = signal_map.get(raw_signal, "WAIT")
    if strategy.get("adx_filter", True):
        adx_max = float(strategy.get("adx_max", 25.0))
        if adx >= adx_max:
            decision = "WAIT"
    entry = close
    risk = atr * float(strategy.get("atr_mult", 1.0))
    stop_loss = None
    tp = None
    rr = float(strategy.get("final_rr", 4.0))
    if decision == "LONG":
        stop_loss = entry - risk
        tp = entry + risk * rr
    elif decision == "SHORT":
        stop_loss = entry + risk
        tp = entry - risk * rr
    if raw_signal == "WAIT":
        reason = "No trigger"
    elif decision == "WAIT" and strategy.get("adx_filter", True) and adx >= strategy.get("adx_max", 25.0):
        reason = f"ADX filter blocked signal: ADX {adx:.4f} >= {strategy.get('adx_max', 25.0)}"
    elif decision in ["LONG", "SHORT"]:
        reason = "Signal accepted"
    else:
        reason = "Signal not accepted"
    return {
        "status": "OK", "decision": decision, "timestamp": timestamp,
        "signal": decision, "raw_signal": raw_signal, "entry": entry,
        "stop_loss": stop_loss, "tp": tp, "risk": risk, "rr": rr,
        "adx": adx, "rsi": rsi, "atr": atr, "reason": reason,
        "strategy_version": "FINAL_V2",
        "max_hold": strategy.get("max_hold", 30),
        "trail_activation_r": strategy.get("trail_activation_r", 3.0),
    }

def create_position_state(decision_result):
    if decision_result["decision"] not in ["LONG", "SHORT"]:
        raise ValueError("Cannot create position from WAIT decision")
    return {
        "status": "OK", "position": decision_result["decision"],
        "entry": decision_result["entry"], "initial_sl": decision_result["stop_loss"],
        "current_sl": decision_result["stop_loss"], "tp": decision_result["tp"],
        "risk": decision_result["risk"], "rr": decision_result["rr"],
        "adx": decision_result["adx"], "rsi": decision_result["rsi"], "atr": decision_result["atr"],
        "entry_timestamp": decision_result["timestamp"], "bars_held": 0,
        "trail_activated": False, "trail_activation_r": decision_result["trail_activation_r"],
        "max_hold": decision_result["max_hold"], "exit_reason": None,
        "exit_price": None, "position_status": "OPEN",
    }

def update_trailing_stop_v2(position_state, current_price):
    state = position_state.copy()
    if state["position_status"] != "OPEN":
        return state
    position = state["position"]
    entry = float(state["entry"])
    risk = float(state["risk"])
    current_sl = float(state["current_sl"])
    activation_r = float(state["trail_activation_r"])
    current_price = float(current_price)
    if risk <= 0:
        raise ValueError("Risk must be greater than zero")
    current_r = ((current_price - entry) / risk) if position == "LONG" else ((entry - current_price) / risk)
    if current_r >= (activation_r - 1e-9):
        if position == "LONG":
            new_sl = entry + 2.0 * risk
            if new_sl > current_sl:
                state["current_sl"] = new_sl
        else:
            new_sl = entry - 2.0 * risk
            if new_sl < current_sl:
                state["current_sl"] = new_sl
        state["trail_activated"] = True
    return state

def check_position_exit(position_state, candle):
    state = position_state.copy()
    if state["position_status"] != "OPEN":
        return state
    position = state["position"]
    high = float(candle["high"])
    low = float(candle["low"])
    close = float(candle["close"])
    current_sl = float(state["current_sl"])
    tp = float(state["tp"])
    bars_held = int(state["bars_held"])
    max_hold = int(state["max_hold"])
    exit_reason = None
    exit_price = None
    if position == "LONG":
        sl_hit = low <= current_sl
        tp_hit = high >= tp
        if sl_hit:
            exit_reason, exit_price = "SL", current_sl
        elif tp_hit:
            exit_reason, exit_price = "TP", tp
    elif position == "SHORT":
        sl_hit = high >= current_sl
        tp_hit = low <= tp
        if sl_hit:
            exit_reason, exit_price = "SL", current_sl
        elif tp_hit:
            exit_reason, exit_price = "TP", tp
    if exit_reason is None and bars_held >= max_hold:
        exit_reason, exit_price = "MAX_HOLD", close
    if exit_reason is not None:
        state["exit_reason"] = exit_reason
        state["exit_price"] = exit_price
        state["position_status"] = "CLOSED"
    return state

def run_trade_lifecycle_v2(position_state, candles):
    state = position_state.copy()
    for _, candle in candles.iterrows():
        if state["position_status"] != "OPEN":
            break
        state = check_position_exit(state, candle)
        if state["position_status"] != "OPEN":
            break
        state["bars_held"] += 1
        state = update_trailing_stop_v2(state, float(candle["close"]))
    return state
