# src/metrics/base_metrics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any
import pandas as pd


@dataclass
class BaseMetricSet:
    """
    Base class for metric sets at any granularity (competition/team/match/player).

    Parameters
    ----------
    df : pd.DataFrame
        Raw events dataframe (can be full or pre-filtered).
    event_type : Optional[str]
        If provided and df has a 'type' column, rows are filtered to that event type.
    outcome_column : Optional[str]
        Column that represents the event's outcome. For StatsBomb passes this is 'pass_outcome'
        where NaN means 'completed'.
    """
    df: pd.DataFrame
    event_type: Optional[str] = None
    outcome_column: Optional[str] = None

    def __post_init__(self) -> None:
        df = self.df.copy()

        # Optional: filter to event type if present
        if self.event_type and "type" in df.columns:
            df = df[df["type"] == self.event_type]

        # Keep an index that's simple to work with
        df = df.reset_index(drop=True)
        self.df = df

    # ─────────────────────────────────────────────────────────────
    # Shared helpers (used by pass metrics across all granularities)
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _is_completed(series: pd.Series) -> pd.Series:
        """
        StatsBomb convention for passes:
        - Completed passes have NaN in 'pass_outcome'.
        For other event families that use different coding, override in subclass if needed.
        """
        return series.isna()

    @staticmethod
    def _is_set_piece(df: pd.DataFrame) -> pd.Series:
        """
        Detect set-piece passes using pass_type or play_pattern when available.
        Falls back to 'all open play' if neither exists.
        """
        if "pass_type" in df.columns:
            return df["pass_type"].isin(["Corner", "Free Kick", "Throw-in"])
        if "play_pattern" in df.columns:
            return df["play_pattern"].isin(["From Corner", "From Free Kick", "From Throw In"])
        return pd.Series(False, index=df.index)

    @staticmethod
    def _in_box(x: Any, y: Any) -> bool:
        """
        Box area per glossary: x>=102 and 18<=y<=62 (StatsBomb 120x80 pitch space).
        Handles NaNs / bad values defensively.
        """
        try:
            if pd.isna(x) or pd.isna(y):
                return False
            xf, yf = float(x), float(y)
            return (xf >= 102.0) and (18.0 <= yf <= 62.0)
        except Exception:
            return False

    @staticmethod
    def _is_throughball_series(df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series(False, index=df.index)
        mask = pd.Series(False, index=df.index)
        if "pass_through_ball" in df.columns:
            mask |= df["pass_through_ball"].fillna(False).astype(bool)
        if "pass_technique" in df.columns:
            tech = df["pass_technique"].fillna("").astype(str).str.lower().str.strip()
            mask |= tech.str.contains(r"\bthrough[- ]?ball\b", regex=True)
        return mask

    # ─────────────────────────────────────────────────────────────
    # Generic utilities
    # ─────────────────────────────────────────────────────────────

    def top_n(
        self,
        group_column: str,
        n: int = 5,
        value_name: str = "count",
        *,
        df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Return top-N frequencies for a group column.
        """
        data = self.df if df is None else df
        if data.empty or group_column not in data.columns:
            return pd.DataFrame(columns=[group_column, value_name])
        out = (
            data.groupby(group_column)
            .size()
            .sort_values(ascending=False)
            .head(n)
            .reset_index(name=value_name)
        )
        return out

    def top_by_bool(
        self,
        flag_column: str,
        true_value: Any = True,
        group_column: str = "player",
        n: int = 5,
        value_name: str = "count",
        *,
        df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
        """
        Return top-N counts by a boolean-like flag in rows.
        Example: top assisters where `pass_goal_assist == True`.
        """
        data = self.df if df is None else df
        if data.empty or (flag_column not in data.columns) or (group_column not in data.columns):
            return pd.DataFrame(columns=[group_column, value_name])
        filt = data[flag_column] == true_value
        sub = data[filt]
        if sub.empty:
            return pd.DataFrame(columns=[group_column, value_name])
        out = (
            sub.groupby(group_column)
            .size()
            .sort_values(ascending=False)
            .head(n)
            .reset_index(name=value_name)
        )
        return out

    def action_success_rate(self, player: Optional[str] = None) -> float:
        """
        Generic success rate for an event family that uses an outcome column.
        For passes (StatsBomb), NaN in outcome column means 'completed' (success).
        """
        if self.outcome_column is None or self.outcome_column not in self.df.columns:
            return 0.0
        df = self.df if player is None else self.df[self.df["player"] == player]
        attempted = len(df)
        if attempted == 0:
            return 0.0
        success = self._is_completed(df[self.outcome_column]).sum()
        return success / attempted
