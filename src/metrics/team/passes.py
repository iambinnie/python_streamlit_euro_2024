# src/metrics/team/passes.py
from src.metrics.base_metrics import BaseMetricSet
from src.metrics.shared.filters import filter_by_team
import pandas as pd


class TeamPassMetrics(BaseMetricSet):
    def __init__(self, df: pd.DataFrame, team_name: str):
        df = filter_by_team(df, team_name)
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
        self.team_name = team_name

    def top_passers(self, n: int = 5) -> pd.DataFrame:
        return self.top_n("player", n=n, value_name="passes")

    def top_assisters(self, n: int = 5) -> pd.DataFrame:
        return self.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=n, value_name="assists")

    def pass_success_rate(self, player: str = None) -> float:
        return super().action_success_rate(player)

    def average_pass_length(self) -> float:
        return float(self.df["pass_length"].mean()) if "pass_length" in self.df.columns else 0.0
