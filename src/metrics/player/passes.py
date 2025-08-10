from __future__ import annotations
import pandas as pd

from src.metrics.passes_core import PassMetricsCore
from src.metrics.shared.filters import filter_by_player

class PlayerPassMetrics(PassMetricsCore):
    """
    Player-scoped pass metrics.
    Only responsibility: filter df by player in __init__.
    """
    def __init__(self, df: pd.DataFrame, player_name: str):
        scoped = filter_by_player(df, player_name)
        super().__init__(scoped)
        self.player_name = player_name
