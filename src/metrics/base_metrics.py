"""
Base metric helpers used across metric packages.

Adds:
- top_n(group_column, n, value_name)     -> generic top-N counts
- top_by_bool(bool_column, true_value, group_column, n, value_name)
                                           -> top-N where a boolean flag is True (e.g. assists)
"""

from typing import Optional
import pandas as pd


class BaseMetricSet:
    def __init__(self, df: pd.DataFrame, event_type: Optional[str] = None, outcome_column: Optional[str] = None):
        """
        :param df: flattened events dataframe
        :param event_type: if provided, filter df to this event type (e.g. "Pass")
        :param outcome_column: column name used for success/failure (NaN -> success)
        """
        self.df = df.copy()
        self.event_type = event_type
        self.outcome_column = outcome_column

        if self.event_type:
            # filter to events of this type
            self.df = self.df[self.df["type"] == self.event_type]

    def top_n(self, group_column: str, n: int = 5, value_name: str = "count") -> pd.DataFrame:
        """
        Generic top-N by count for a grouping column.
        Returns a DataFrame with [group_column, value_name].
        """
        if group_column not in self.df.columns:
            return pd.DataFrame(columns=[group_column, value_name])

        result = (
            self.df.groupby(group_column)
            .size()
            .sort_values(ascending=False)
            .head(n)
            .reset_index(name=value_name)
        )
        return result

    def top_by_bool(
        self,
        bool_column: str,
        true_value=True,
        group_column: str = "player",
        n: int = 5,
        value_name: str = "count",
    ) -> pd.DataFrame:
        """
        Generic top-N where `bool_column == true_value`.
        Useful for things like `pass_goal_assist`.
        """
        if bool_column not in self.df.columns:
            return pd.DataFrame(columns=[group_column, value_name])

        true_df = self.df[self.df[bool_column] == true_value]
        if true_df.empty:
            return pd.DataFrame(columns=[group_column, value_name])

        result = (
            true_df.groupby(group_column)
            .size()
            .sort_values(ascending=False)
            .head(n)
            .reset_index(name=value_name)
        )
        return result

    def player_average_per_90(self, player: str) -> float:
        """Crude per-90 estimate using the max minute in events for that player."""
        p = self.df[self.df["player"] == player]
        if p.empty or "minute" not in p.columns:
            return 0.0
        minutes = p["minute"].max() or 0
        return (len(p) / minutes) * 90 if minutes > 0 else 0.0

    def overall_average_per_90(self) -> float:
        """Crude per-90 estimate across the dataset."""
        if "minute" not in self.df.columns or self.df.empty:
            return 0.0
        minutes = self.df["minute"].max() or 0
        return (len(self.df) / minutes) * 90 if minutes > 0 else 0.0

    def action_success_rate(self, player: Optional[str] = None) -> float:
        """
        Success rate = proportion of rows where outcome_column is NaN.
        Returns float in range [0,1] or NaN if outcome_column not set.
        """
        if not self.outcome_column:
            return float("nan")
        df = self.df if player is None else self.df[self.df["player"] == player]
        if self.outcome_column not in df.columns or df.empty:
            return 0.0
        success = df[self.outcome_column].isna().sum()
        total = len(df)
        return success / total if total > 0 else 0.0
