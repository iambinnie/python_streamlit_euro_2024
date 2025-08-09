from __future__ import annotations
from typing import Optional
import pandas as pd

from src.metrics.base_metrics import BaseMetricSet
from src.metrics.shared.filters import filter_by_team


class TeamPassMetrics(BaseMetricSet):
    """
    Team-level pass metrics (Phase 1)
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

    Also: top_passers, top_assisters, aliases for back-compat.
    """

    def __init__(self, df: pd.DataFrame, team_name: str):
        df = filter_by_team(df, team_name)
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
        self.team_name = team_name

    # ---------- core metrics (glossary-aligned) ----------

    def passing_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0.0
        attempted = len(df)
        completed = self._is_completed(df["pass_outcome"]).sum() if "pass_outcome" in df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    def pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0.0
        return float(df["pass_length"].mean())

    def successful_pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        need = {"pass_length", "pass_outcome"}
        if df.empty or not need.issubset(df.columns):
            return 0.0
        comp = df[self._is_completed(df["pass_outcome"])]
        return float(comp["pass_length"].mean()) if not comp.empty else 0.0

    def long_balls(self, player: Optional[str] = None, min_len: float = 35.0) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0
        mask = df["pass_length"] >= min_len
        if "pass_outcome" in df.columns:
            mask = mask & self._is_completed(df["pass_outcome"])
        return int(mask.sum())

    def long_ball_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if "pass_length" not in df.columns or df.empty:
            return 0.0
        attempted = (df["pass_length"] >= min_len).sum()
        completed = ((df["pass_length"] >= min_len) & self._is_completed(df["pass_outcome"])).sum() \
            if "pass_outcome" in df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    def open_play_passes(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        sp = self._is_set_piece(df)
        return int((~sp).sum())

    def passes_into_box(self, player: Optional[str] = None, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        need = {"pass_end_x", "pass_end_y", "pass_outcome"}
        if df.empty or not need.issubset(df.columns):
            return 0
        comp = df[self._is_completed(df["pass_outcome"])]
        if open_play:
            sp = self._is_set_piece(comp)
            comp = comp[~sp]
        if comp.empty:
            return 0
        in_box = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1)
        return int(in_box.sum())

    def op_passes_into_box(self, player: Optional[str] = None) -> int:
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
        end_in   = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1)
        return int((start_in & end_in).sum())

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

    # ---------- top summaries + aliases ----------

    def top_passers(self, n: int = 5) -> pd.DataFrame:
        return self.top_n("player", n=n, value_name="passes")

    def top_assisters(self, n: int = 5) -> pd.DataFrame:
        return self.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=n, value_name="assists")

    def pass_success_rate(self, player: Optional[str] = None) -> float:
        # alias to glossary “Passing%”
        return self.passing_percentage(player)

    def avg_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def average_pass_length(self, player: Optional[str] = None) -> float:
        return self.pass_length(player)

    def long_ball_completed_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        return self.long_ball_percentage(player, min_len)

    def through_balls(self, player: Optional[str] = None) -> int:
        return self.throughballs(player)
