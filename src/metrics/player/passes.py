from __future__ import annotations
import pandas as pd

from src.metrics.base_metrics import BaseMetricSet
from src.metrics.shared.filters import filter_by_player


class PlayerPassMetrics(BaseMetricSet):
    """
    Player-level pass metrics (Phase 1). Same methods; no player arg needed because
    df is already filtered in __init__.
    """

    def __init__(self, df: pd.DataFrame, player_name: str):
        df = filter_by_player(df, player_name)
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
        self.player_name = player_name

    # ---------- core metrics ----------

    def passing_percentage(self) -> float:
        if self.df.empty:
            return 0.0
        attempted = len(self.df)
        completed = self._is_completed(self.df["pass_outcome"]).sum() if "pass_outcome" in self.df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    def pass_length(self) -> float:
        if "pass_length" not in self.df.columns or self.df.empty:
            return 0.0
        return float(self.df["pass_length"].mean())

    def successful_pass_length(self) -> float:
        need = {"pass_length", "pass_outcome"}
        if self.df.empty or not need.issubset(self.df.columns):
            return 0.0
        comp = self.df[self._is_completed(self.df["pass_outcome"])]
        return float(comp["pass_length"].mean()) if not comp.empty else 0.0

    def long_balls(self, min_len: float = 35.0) -> int:
        if "pass_length" not in self.df.columns or self.df.empty:
            return 0
        mask = self.df["pass_length"] >= min_len
        if "pass_outcome" in self.df.columns:
            mask = mask & self._is_completed(self.df["pass_outcome"])
        return int(mask.sum())

    def long_ball_percentage(self, min_len: float = 35.0) -> float:
        if "pass_length" not in self.df.columns or self.df.empty:
            return 0.0
        attempted = (self.df["pass_length"] >= min_len).sum()
        completed = ((self.df["pass_length"] >= min_len) & self._is_completed(self.df["pass_outcome"])).sum() \
            if "pass_outcome" in self.df.columns else 0
        return completed / attempted if attempted > 0 else 0.0

    def open_play_passes(self) -> int:
        if self.df.empty:
            return 0
        sp = self._is_set_piece(self.df)
        return int((~sp).sum())

    def passes_into_box(self, open_play: bool = False) -> int:
        need = {"pass_end_x", "pass_end_y", "pass_outcome"}
        if self.df.empty or not need.issubset(self.df.columns):
            return 0
        comp = self.df[self._is_completed(self.df["pass_outcome"])]
        if open_play:
            sp = self._is_set_piece(comp)
            comp = comp[~sp]
        if comp.empty:
            return 0
        in_box = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1)
        return int(in_box.sum())

    def op_passes_into_box(self) -> int:
        return self.passes_into_box(open_play=True)

    def passes_inside_box(self) -> int:
        need = {"x", "y", "pass_end_x", "pass_end_y", "pass_outcome"}
        if self.df.empty or not need.issubset(self.df.columns):
            return 0
        comp = self.df[self._is_completed(self.df["pass_outcome"])]
        if comp.empty:
            return 0
        start_in = comp.apply(lambda r: self._in_box(r["x"], r["y"]), axis=1)
        end_in   = comp.apply(lambda r: self._in_box(r["pass_end_x"], r["pass_end_y"]), axis=1)
        return int((start_in & end_in).sum())

    def throughballs_attempted(self) -> int:
        if self.df.empty:
            return 0
        return int(self._is_throughball_series(self.df).sum())

    def throughballs(self) -> int:
        if self.df.empty:
            return 0
        mask = self._is_throughball_series(self.df)
        if "pass_outcome" in self.df.columns:
            mask &= self._is_completed(self.df["pass_outcome"])
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

    # ---------- tops + aliases ----------

    def top_passers(self, n: int = 5) -> pd.DataFrame:
        # player-level: effectively returns self with count, but keep for API parity
        return self.top_n("player", n=n, value_name="passes")

    def top_assisters(self, n: int = 5) -> pd.DataFrame:
        return self.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=n, value_name="assists")

    def pass_success_rate(self) -> float:
        return self.passing_percentage()

    def avg_pass_length(self) -> float:
        return self.pass_length()

    def average_pass_length(self) -> float:
        return self.pass_length()

    def long_ball_completed_percentage(self, min_len: float = 35.0) -> float:
        return self.long_ball_percentage(min_len)

    def through_balls(self) -> int:
        return self.throughballs()
