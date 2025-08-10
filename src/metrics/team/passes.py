from __future__ import annotations
import pandas as pd

from src.metrics.passes_core import PassMetricsCore
from src.metrics.shared.filters import filter_by_team

class TeamPassMetrics(PassMetricsCore):
    """
    Team-scoped pass metrics.
    Only responsibility: filter df by team in __init__.
    """
    def __init__(self, df: pd.DataFrame, team_name: str):
        scoped = filter_by_team(df, team_name)
        super().__init__(scoped)
        self.team_name = team_name
