import json
import math
import os
from copy import deepcopy
from pathlib import Path

import pandas as pd

from app import (
    agent,
    PAPER_TRADING,
    REAL_ORDER_ENABLED,
    calculate_verified_features,
)
from OKX_LIVE_CANDLES_REFERENCE import get_okx_live_candles


BASE = Path(__file__).resolve().parent
STATE_DIR = BASE / ".agent_state"
STATE_FILE = STATE_DIR / "agent_state.json"
JOURNAL_FILE = BASE / "TRADE_JOURNAL.md"

STATE_VERSION = 4
REQUIRED_STATE_KEYS = {
    "status",
    "position",
    "last_signal",
    "last_timestamp",
}

REQUIRED_FEATURES = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "ATR14",
    "RSI14",
    "ADX",
]


def log(message):
    print(message, flush=True)


def normalize_timestamp(value):
    if value is None:
        return None

    ts = pd.Timestamp(value)

    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)

    return ts


def finite_number(value):
    try:
        value = float(value)
        return math.isfinite(value)
    except Exception:
        return False


def ensure_safety():
    if PAPER_TRADING is not True:
        raise RuntimeError(
            "SAFETY FAILURE: PAPER_TRADING must remain True."
        )

    if REAL_ORDER_ENABLED is not False:
        raise RuntimeError(
            "SAFETY FAILURE: REAL_ORDER_ENABLED must remain False."
        )

    log("PAPER_TRADING       : True")
    log("REAL_ORDER_ENABLED  : False")


def ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def save_state():
    ensure_state_dir()

    payload = {
        "version": STATE_VERSION,
        "status": agent.status,
        "position": deepcopy(agent.position),
        "last_signal": agent.last_signal,
        "last_timestamp": (
            str(agent.last_timestamp)
            if agent.last_timestamp is not None
            else None
        ),
        "last_decision": deepcopy(agent.last_decision),
    }

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def restore_state():
    if not STATE_FILE.exists():
        log("STATE MISSING: rebuild required")
        return False

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        state = json.load(f)

    version = state.get("version")

    if version not in [3, 4]:
        raise RuntimeError(
            f"Unsupported state version: {version}"
        )

    missing = REQUIRED_STATE_KEYS - set(state.keys())

    if missing:
        raise RuntimeError(
            f"STATE CORRUPT: missing keys {sorted(missing)}"
        )

    position = state.get("position")

    if position is not None:
        if not isinstance(position, dict):
            raise RuntimeError("STATE CORRUPT: position is not a dict")

        entry_timestamp = position.get("entry_timestamp")

        if entry_timestamp is not None:
            position["entry_timestamp"] = normalize_timestamp(
                entry_timestamp
            )

        for key in [
            "entry_price",
            "initial_sl",
            "current_sl",
            "tp",
            "risk",
            "rr",
            "adx",
            "rsi",
            "atr",
        ]:
            if key in position and position[key] is not None:
                if not finite_number(position[key]):
                    raise RuntimeError(
                        f"STATE CORRUPT: invalid {key}"
                    )
                position[key] = float(position[key])

    agent.status = state.get("status", "READY")
    agent.position = deepcopy(position)
    agent.last_signal = state.get("last_signal")

    last_timestamp = state.get("last_timestamp")

    agent.last_timestamp = (
        normalize_timestamp(last_timestamp)
        if last_timestamp is not None
        else None
    )

    agent.last_decision = deepcopy(
        state.get("last_decision")
    )

    log(
        "STATE RESTORED: "
        f"version {version}"
    )

    if agent.position is not None:
        log(
            "RESTORED POSITION: "
            f"{agent.position.get('position_side')} "
            f"entry={agent.position.get('entry_price')} "
            f"entry_time={agent.position.get('entry_timestamp')}"
        )

    log(
        "RESTORED LAST TIMESTAMP: "
        f"{agent.last_timestamp}"
    )

    return True


