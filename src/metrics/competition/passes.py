from __future__ import annotations
import pandas as pd

from src.metrics.passes_core import PassMetricsCore

class CompetitionPassMetrics(PassMetricsCore):
    """
    Competition-wide pass metrics.
    Inherits all metric methods from PassMetricsCore.
    """
    def __init__(self, df: pd.DataFrame):
        # No extra scoping: pass full competition df straight to the core
        super().__init__(df)
