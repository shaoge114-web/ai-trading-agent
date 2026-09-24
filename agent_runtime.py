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
                "position": deepcopy(self.position),
            }

        decision_result = agent_core_decision_v2(
            pd.Series(feature_row),
            self.strategy,
        )
        self.last_decision = deepcopy(decision_result)
        assert decision_result["status"] == "OK"
        decision = decision_result.get("decision")
        self.last_signal = decision

        if decision not in ["LONG", "SHORT"]:
            self.status = "WAITING"
            return {
                "status": "WAITING",
                "action": "WAIT",
                "decision": decision,
                "timestamp": timestamp,
                "reason": decision_result.get("reason"),
            }

        new_position = create_position_state(decision_result)
        assert new_position is not None
        assert new_position["position_status"] == "OPEN"
        self.position = deepcopy(new_position)
        self.status = "POSITION_OPEN"

        return {
            "status": "OPEN",
            "action": "ENTRY",
            "decision": decision,
            "position": deepcopy(self.position),
        }

    def process_candles(self, candles):
        if isinstance(candles, pd.Series):
            candles = pd.DataFrame([candles.to_dict()])
        elif isinstance(candles, dict):
            candles = pd.DataFrame([candles])
        else:
            candles = candles.copy()

        results = []
        for _, row in candles.iterrows():
            result = self.process_feature_row(row.to_dict())
            results.append(result)
            if result.get("status") == "CLOSED":
                break
        return results

    def get_state(self):
        return {
            "status": self.status,
            "position": deepcopy(self.position),
            "last_signal": self.last_signal,
            "last_timestamp": self.last_timestamp,
        }

    def export_state(self):
        return json.loads(
            json.dumps(
                self.get_state(),
                default=str,
            )
        )