def validate_raw_candles(candles):
    if candles is None:
        raise RuntimeError("OKX returned no candles.")

    if not isinstance(candles, pd.DataFrame):
        candles = pd.DataFrame(candles)

    candles = candles.copy()

    if candles.empty:
        raise RuntimeError("OKX returned an empty candle set.")

    if "timestamp" not in candles.columns:
        raise RuntimeError(
            "CANDLE ERROR: timestamp column missing."
        )

    candles["timestamp"] = candles["timestamp"].apply(
        normalize_timestamp
    )

    candles = candles.dropna(
        subset=["timestamp"]
    ).sort_values(
        "timestamp"
    ).drop_duplicates(
        subset=["timestamp"],
        keep="last",
    ).reset_index(drop=True)

    if candles.empty:
        raise RuntimeError(
            "CANDLE ERROR: no valid timestamps."
        )

    # OKX normally exposes confirmation state as "confirm".
    # If the helper does not expose it, we keep all returned rows.
    if "confirm" in candles.columns:
        confirmed = candles[
            candles["confirm"].astype(str) == "1"
        ].copy()

        if confirmed.empty:
            raise RuntimeError(
                "CANDLE ERROR: no confirmed candles."
            )

        candles = confirmed.reset_index(drop=True)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in numeric_columns:
        if column not in candles.columns:
            raise RuntimeError(
                f"CANDLE ERROR: missing {column}."
            )

        candles[column] = pd.to_numeric(
            candles[column],
            errors="coerce",
        )

    candles = candles.dropna(
        subset=numeric_columns
    ).reset_index(drop=True)

    if len(candles) < 20:
        raise RuntimeError(
            f"CANDLE ERROR: only {len(candles)} valid candles."
        )

    # Check 15m continuity on raw confirmed candles.
    deltas = (
        candles["timestamp"]
        .diff()
        .dropna()
    )

    invalid_deltas = deltas[
        deltas != pd.Timedelta(minutes=15)
    ]

    if not invalid_deltas.empty:
        raise RuntimeError(
            "CANDLE ERROR: irregular 15m candle spacing detected."
        )

    latest = candles["timestamp"].iloc[-1]

    now_utc = pd.Timestamp.now("UTC").tz_localize(None)

    age_minutes = (
        now_utc - latest
    ).total_seconds() / 60.0

    log(f"RAW CANDLES         : {len(candles)}")
    log(f"LATEST CANDLE       : {latest}")
    log(
        f"DATA AGE MINUTES    : "
        f"{age_minutes:.2f}"
    )

    if age_minutes < 0:
        raise RuntimeError(
            "CANDLE ERROR: latest candle is in the future."
        )

    # Do not reject an otherwise valid candle just because the
    # workflow starts a few minutes after the candle close.
    if age_minutes > 60:
        raise RuntimeError(
            f"CANDLE ERROR: data is stale ({age_minutes:.2f} minutes)."
        )

    return candles


def build_features(candles):
    features = calculate_verified_features(
        candles.copy()
    )

    if not isinstance(features, pd.DataFrame):
        raise RuntimeError(
            "FEATURE ERROR: feature engine did not return DataFrame."
        )

    for column in REQUIRED_FEATURES:
        if column not in features.columns:
            raise RuntimeError(
                f"FEATURE ERROR: missing column {column}."
            )

    features["timestamp"] = features["timestamp"].apply(
        normalize_timestamp
    )

    # Warm-up rows naturally contain NaN values for indicators.
    # They must be removed AFTER feature calculation.
    features = features.dropna(
        subset=[
            "timestamp",
            "close",
            "high",
            "low",
            "ATR14",
            "RSI14",
            "ADX",
        ]
    ).reset_index(drop=True)

    if features.empty:
        raise RuntimeError(
            "FEATURE ERROR: no usable rows after warm-up removal."
        )

    # Validate all live decision inputs.
    for column in [
        "close",
        "ATR14",
        "RSI14",
        "ADX",
    ]:
        invalid = ~features[column].apply(
            finite_number
        )

        if invalid.any():
            bad_rows = features.loc[
                invalid,
                ["timestamp", column],
            ]

            raise RuntimeError(
                f"FEATURE ERROR: non-finite values in {column}: "
                f"{bad_rows.to_dict('records')}"
            )

    if (features["ATR14"] <= 0).any():
        raise RuntimeError(
            "FEATURE ERROR: ATR14 contains zero or negative values."
        )

    return features


