# src/metrics/passes_core.py
from __future__ import annotations
from typing import Optional, Dict, Hashable, Tuple
import pandas as pd
import numpy as np

from src.metrics.base_metrics import BaseMetricSet


class PassMetricsCore(BaseMetricSet):
    """
    Phase-1 + Phase-2 passing metrics.
    Adds directional percentages & attempts for defensive (D3), middle (M3), and final third (F3).
    Per-90 plumbing avoids 0.00 results when minutes are missing by using a safe fallback.

    Notes on thirds:
      - Third boundaries are inferred from the data's x-range (max x). We split at ~1/3 and ~2/3.
      - Works for both 0–120 and 0–100 coordinate systems.
    """

    # ─────────────────────────────────────────────────────────────
    # Per-90 minutes plumbing & safe fallback
    # ─────────────────────────────────────────────────────────────
    DEFAULT_MATCH_MINUTES: float = 90.0

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        minutes_map: Optional[Dict[Hashable, float]] = None,
        key_col: str = "player",
    ):
        """
        Args:
            df: events dataframe (can be all events; BaseMetricSet will filter to 'Pass').
            minutes_map: optional {key -> minutes} for per-90; if None, a safe fallback is computed.
            key_col: column used to index minutes (defaults to 'player').
        """
        super().__init__(df, event_type="Pass", outcome_column="pass_outcome")
        self._key_col = key_col
        self._minutes_map = self._resolve_minutes_map(minutes_map)

    def _fallback_minutes_map(self) -> Dict[Hashable, float]:
        """
        Fallback: assume DEFAULT_MATCH_MINUTES for each distinct match the key appears in.
        Requires presence of `match_id`; if missing, assume one match (i.e., 90 minutes).
        """
        if self.df.empty or self._key_col not in self.df.columns:
            return {}

        if "match_id" not in self.df.columns:
            keys = self.df[self._key_col].dropna().unique().tolist()
            return {k: self.DEFAULT_MATCH_MINUTES for k in keys}

        counts = (
            self.df[[self._key_col, "match_id"]]
            .dropna()
            .drop_duplicates()
            .groupby(self._key_col)["match_id"]
            .nunique()
            .rename("n_matches")
        )
        return (counts * self.DEFAULT_MATCH_MINUTES).to_dict()

    def _resolve_minutes_map(self, minutes_map: Optional[Dict[Hashable, float]]) -> Dict[Hashable, float]:
        if minutes_map is not None:
            return dict(minutes_map)
        return self._fallback_minutes_map()

    def _per90(self, value: float, key: Hashable) -> float:
        """
        Convert a count/sum to per-90 using the resolved minutes map.
        Guards against missing/zero minutes.
        """
        mins = float(self._minutes_map.get(key, self.DEFAULT_MATCH_MINUTES))
        if mins <= 0:
            mins = self.DEFAULT_MATCH_MINUTES
        return (float(value) * 90.0) / mins

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
                truthy = {"true", "1", "yes", "y", "t"}
                tb_flag = col.astype(str).str.strip().str.lower().isin(truthy)
            mask |= tb_flag.fillna(False)

        if "pass_technique" in df.columns:
            tech = df["pass_technique"].astype(str).str.lower().str.strip()
            mask |= tech.str.contains(r"\bthrough[- ]?ball\b", regex=True, na=False)

        return mask

    # ─────────────────────────────────────────────────────────────
    # Helper: angle buckets + zone membership (D3/M3/F3)
    # ─────────────────────────────────────────────────────────────
    def _third_bounds(self, df: pd.DataFrame, xcol: str) -> Tuple[float, float]:
        """
        Compute split bounds (t1, t2) as ~1/3 and ~2/3 of the observed max x.
        Works for 0–120 or 0–100 coordinate systems.
        """
        if xcol not in df.columns or df.empty:
            return (40.0, 80.0)  # sensible default for 0–120
        x = pd.to_numeric(df[xcol], errors="coerce")
        max_x = float(x.max()) if np.isfinite(x.max()) else 120.0
        if max_x <= 0:
            max_x = 120.0
        t1, t2 = max_x / 3.0, 2.0 * max_x / 3.0
        return (t1, t2)

    def _zone_series(self, df: pd.DataFrame, xcol: str, zone: str) -> pd.Series:
        """
        Return boolean mask for the x-column being in a named zone:
          - 'D3' : defensive third (x < t1)
          - 'M3' : middle third    (t1 <= x < t2)
          - 'F3' : final third     (x >= t2)
        """
        if df.empty or xcol not in df.columns:
            return pd.Series(False, index=df.index)
        x = pd.to_numeric(df[xcol], errors="coerce")
        t1, t2 = self._third_bounds(df, xcol)
        if zone == "D3":
            return x < t1
        if zone == "M3":
            return (x >= t1) & (x < t2)
        if zone == "F3":
            return x >= t2
        return pd.Series(False, index=df.index)

    def _direction_masks_by_zone(
        self, df: pd.DataFrame, zone: str
    ) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Returns (denom_mask, forward_mask, sideways_mask, backward_mask) for the given zone.
        - Angles from pass vector (x,y → pass_end_x, pass_end_y)
        - Forward:  -π/6 <= θ <=  π/6
        - Backward: θ >= 5π/6  or θ <= -5π/6
        - Sideways: remaining within denom
        - Denominator: passes where start OR end is inside the requested zone.
        """
        theta = self.pass_angle_series(df)
        valid_angle = theta.notna()

        start_zone = self._zone_series(df, "x", zone)
        end_zone = self._zone_series(df, "pass_end_x", zone)
        denom = valid_angle & (start_zone | end_zone)

        forward = denom & (theta >= -np.pi / 6) & (theta <= np.pi / 6)
        backward = denom & ((theta >= 5 * np.pi / 6) | (theta <= -5 * np.pi / 6))
        sideways = denom & ~(forward | backward)

        return denom, forward, sideways, backward

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
        comp = self._is_success(df)
        return self.mean_of(df, "pass_length", comp)

    def long_balls(self, player: Optional[str] = None, min_len: float = 35.0) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        long_mask = (df["pass_length"] >= min_len) if "pass_length" in df.columns else None
        comp = self._is_success(df)
        return self.attempts(df, long_mask, comp)

    def long_ball_percentage(self, player: Optional[str] = None, min_len: float = 35.0) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        long_mask = (df["pass_length"] >= min_len) if "pass_length" in df.columns else None
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

        comp = self._is_success(df)

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
    # Directional percentages – final third (existing, kept)
    # ─────────────────────────────────────────────────────────────
    def _direction_masks(self, df: pd.DataFrame, *, final_third: bool = False) -> tuple[
        pd.Series, pd.Series, pd.Series, pd.Series]:
        """
        Legacy helper kept for back-compat (final-third only).
        """
        theta = self.pass_angle_series(df)
        valid_angle = theta.notna()

        if final_third:
            in_f3 = self.final_third_series(df, "x")
            end_f3 = self.final_third_series(df, "pass_end_x")
            denom = valid_angle & (in_f3 | end_f3)
        else:
            denom = valid_angle

        forward = denom & (theta >= -np.pi / 6) & (theta <= np.pi / 6)
        backward = denom & ((theta >= 5 * np.pi / 6) | (theta <= -5 * np.pi / 6))
        sideways = denom & ~(forward | backward)

        return denom, forward, sideways, backward

    # final third (attempt-based %)
    def f3_pass_forward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, forward, _, _ = self._direction_masks(df, final_third=True)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(forward.sum()) / att

    def f3_pass_sideways_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, _, sideways, _ = self._direction_masks(df, final_third=True)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(sideways.sum()) / att

    def f3_pass_backward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, _, _, backward = self._direction_masks(df, final_third=True)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(backward.sum()) / att

    # ─────────────────────────────────────────────────────────────
    # NEW: Directional percentages – defensive & middle third
    # ─────────────────────────────────────────────────────────────
    def d3_pass_forward_percentage(self, player: Optional[str] = None) -> float:
        """Attempt-based directional share for passes in the DEFENSIVE third."""
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, forward, _, _ = self._direction_masks_by_zone(df, "D3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(forward.sum()) / att

    def d3_pass_sideways_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, _, sideways, _ = self._direction_masks_by_zone(df, "D3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(sideways.sum()) / att

    def d3_pass_backward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, _, _, backward = self._direction_masks_by_zone(df, "D3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(backward.sum()) / att

    def m3_pass_forward_percentage(self, player: Optional[str] = None) -> float:
        """Attempt-based directional share for passes in the MIDDLE third."""
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, forward, _, _ = self._direction_masks_by_zone(df, "M3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(forward.sum()) / att

    def m3_pass_sideways_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, _, sideways, _ = self._direction_masks_by_zone(df, "M3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(sideways.sum()) / att

    def m3_pass_backward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0.0
        denom, _, _, backward = self._direction_masks_by_zone(df, "M3")
        att = int(denom.sum())
        return 0.0 if att == 0 else int(backward.sum()) / att

    # ─────────────────────────────────────────────────────────────
    # NEW: Directional ATTEMPTS – defensive/middle/final third
    # ─────────────────────────────────────────────────────────────
    def d3_pass_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        denom, _, _, _ = self._direction_masks_by_zone(df, "D3")
        return int(denom.sum())

    def d3_pass_forward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, forward, _, _ = self._direction_masks_by_zone(df, "D3")
        return int(forward.sum())

    def d3_pass_sideways_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, sideways, _ = self._direction_masks_by_zone(df, "D3")
        return int(sideways.sum())

    def d3_pass_backward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, _, backward = self._direction_masks_by_zone(df, "D3")
        return int(backward.sum())

    def m3_pass_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        denom, _, _, _ = self._direction_masks_by_zone(df, "M3")
        return int(denom.sum())

    def m3_pass_forward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, forward, _, _ = self._direction_masks_by_zone(df, "M3")
        return int(forward.sum())

    def m3_pass_sideways_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, sideways, _ = self._direction_masks_by_zone(df, "M3")
        return int(sideways.sum())

    def m3_pass_backward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, _, backward = self._direction_masks_by_zone(df, "M3")
        return int(backward.sum())

    def f3_pass_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        denom, _, _, _ = self._direction_masks_by_zone(df, "F3")
        return int(denom.sum())

    def f3_pass_forward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, forward, _, _ = self._direction_masks_by_zone(df, "F3")
        return int(forward.sum())

    def f3_pass_sideways_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, sideways, _ = self._direction_masks_by_zone(df, "F3")
        return int(sideways.sum())

    def f3_pass_backward_attempts(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty: return 0
        _, _, _, backward = self._direction_masks_by_zone(df, "F3")
        return int(backward.sum())

    # ─────────────────────────────────────────────────────────────
    # NEW: Per-90 versions of directional ATTEMPTS per third
    # ─────────────────────────────────────────────────────────────
    def d3_pass_attempts_per90(self, player: str) -> float:
        return self._per90(self.d3_pass_attempts(player), player)

    def d3_pass_forward_attempts_per90(self, player: str) -> float:
        return self._per90(self.d3_pass_forward_attempts(player), player)

    def d3_pass_sideways_attempts_per90(self, player: str) -> float:
        return self._per90(self.d3_pass_sideways_attempts(player), player)

    def d3_pass_backward_attempts_per90(self, player: str) -> float:
        return self._per90(self.d3_pass_backward_attempts(player), player)

    def m3_pass_attempts_per90(self, player: str) -> float:
        return self._per90(self.m3_pass_attempts(player), player)

    def m3_pass_forward_attempts_per90(self, player: str) -> float:
        return self._per90(self.m3_pass_forward_attempts(player), player)

    def m3_pass_sideways_attempts_per90(self, player: str) -> float:
        return self._per90(self.m3_pass_sideways_attempts(player), player)

    def m3_pass_backward_attempts_per90(self, player: str) -> float:
        return self._per90(self.m3_pass_backward_attempts(player), player)

    def f3_pass_attempts_per90(self, player: str) -> float:
        return self._per90(self.f3_pass_attempts(player), player)

    def f3_pass_forward_attempts_per90(self, player: str) -> float:
        return self._per90(self.f3_pass_forward_attempts(player), player)

    def f3_pass_sideways_attempts_per90(self, player: str) -> float:
        return self._per90(self.f3_pass_sideways_attempts(player), player)

    def f3_pass_backward_attempts_per90(self, player: str) -> float:
        return self._per90(self.f3_pass_backward_attempts(player), player)

    # ─────────────────────────────────────────────────────────────
    # Whole-pitch direction splits (attempt-based)
    # ─────────────────────────────────────────────────────────────
    def pass_forward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, forward, _, _ = self._direction_masks(df, final_third=False)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(forward.sum()) / att

    def pass_sideways_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, _, sideways, _ = self._direction_masks(df, final_third=False)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(sideways.sum()) / att

    def pass_backward_percentage(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        denom, _, _, backward = self._direction_masks(df, final_third=False)
        att = int(denom.sum())
        return 0.0 if att == 0 else int(backward.sum()) / att

    # ── Phase 2: Pressure-related passing metrics ──────────────────────────

    def passes_pressured_percentage(self, player: Optional[str] = None) -> float:
        """
        Of COMPLETED passes, what share were made under pressure?
        """
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty or "under_pressure" not in df.columns:
            return 0.0
        comp = self._is_success(df)
        prs = self.mask_pressured(df)
        completed_total = int(comp.sum())
        if completed_total == 0:
            return 0.0
        completed_pressured = int((comp & prs).sum())
        return completed_pressured / completed_total

    def pressured_pass_percentage(self, player: Optional[str] = None) -> float:
        """
        Among passes ATTEMPTED under pressure, what fraction were completed?
        """
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty or "under_pressure" not in df.columns:
            return 0.0
        prs = self.mask_pressured(df)
        comp = self._is_success(df)
        pressured_attempts = int(prs.sum())
        if pressured_attempts == 0:
            return 0.0
        pressured_completed = int((prs & comp).sum())
        return pressured_completed / pressured_attempts

    def pressured_pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty or "under_pressure" not in df.columns:
            return 0.0
        prs = self.mask_pressured(df)
        return self.mean_of(df, "pass_length", prs)

    def successful_pressured_pass_length(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty or "under_pressure" not in df.columns:
            return 0.0
        prs = self.mask_pressured(df)
        comp = self._is_success(df)
        return self.mean_of(df, "pass_length", prs, comp)

    def pressured_pass_length_difference(self, player: Optional[str] = None) -> float:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty or "under_pressure" not in df.columns:
            return 0.0
        prs = self.mask_pressured(df)
        pr_len = self.mean_of(df, "pass_length", prs)
        all_len = self.mean_of(df, "pass_length")
        return pr_len - all_len

    def pressured_pass_percent_difference(self, player: Optional[str] = None) -> float:
        return self.pressured_pass_percentage(player) - self.passing_percentage(player)

    # ---- Passes Into Box (attempted/completed/%) ----
    def passes_into_box_attempted(self, player: Optional[str] = None, *, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        end_in_box = self.in_box_series(df, "pass_end_x", "pass_end_y")
        masks = [end_in_box]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    def passes_into_box_completed(self, player: Optional[str] = None, *, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        end_in_box = self.in_box_series(df, "pass_end_x", "pass_end_y")
        comp = self._is_success(df)
        masks = [end_in_box, comp]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    def passes_into_box_completion_percentage(self, player: Optional[str] = None, *, open_play: bool = False) -> float:
        att = self.passes_into_box_attempted(player, open_play=open_play)
        if att == 0:
            return 0.0
        comp = self.passes_into_box_completed(player, open_play=open_play)
        return comp / att

    def op_passes_into_box_attempted(self, player: Optional[str] = None) -> int:
        return self.passes_into_box_attempted(player, open_play=True)

    def op_passes_into_box_completed(self, player: Optional[str] = None) -> int:
        return self.passes_into_box_completed(player, open_play=True)

    def op_passes_into_box_completion_percentage(self, player: Optional[str] = None) -> float:
        return self.passes_into_box_completion_percentage(player, open_play=True)

    # ---- Passes Inside Box (attempted/completed/%) ----
    def passes_inside_box_attempted(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        start_in = self.in_box_series(df, "x", "y")
        end_in = self.in_box_series(df, "pass_end_x", "pass_end_y")
        return self.attempts(df, start_in, end_in)

    def passes_inside_box_completed(self, player: Optional[str] = None) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        start_in = self.in_box_series(df, "x", "y")
        end_in = self.in_box_series(df, "pass_end_x", "pass_end_y")
        comp = self._is_success(df)
        return self.attempts(df, start_in, end_in, comp)

    def passes_inside_box_completion_percentage(self, player: Optional[str] = None) -> float:
        att = self.passes_inside_box_attempted(player)
        if att == 0:
            return 0.0
        comp = self.passes_inside_box_completed(player)
        return comp / att

    # ---- Deep Progressions (pass-only) ----
    def pass_deep_progressions_attempted(self, player: Optional[str] = None, *, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        from_buildup = ~self._zone_series(df, "x", "F3")   # start outside F3
        into_f3 = self._zone_series(df, "pass_end_x", "F3")  # end inside F3
        masks = [from_buildup, into_f3]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    def pass_deep_progressions(self, player: Optional[str] = None, *, open_play: bool = False) -> int:
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        from_buildup = ~self._zone_series(df, "x", "F3")
        into_f3 = self._zone_series(df, "pass_end_x", "F3")
        comp = self._is_success(df)
        masks = [from_buildup, into_f3, comp]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    def pass_deep_progressions_completion_percentage(self, player: Optional[str] = None, *, open_play: bool = False) -> float:
        att = self.pass_deep_progressions_attempted(player, open_play=open_play)
        if att == 0:
            return 0.0
        comp = self.pass_deep_progressions(player, open_play=open_play)
        return comp / att

    def op_final_third_passes(self, player: Optional[str] = None) -> int:
        """Successful final-third passes in open play (glossary: OP F3 Passes)."""
        return self.final_third_passes(player, open_play=True)

    def final_third_passes(self, player: Optional[str] = None, *, open_play: bool = False) -> int:
        """
        Count of *completed* passes where start OR end is in the final third.
        If open_play=True, excludes set pieces.
        """
        df = self.df if player is None else self.df[self.df["player"] == player]
        if df.empty:
            return 0
        start_f3 = self._zone_series(df, "x", "F3")
        end_f3 = self._zone_series(df, "pass_end_x", "F3")
        comp = self._is_success(df)
        masks = [start_f3 | end_f3, comp]
        if open_play:
            masks.append(self.mask_open_play(df))
        return self.attempts(df, *masks)

    # ── Per-90 wrappers for radar-friendly passing metrics ─────────
    def op_final_third_passes_per90(self, player: str) -> float:
        return self._per90(self.op_final_third_passes(player), player)

    def passes_into_box_completed_per90(self, player: str) -> float:
        return self._per90(self.passes_into_box_completed(player), player)

    def op_passes_into_box_completed_per90(self, player: str) -> float:
        return self._per90(self.passes_into_box_completed(player, open_play=True), player)

    def passes_inside_box_completed_per90(self, player: str) -> float:
        return self._per90(self.passes_inside_box_completed(player), player)

    def pass_deep_progressions_attempted_per90(self, player: str, *, open_play: bool = False) -> float:
        return self._per90(self.pass_deep_progressions_attempted(player, open_play=open_play), player)

    def pass_deep_progressions_per90(self, player: str, *, open_play: bool = False) -> float:
        return self._per90(self.pass_deep_progressions(player, open_play=open_play), player)

    def op_pass_deep_progressions_attempted_per90(self, player: str) -> float:
        return self.pass_deep_progressions_attempted_per90(player, open_play=True)

    def op_pass_deep_progressions_per90(self, player: str) -> float:
        return self.pass_deep_progressions_per90(player, open_play=True)

    def throughballs_attempted_per90(self, player: str) -> float:
        return self._per90(self.throughballs_attempted(player), player)

    def throughballs_per90(self, player: str) -> float:
        return self._per90(self.throughballs(player), player)
