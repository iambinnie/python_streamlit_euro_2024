# src/metrics/base_metrics.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Iterable
import pandas as pd
import numpy as np


@dataclass
class BaseMetricSet:
    """
    Base class for metric sets at any granularity (competition/team/match/player).

    Parameters
    ----------
    df : pd.DataFrame
        Events dataframe (already scoped or full, depending on the wrapper).
    event_type : Optional[str]
        If provided and df has a 'type' column, rows are filtered to that event type.
    outcome_column : Optional[str]
        Column name for event outcome. Default success predicate uses this.
        (e.g., passes: 'pass_outcome' where NaN means 'completed')
    """
    df: pd.DataFrame
    event_type: Optional[str] = None
    outcome_column: Optional[str] = None

    # ─────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────
    def __post_init__(self) -> None:
        df = self.df.copy()

        # Optional: filter to event type if present
        if self.event_type and "type" in df.columns:
            df = df[df["type"] == self.event_type]

        self.df = df.reset_index(drop=True)
        self._minutes_map: dict[str, float] = {}


    # ─────────────────────────────────────────────────────────────
    # Success predicate abstraction
    # ─────────────────────────────────────────────────────────────
    def _is_success(self, df: pd.DataFrame) -> pd.Series:
        """
        Generic success predicate.
        Default: if outcome_column exists → NaN means success (StatsBomb pass-like).
        Override in core subclasses if the event family uses different logic.
        """
        if self.outcome_column and self.outcome_column in df.columns:
            return df[self.outcome_column].isna()
        return pd.Series(False, index=df.index)

    # Convenience for pass-style completion when needed explicitly.
    @staticmethod
    def _is_completed(series: pd.Series) -> pd.Series:
        return series.isna()

    # ─────────────────────────────────────────────────────────────
    # Generic selectors / math
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _and_all(df: pd.DataFrame, masks: Iterable[Optional[pd.Series]]) -> pd.Series:
        mask = pd.Series(True, index=df.index)
        for m in masks:
            if m is None:
                continue
            # align to df index
            m = m.reindex(df.index, fill_value=False)
            mask &= m
        return mask

    def where(self, df: pd.DataFrame, *masks: Optional[pd.Series]) -> pd.DataFrame:
        """Return df filtered by AND of the masks."""
        if not masks:
            return df
        return df[self._and_all(df, masks)]

    def attempts(self, df: pd.DataFrame, *masks: Optional[pd.Series]) -> int:
        """Count rows matching masks."""
        return int(self.where(df, *masks).shape[0])

    def successes(self, df: pd.DataFrame, *masks: Optional[pd.Series]) -> int:
        """Count successes (using _is_success) among rows matching masks."""
        sub = self.where(df, *masks)
        if sub.empty:
            return 0
        return int(self._is_success(sub).sum())

    def success_rate(self, df: pd.DataFrame, *masks: Optional[pd.Series]) -> float:
        """Successes / Attempts for rows matching masks."""
        att = self.attempts(df, *masks)
        if att == 0:
            return 0.0
        suc = self.successes(df, *masks)
        return suc / att

    def mean_of(self, df: pd.DataFrame, col: str, *masks: Optional[pd.Series]) -> float:
        """Mean of a column over rows matching masks."""
        sub = self.where(df, *masks)
        if sub.empty or col not in sub.columns:
            return 0.0
        return float(pd.to_numeric(sub[col], errors="coerce").mean())

    def sum_of(self, df: pd.DataFrame, col: str, *masks: Optional[pd.Series]) -> float:
        """Sum of a column over rows matching masks."""
        sub = self.where(df, *masks)
        if sub.empty or col not in sub.columns:
            return 0.0
        return float(pd.to_numeric(sub[col], errors="coerce").sum())

    def per_90(self, value: float, minutes: float) -> float:
        """Scale a value to per-90 using minutes played."""
        if not minutes or minutes <= 0:
            return 0.0
        return (value / minutes) * 90.0

    # ─────────────────────────────────────────────────────────────
    # Common masks (reusable across event families)
    # ─────────────────────────────────────────────────────────────
    def mask_open_play(self, df: pd.DataFrame) -> pd.Series:
        """True for open-play rows; False for set pieces when detectable."""
        if "pass_type" in df.columns:
            return ~df["pass_type"].isin(["Corner", "Free Kick", "Throw-in"])
        if "play_pattern" in df.columns:
            return ~df["play_pattern"].isin(["From Corner", "From Free Kick", "From Throw In"])
        return pd.Series(True, index=df.index)

    def mask_pressured(self, df: pd.DataFrame) -> pd.Series:
        if "under_pressure" in df.columns:
            return df["under_pressure"].fillna(False).astype(bool)
        return pd.Series(False, index=df.index)

    def in_box_series(self, df: pd.DataFrame, x_col: str, y_col: str) -> pd.Series:
        """Opposition box per glossary: x>=102 and 18<=y<=62 on 120x80 pitch space."""
        if x_col not in df.columns or y_col not in df.columns:
            return pd.Series(False, index=df.index)
        x = pd.to_numeric(df[x_col], errors="coerce")
        y = pd.to_numeric(df[y_col], errors="coerce")
        return (x >= 102) & (y >= 18) & (y <= 62)

    def final_third_series(self, df: pd.DataFrame, x_col: str = "x") -> pd.Series:
        if x_col not in df.columns:
            return pd.Series(False, index=df.index)
        x = pd.to_numeric(df[x_col], errors="coerce")
        return x > 80

    def pass_angle_series(
        self,
        df: pd.DataFrame,
        x0: str = "x",
        y0: str = "y",
        x1: str = "pass_end_x",
        y1: str = "pass_end_y",
    ) -> pd.Series:
        """Angle of pass vector in radians (arctan2(dy, dx))."""
        if any(c not in df.columns for c in [x0, y0, x1, y1]):
            return pd.Series(dtype=float, index=df.index)
        dx = pd.to_numeric(df[x1], errors="coerce") - pd.to_numeric(df[x0], errors="coerce")
        dy = pd.to_numeric(df[y1], errors="coerce") - pd.to_numeric(df[y0], errors="coerce")
        return np.arctan2(dy, dx)

    # ─────────────────────────────────────────────────────────────
    # Generic "top" utilities
    # ─────────────────────────────────────────────────────────────
    def top_n(
        self,
        group_column: str,
        n: int = 5,
        value_name: str = "count",
        *,
        df: Optional[pd.DataFrame] = None,
    ) -> pd.DataFrame:
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

    def set_minutes_map(self, minutes: dict[str, float]) -> None:
        """Attach a {player: minutes_played} map to this metric set."""
        self._minutes_map = minutes or {}

    def minutes_for(self, player: str | None) -> float:
        if not player:
            return 0.0
        return float(self._minutes_map.get(player, 0.0))

    def per_90(self, value: float, player: Optional[str]) -> float:
        """Scale a player-valued metric to per-90 using stored minutes."""
        mins = self.minutes_for(player)
        if mins <= 0:
            return 0.0
        return (value / mins) * 90.0