def trade_id_from_position(position):
    side = position.get("position_side")

    entry_timestamp = normalize_timestamp(
        position.get("entry_timestamp")
    )

    if side is None or entry_timestamp is None:
        raise RuntimeError(
            "Cannot build trade ID from incomplete position."
        )

    return (
        "BTC-USDT-"
        f"{str(side).upper()}-"
        f"{entry_timestamp.strftime('%Y%m%d-%H%M%S')}"
    )


def read_journal():
    if not JOURNAL_FILE.exists():
        return []

    rows = []

    with open(
        JOURNAL_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            line = line.strip()

            if not line.startswith("|"):
                continue

            parts = [
                p.strip()
                for p in line.split("|")
            ]

            if len(parts) < 15:
                continue

            trade_id = parts[1]

            if (
                trade_id == "Trade ID"
                or trade_id.startswith("---")
            ):
                continue

            rows.append(
                {
                    "trade_id": trade_id,
                    "raw": line,
                }
            )

    return rows


def journal_has_trade(trade_id):
    for row in read_journal():
        if row["trade_id"] == trade_id:
            return True

    return False


def journal_append_entry(position, mode):
    trade_id = trade_id_from_position(
        position
    )

    if journal_has_trade(trade_id):
        return

    if not JOURNAL_FILE.exists():
        raise RuntimeError(
            "TRADE_JOURNAL.md is missing."
        )

    entry_timestamp = normalize_timestamp(
        position["entry_timestamp"]
    )

    row = (
        "| "
        f"{trade_id} | "
        f"{position['position_side']} | "
        f"{entry_timestamp} | "
        f"{position['entry_price']:.8f} | "
        f"{position['initial_sl']:.8f} | "
        f"{position['tp']:.8f} | "
        f" | "
        f" | "
        f" | "
        f" | "
        f"{position.get('bars_held', 0)} | "
        f"OPEN | "
        f"{mode} |"
    )

    with open(
        JOURNAL_FILE,
        "a",
        encoding="utf-8",
    ) as f:
        f.write("\n" + row + "\n")


def calculate_trade_r(position, exit_price):
    entry = float(position["entry_price"])
    risk = float(position["risk"])
    side = str(
        position["position_side"]
    ).upper()

    if risk <= 0:
        raise RuntimeError(
            "Cannot calculate R with non-positive risk."
        )

    if side == "LONG":
        return (float(exit_price) - entry) / risk

    if side == "SHORT":
        return (entry - float(exit_price)) / risk

    raise RuntimeError(
        f"Unknown position side: {side}"
    )


def journal_update_exit(
    position,
    exit_timestamp,
    exit_price,
    exit_reason,
):
    trade_id = trade_id_from_position(
        position
    )

    if not JOURNAL_FILE.exists():
        raise RuntimeError(
            "TRADE_JOURNAL.md is missing."
        )

    with open(
        JOURNAL_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        lines = f.readlines()

    found = False

    r_value = calculate_trade_r(
        position,
        exit_price,
    )

    new_lines = []

    for line in lines:
        stripped = line.strip()

        if not stripped.startswith("|"):
            new_lines.append(line)
            continue

        parts = [
            p.strip()
            for p in line.split("|")
        ]

        if len(parts) < 15:
            new_lines.append(line)
            continue

        if parts[1] != trade_id:
            new_lines.append(line)
            continue

        parts[7] = str(
            normalize_timestamp(exit_timestamp)
        )
        parts[8] = f"{float(exit_price):.8f}"
        parts[9] = str(exit_reason)
        parts[10] = f"{float(r_value):.4f}"
        parts[11] = str(
            position.get("bars_held", 0)
        )
        parts[12] = "CLOSED"

        rebuilt = "|" + "|".join(
            f" {p} "
            for p in parts[1:-1]
        ) + "|\n"

        new_lines.append(rebuilt)
        found = True

    if found:
        with open(
            JOURNAL_FILE,
            "w",
            encoding="utf-8",
        ) as f:
            f.writelines(new_lines)


def process_rows(features, rebuild):
    if features.empty:
        return

    if rebuild:
        rows = features.copy()

        log(
            "REBUILD MODE: "
            f"processing {len(rows)} feature rows."
        )

        for _, row in rows.iterrows():
            result = agent.process_feature_row(
                row.to_dict()
            )

            # IMPORTANT:
            # Historical rebuilds reconstruct state only.
            # They do NOT create historical journal trades.
            if result.get("status") == "CLOSED":
                continue

        # Only the final currently-open position is journaled.
        # This avoids fabricating historical live executions.
        if agent.position is not None:
            journal_append_entry(
                agent.position,
                "BOOTSTRAP",
            )

        return

    last_timestamp = agent.last_timestamp

    if last_timestamp is None:
        pending = features
    else:
        pending = features[
            features["timestamp"] > last_timestamp
        ].copy()

    if pending.empty:
        log("NO NEW CONFIRMED CANDLES")
        return

    log(
        "PENDING CANDLES    : "
        f"{len(pending)}"
    )

    for _, row in pending.iterrows():
        result = agent.process_feature_row(
            row.to_dict()
        )

        action = result.get("action")
        status = result.get("status")

        log(
            "PROCESS            : "
            f"{row['timestamp']} "
            f"action={action} "
            f"status={status}"
        )

        if action == "ENTRY":
            position = result.get("position")

            if position is not None:
                journal_append_entry(
                    position,
                    "PAPER",
                )

                log(
                    "JOURNAL ENTRY      : "
                    f"{trade_id_from_position(position)}"
                )

        elif action == "EXIT":
            position = result.get("position")

            if position is not None:
                exit_price = position.get(
                    "exit_price"
                )

                if exit_price is None:
                    exit_price = row["close"]

                exit_reason = position.get(
                    "exit_reason"
                ) or "UNKNOWN"

                journal_update_exit(
                    position,
                    row["timestamp"],
                    exit_price,
                    exit_reason,
                )

                log(
                    "JOURNAL EXIT       : "
                    f"{trade_id_from_position(position)} "
                    f"price={exit_price} "
                    f"reason={exit_reason}"
                )


def main():
    log("=" * 60)
    log("AI TRADING AGENT HEARTBEAT")
    log("=" * 60)

    ensure_safety()
    ensure_state_dir()

    restored = restore_state()

    raw_candles = get_okx_live_candles()

    candles = validate_raw_candles(
        raw_candles
    )

    features = build_features(
        candles
    )

    latest_feature_timestamp = (
        features["timestamp"].iloc[-1]
    )

    log(
        "LATEST FEATURE     : "
        f"{latest_feature_timestamp}"
    )

    rebuild = not restored

    if restored and agent.last_timestamp is not None:
        if agent.last_timestamp > latest_feature_timestamp:

            if agent.position is not None:
                raise RuntimeError(
                    "STATE AHEAD OF MARKET: "
                    "open position requires manual reconciliation."
                )

            log(
                "STATE AHEAD OF DATA: "
                "safe rebuild required."
            )

            rebuild = True

    process_rows(
        features,
        rebuild,
    )

    save_state()

    log(
        "STATE SAVED        : "
        f"version {STATE_VERSION}"
    )

    log(
        "FINAL STATUS       : "
        f"{agent.status}"
    )

    log(
        "FINAL POSITION     : "
        f"{agent.position}"
    )

    log(
        "LAST SIGNAL        : "
        f"{agent.last_signal}"
    )

    log(
        "LAST TIMESTAMP     : "
        f"{agent.last_timestamp}"
    )

    log("=" * 60)
    log("HEARTBEAT SUCCESS")
    log("=" * 60)


if __name__ == "__main__":
    main()
