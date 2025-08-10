# src/metrics/passes_core.py
from __future__ import annotations
from typing import Optional
import pandas as pd


from src.metrics.base_metrics import BaseMetricSet


class PassMetricsCore(BaseMetricSet):
    """
    All Phase-1 passing metrics live here once.
    Wrappers (Competition/Team/Match/Player) should only scope the DataFrame in __init__.
    """

    def __init__(self, df: pd.DataFrame):
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")

    # ─────────────────────────────────────────────────────────────
    # Robust through-ball detector (works for boolean + technique text)
    # ─────────────────────────────────────────────────────────────
    @staticmethod
    def _is_throughball_series(df: pd.DataFrame) -> pd.Series:
        """
        Robust through-ball detection:
        - boolean-like flag: pass_through_ball == True / 'true' / 1 / '1' / 'yes'
        - technique text: pass_technique contains 'through ball' (hyphen/space tolerant)
        """
        if df.empty:
            return pd.Series(False, index=df.index)

        mask = pd.Series(False, index=df.index)

        if "pass_through_ball" in df.columns:
            col = df["pass_through_ball"]
            if col.dtype == "bool":
                tb_flag = col
            elif pd.api.types.is_numeric_dtype(col):
                tb_flag = col.fillna(0).astype(int).astype(bool)
            else:
                # object/string → normalize to truthy set
                truthy = {"true", "1", "yes", "y", "t"}
                tb_flag = col.astype(str).str.strip().str.lower().isin(truthy)
            mask |= tb_flag.fillna(False)

        if "pass_technique" in df.columns:
            tech = df["pass_technique"].astype(str).str.lower().str.strip()
            # matches: 'through ball', 'through-ball', 'throughball'
            mask |= tech.str.contains(r"\bthrough[- ]?ball\b", regex=True, na=False)

        return mask

    # ─────────────────────────────────────────────────────────────
    # Phase-1 metrics (glossary-aligned)
    # ─────────────────────────────────────────────────────────────

    def passing_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        return self.success_rate(df)

    def pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        return self.mean_of(df, "pass_length")

    def successful_pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        comp = self._is_success(df)  # completion predicate
        return self.mean_of(df, "pass_length", comp)

    def long_balls(self, player: Optional[str] = None, min_len: float = 35.0) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        long_mask = None
        if "pass_length" in df.columns:
            long_mask = df["pass_length"] >= min_len
        comp = self._is_success(df)
        return self.attempts(df, long_mask, comp)

    def long_ball_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        long_mask = None
        if "pass_length" in df.columns:
            long_mask = df["pass_length"] >= min_len
        return self.success_rate(df, long_mask)

    def open_play_passes(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        return self.attempts(df, self.mask_open_play(df))

    def passes_into_box(self, player: Optional[str] = None, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        in_box = self.in_box_series(df, "pass_end_x", "pass_end_y")
        comp = self._is_success(df)
        masks = [in_box, comp]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    def op_passes_into_box(self, player: Optional[str] = None) -> int:
        return self.passes_into_box(player=player, open_play=True)

    def passes_inside_box(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        start_in = self.in_box_series(df, "x", "y")
        end_in = self.in_box_series(df, "pass_end_x", "pass_end_y")
        comp = self._is_success(df)
        return self.attempts(df, start_in, end_in, comp)

    def throughballs_attempted(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        return self.attempts(df, self._is_throughball_series(df))

    def throughballs(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        is_tb = self._is_throughball_series(df)
        comp = self._is_success(df)
        return self.attempts(df, is_tb, comp)

    def throughballs_completion_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        is_tb = self._is_throughball_series(df)
        return self.success_rate(df, is_tb)

    def top_throughball_creators(self, n: int = 5) -> pd.DataFrame:
        """
        Top players by through-balls attempted, completed, and completion percentage.
        """
        df = self.df
        if df.empty or "player" not in df.columns:
            return pd.DataFrame(columns=[
                "player", "throughballs_attempted", "throughballs_completed", "completion_pct"
            ])

        is_tb = self._is_throughball_series(df)
        if not is_tb.any():
            return pd.DataFrame(columns=[
                "player", "throughballs_attempted", "throughballs_completed", "completion_pct"
            ])

        comp = self._is_success(df)  # pass completion predicate (NaN outcome → success)

        attempted = df[is_tb].groupby("player").size()
        completed = df[is_tb & comp].groupby("player").size()

        out = pd.DataFrame({
            "throughballs_attempted": attempted,
            "throughballs_completed": completed
        }).fillna(0).astype(int)

        out["completion_pct"] = (
                out["throughballs_completed"] / out["throughballs_attempted"] * 100
        ).replace([float("inf"), float("-inf")], 0).fillna(0).round(1)

        return out.sort_values("throughballs_attempted", ascending=False).head(n).reset_index()

    # ─────────────────────────────────────────────────────────────
    # Back-compat aliases (optional)
    # ─────────────────────────────────────────────────────────────
    def pass_success_rate(self, player: Optional[str] = None) -> float:
        return self.passing_percentage(player)

    def avg_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def average_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def long_ball_completed_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        return self.long_ball_percentage(player, min_len)

    def through_balls(self, player: Optional[str] = None) -> int:
        return self.throughballs(player)
