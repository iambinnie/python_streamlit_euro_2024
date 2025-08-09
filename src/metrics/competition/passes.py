# src/metrics/competition/passes.py
from typing import Optional

from src.metrics.base_metrics import BaseMetricSet
import pandas as pd


class CompetitionPassMetrics(BaseMetricSet):
    """
       Phase 1: Easy + high-value passing metrics
       - Passing%
       - Pass Length
       - Successful Pass Length
       - Long Balls
       - Long Ball%
       - Open Play Passes
       - OP Passes Into Box (Open Play)
       - Passes Into Box
       - Passes Inside Box
       - Throughballs
       """
    def __init__(self, df: pd.DataFrame):
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
    # ---------- small helpers ----------
    @staticmethod
    def _is_completed(series: pd.Series) -> pd.Series:
        # StatsBomb convention: completed passes have NaN in pass_outcome
        return series.isna()

    @staticmethod
    def _is_set_piece(df: pd.DataFrame) -> pd.Series:
        # Prefer pass_type if present; fall back to play_pattern if needed.
        if "pass_type" in df.columns:
            return df["pass_type"].isin(["Corner", "Free Kick", "Throw-in"])
        if "play_pattern" in df.columns:
            # Simple fallback: treat set-piece patterns as SP (you can refine later)
            return df["play_pattern"].isin(["From Corner", "From Free Kick", "From Throw In"])
        # No column = assume open play (no set piece)
        return pd.Series(False, index=df.index)

    @staticmethod
    def _in_box(x: float, y: float) -> bool:
        # Using Hudl/StatsBomb glossary thresholds (units 120x80 scaled to 120/80?):
        # Here we're using the values you pasted: x>=102 and 18<=y<=62
        return (pd.notna(x) and pd.notna(y) and (x >= 102) and (18 <= y <= 62))

    # ---------- Phase 1 metrics (canonical names match glossary) ----------

    def passing_percentage(self, player: Optional[str] = None) -> float:
        # canonical for “Passing%”
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0.0
        attempted = len(df)
        completed = self._is_completed(df["pass_outcome"]).sum() if "pass_outcome" in df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    # Back-compat/aliases
    def pass_complete_percentage(self, player: Optional[str] = None) -> float:
        return self.passing_percentage(player)

    def pass_success_rate(self, player: Optional[str] = None) -> float:
        # keep this alias since you already call it elsewhere
        return self.passing_percentage(player)

    def pass_length(self, player: Optional[str] = None) -> float:
        # canonical for “Pass Length”
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0.0
        return float(df["pass_length"].mean())

    # Back-compat/aliases
    def avg_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def average_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def successful_pass_length(self, player: Optional[str] = None) -> float:
        # canonical for “Successful Pass Length”
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or "pass_outcome" not in df.columns or df.empty:
            return 0.0
        comp = df[self._is_completed(df["pass_outcome"])]
        if comp.empty:
            return 0.0
        return float(comp["pass_length"].mean())

    def long_balls(self, player: Optional[str] = None, min_len: float = 35.0) -> int:
        # canonical for “Long Balls” (completed ≥ min_len)
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0
        mask = (df["pass_length"] >= min_len)
        if "pass_outcome" in df.columns:
            mask = mask & self._is_completed(df["pass_outcome"])
        return int(mask.sum())

    def long_ball_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        # canonical for “Long Ball%”
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0.0
        attempted = (df["pass_length"] >= min_len).sum()
        completed = ((df["pass_length"] >= min_len) & self._is_completed(df["pass_outcome"])).sum() \
            if "pass_outcome" in df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    # Back-compat alias
    def long_ball_completed_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        return self.long_ball_percentage(player, min_len)

    def throughballs_attempted(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        return int(self._is_throughball_series(df).sum())

    def throughballs(self, player: Optional[str] = None) -> int:
        # Completed through-balls (glossary)
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        mask = self._is_throughball_series(df)
        if "pass_outcome" in df.columns:
            mask &= self._is_completed(df["pass_outcome"])
        return int(mask.sum())

    # Back-compat alias
    def through_balls(self, player: Optional[str] = None) -> int:
        return self.throughballs(player)

    def throughballs_completion_percentage(self, player: str | None = None) -> float:
        # Player class: drop the `player` arg and use self.df
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0.0
        attempted = self._is_throughball_series(df).sum()
        if attempted == 0:
            return 0.0
        completed = (self._is_throughball_series(df) & self._is_completed(
            df.get("pass_outcome", pd.Series(index=df.index)))).sum()
        return completed / attempted

    def top_throughball_creators(self, n: int = 5) -> pd.DataFrame:
        df = self.df
        if df.empty or "player" not in df.columns:
            return pd.DataFrame(columns=[
                "player",
                "throughballs_attempted",
                "throughballs_completed",
                "completion_pct"
            ])

        is_tb = self._is_throughball_series(df)
        attempted = df[is_tb].groupby("player").size()
        completed = df[is_tb & self._is_completed(df.get("pass_outcome", pd.Series(index=df.index)))].groupby(
            "player").size()

        out = pd.DataFrame({
            "throughballs_attempted": attempted,
            "throughballs_completed": completed
        }).fillna(0).astype(int)

        # Calculate completion percentage
        out["completion_pct"] = (out["throughballs_completed"] / out["throughballs_attempted"]) * 100
        out["completion_pct"] = out["completion_pct"].fillna(0).round(1)  # round to 1 decimal place

        return out.sort_values("throughballs_attempted", ascending=False).head(n).reset_index()

    def open_play_passes(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        sp = self._is_set_piece(df)
        return int((~sp).sum())

    def passes_into_box(self, player: Optional[str] = None, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        need_cols = {"pass_end_x", "pass_end_y", "pass_outcome"}
        if df.empty or not need_cols.issubset(df.columns):
            return 0
        comp = df[self._is_completed(df["pass_outcome"])]
        if open_play:
            sp = self._is_set_piece(comp)
            comp = comp[~sp]
        if comp.empty:
            return 0
        in_box_counts = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1).sum()
        return int(in_box_counts)

    def op_passes_into_box(self, player: Optional[str] = None) -> int:
        # Glossary: “OP Passes Into Box”
        return self.passes_into_box(player=player, open_play=True)

    def passes_inside_box(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        need = {"x", "y", "pass_end_x", "pass_end_y", "pass_outcome"}
        if df.empty or not need.issubset(df.columns):
            return 0
        comp = df[self._is_completed(df["pass_outcome"])]
        if comp.empty:
            return 0
        start_in = comp.apply(lambda r: self._in_box(r["x"], r["y"]), axis=1)
        end_in = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1)
        return int((start_in & end_in).sum())

    # existing top/assist methods unchanged
    def top_passers(self, n: int = 5) -> pd.DataFrame:
        return self.top_n("player", n=n, value_name="passes")

    def top_assisters(self, n: int = 5) -> pd.DataFrame:
        return self.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=n, value_name="assists")
