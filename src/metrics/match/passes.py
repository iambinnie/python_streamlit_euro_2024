from __future__ import annotations
import pandas as pd

from src.metrics.passes_core import PassMetricsCore
from src.metrics.shared.filters import filter_by_match

class MatchPassMetrics(PassMetricsCore):
    """
    Match-scoped pass metrics.
    Only responsibility: filter df by match_id in __init__.
    """
    def __init__(self, df: pd.DataFrame, match_id: int):
        scoped = filter_by_match(df, match_id)
        super().__init__(scoped)
        self.match_id = match_id
