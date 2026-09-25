import json
import math
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

STATE_VERSION = 5

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
    STATE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


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
        "last_decision": deepcopy(
            agent.last_decision
        ),
    }

    with open(
        STATE_FILE,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            payload,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def validate_position_state(position):
    if position is None:
        return

    if not isinstance(position, dict):
        raise RuntimeError(
            "STATE CORRUPT: position is not a dict."
        )

    required_position_keys = {
        "status",
        "position",
        "entry",
        "initial_sl",
        "current_sl",
        "tp",
        "risk",
        "rr",
        "adx",
        "rsi",
        "atr",
        "entry_timestamp",
        "bars_held",
        "trail_activated",
        "trail_activation_r",
        "max_hold",
        "exit_reason",
        "exit_price",
        "position_status",
    }

    missing = (
        required_position_keys
        - set(position.keys())
    )

    if missing:
        raise RuntimeError(
            "STATE CORRUPT: position missing keys: "
            f"{sorted(missing)}"
        )

    if position["position"] not in [
        "LONG",
        "SHORT",
    ]:
        raise RuntimeError(
            "STATE CORRUPT: invalid position side."
        )

    if position["position_status"] != "OPEN":
        raise RuntimeError(
            "STATE CORRUPT: stored position "
            "must be OPEN."
        )

    position["entry_timestamp"] = (
        normalize_timestamp(
            position["entry_timestamp"]
        )
    )

    if position["entry_timestamp"] is None:
        raise RuntimeError(
            "STATE CORRUPT: missing entry_timestamp."
        )

    numeric_fields = [
        "entry",
        "initial_sl",
        "current_sl",
        "tp",
        "risk",
        "rr",
        "adx",
        "rsi",
        "atr",
        "trail_activation_r",
    ]

    for key in numeric_fields:
        if not finite_number(
            position[key]
        ):
            raise RuntimeError(
                f"STATE CORRUPT: invalid {key}."
            )

        position[key] = float(
            position[key]
        )

    position["bars_held"] = int(
        position["bars_held"]
    )

    position["max_hold"] = int(
        position["max_hold"]
    )


def restore_state():
    if not STATE_FILE.exists():
        log(
            "STATE MISSING: rebuild required"
        )
        return False

    with open(
        STATE_FILE,
        "r",
        encoding="utf-8",
    ) as f:
        state = json.load(f)

    version = state.get("version")

    if version not in [3, 4, 5]:
        raise RuntimeError(
            f"Unsupported state version: {version}"
        )

    missing = (
        REQUIRED_STATE_KEYS
        - set(state.keys())
    )

    if missing:
        raise RuntimeError(
            "STATE CORRUPT: missing keys "
            f"{sorted(missing)}"
        )

    position = state.get(
        "position"
    )

    if position is not None:
        validate_position_state(
            position
        )

    agent.status = state.get(
        "status",
        "READY",
    )

    agent.position = deepcopy(
        position
    )

    agent.last_signal = state.get(
        "last_signal"
    )

    last_timestamp = state.get(
        "last_timestamp"
    )

    agent.last_timestamp = (
        normalize_timestamp(
            last_timestamp
        )
        if last_timestamp is not None
        else None
    )

    agent.last_decision = deepcopy(
        state.get(
            "last_decision"
        )
    )

    log(
        "STATE RESTORED: "
        f"version {version}"
    )

    if agent.position is not None:
        log(
            "RESTORED POSITION: "
            f"{agent.position['position']} "
            f"entry={agent.position['entry']} "
            f"entry_time="
            f"{agent.position['entry_timestamp']}"
        )

    log(
        "RESTORED LAST TIMESTAMP: "
        f"{agent.last_timestamp}"
    )

    return True


def validate_raw_candles(candles):
    if candles is None:
        raise RuntimeError(
            "OKX returned no candles."
        )

    if not isinstance(
        candles,
        pd.DataFrame,
    ):
        candles = pd.DataFrame(
            candles
        )

    candles = candles.copy()

    if candles.empty:
        raise RuntimeError(
            "OKX returned an empty candle set."
        )

    if "timestamp" not in candles.columns:
        raise RuntimeError(
            "CANDLE ERROR: timestamp column missing."
        )

    candles["timestamp"] = (
        candles["timestamp"].apply(
            normalize_timestamp
        )
    )

    candles = (
        candles
        .dropna(
            subset=["timestamp"]
        )
        .sort_values(
            "timestamp"
        )
        .drop_duplicates(
            subset=["timestamp"],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if candles.empty:
        raise RuntimeError(
            "CANDLE ERROR: no valid timestamps."
        )

    if "confirm" in candles.columns:
        candles = candles[
            candles["confirm"].astype(str)
            == "1"
        ].copy()

        candles = candles.reset_index(
            drop=True
        )

        if candles.empty:
            raise RuntimeError(
                "CANDLE ERROR: "
                "no confirmed candles."
            )

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
    ]

    for column in numeric_columns:
        if column not in candles.columns:
            raise RuntimeError(
                f"CANDLE ERROR: "
                f"missing {column}."
            )

        candles[column] = pd.to_numeric(
            candles[column],
            errors="coerce",
        )

    candles = candles.dropna(
        subset=numeric_columns
    ).reset_index(
        drop=True
    )

    if len(candles) < 20:
        raise RuntimeError(
            "CANDLE ERROR: only "
            f"{len(candles)} valid candles."
        )

    deltas = (
        candles["timestamp"]
        .diff()
        .dropna()
    )

    invalid_deltas = deltas[
        deltas
        != pd.Timedelta(
            minutes=15
        )
    ]

    if not invalid_deltas.empty:
        raise RuntimeError(
            "CANDLE ERROR: irregular "
            "15m candle
