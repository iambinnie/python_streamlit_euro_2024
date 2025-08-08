# src/metrics/player/passes.py
from src.metrics.base_metrics import BaseMetricSet
from src.metrics.shared.filters import filter_by_player
import pandas as pd


class PlayerPassMetrics(BaseMetricSet):
    def __init__(self, df: pd.DataFrame, player_name: str):
        df = filter_by_player(df, player_name)
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
        self.player_name = player_name

    def top_passers(self, n: int = 5) -> pd.DataFrame:
        return self.top_n("player", n=n, value_name="passes")

    def top_assisters(self, n: int = 5) -> pd.DataFrame:
        return self.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=n, value_name="assists")

    def pass_success_rate(self) -> float:
        return super().action_success_rate(self.player_name)

    def average_pass_length(self) -> float:
        return float(self.df["pass_length"].mean()) if "pass_length" in self.df.columns else 0.0
