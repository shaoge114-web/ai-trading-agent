import json
from copy import deepcopy
from pathlib import Path
import importlib.util
import pandas as pd

BASE = Path(__file__).resolve().parent

with open(BASE / "FINAL_STRATEGY.json", "r", encoding="utf-8") as f:
    FINAL_STRATEGY = json.load(f)


def _load_module(name, filename):
    path = BASE / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


feature_engine = _load_module(
    "feature_engine_verified",
    "FEATURE_ENGINE_VERIFIED.py",
)

trade_engine = _load_module(
    "trade_engine_verified",
    "TRADE_ENGINE_VERIFIED.py",
)

trade_engine.FINAL_STRATEGY = FINAL_STRATEGY

calculate_verified_features = feature_engine.calculate_verified_features
agent_core_decision_v2 = trade_engine.agent_core_decision_v2
create_position_state = trade_engine.create_position_state
update_trailing_stop_v2 = trade_engine.update_trailing_stop_v2
check_position_exit = trade_engine.check_position_exit
run_trade_lifecycle_v2 = trade_engine.run_trade_lifecycle_v2


class FinalTradingAgent:

    def __init__(self, strategy):
        self.strategy = deepcopy(strategy)
        self.position = None
        self.last_signal = None
        self.last_decision = None
        self.last_timestamp = None
        self.status = "READY"

    def process_feature_row(self, feature_row):
        feature_row = dict(feature_row)
        timestamp = feature_row.get("timestamp")
        self.last_timestamp = timestamp

        if self.position is not None:
            entry_timestamp = self.position.get("entry_timestamp")

            if (
                timestamp is not None
                and entry_timestamp is not None
                and timestamp <= entry_timestamp
            ):
                return {
                    "status": "OPEN",
                    "action": "HOLD",
                    "position": deepcopy(self.position),
                    "reason": "Entry candle excluded from exit engine",
                }

            candle_df = pd.DataFrame([feature_row])

            lifecycle_result = run_trade_lifecycle_v2(
                self.position,
                candle_df,
            )

            self.position = deepcopy(lifecycle_result)

            if self.position.get("position_status") == "CLOSED":
                closed_position = deepcopy(self.position)
                self.position = None
                self.status = "WAITING"

                return {
                    "status": "CLOSED",
                    "action": "EXIT",
                    "position": closed_position,
                }

            return {
                "status": "OPEN",
                "action": "HOLD",
                "position": deepcopy(self
