"""
per_90.py
---------
Reusable helpers for normalising metrics by minutes played.

Provides:
- apply_per90: generic per-90 normalisation.
- approx_minutes_from_events: coarse fallback for players (distinct event-minutes).
- approx_team_minutes_from_matches: robust team fallback using match durations.

Usage:
    from src.metrics.shared.per_90 import (
        apply_per90,
        approx_minutes_from_events,
        approx_team_minutes_from_matches,
    )
"""

from __future__ import annotations
from typing import List, Optional
import pandas as pd


def apply_per90(
    agg_df: pd.DataFrame,
    minutes_df: pd.DataFrame,
    group_cols: List[str],
    minutes_col: str = "minutes_played",
    suffix: str = "_per90",
    clip_floor_minutes: int = 1,
) -> pd.DataFrame:
    if not set(group_cols).issubset(agg_df.columns):
        missing = set(group_cols) - set(agg_df.columns)
        raise ValueError(f"agg_df missing group_cols: {missing}")

    if not set(group_cols + [minutes_col]).issubset(minutes_df.columns):
        missing = set(group_cols + [minutes_col]) - set(minutes_df.columns)
        raise ValueError(f"minutes_df missing cols: {missing}")

    out = agg_df.merge(minutes_df[group_cols + [minutes_col]], on=group_cols, how="left")
    out[minutes_col] = out[minutes_col].fillna(0).clip(lower=clip_floor_minutes)

    numeric_cols = [
        c for c in out.columns
        if c not in group_cols and c != minutes_col and pd.api.types.is_numeric_dtype(out[c])
    ]
    for c in numeric_cols:
        out[f"{c}{suffix}"] = out[c] * (90.0 / out[minutes_col])
    return out


def approx_minutes_from_events(
    events: pd.DataFrame,
    group_cols: List[str],
    minute_col: str = "minute",
    minutes_col_out: str = "minutes_played",
    per_match_cap: Optional[int] = 120,
) -> pd.DataFrame:
    """
    Coarse fallback — best for PLAYERS:
    Counts distinct minutes with any event for the entity. Under-counts quiet periods.
    """
    req = set(group_cols + [minute_col])
    if not req.issubset(events.columns):
        missing = req - set(events.columns)
        raise ValueError(f"events missing columns: {missing}")

    tmp = (
        events[group_cols + [minute_col]]
        .drop_duplicates()
        .groupby(group_cols, as_index=False)[minute_col]
        .count()
        .rename(columns={minute_col: minutes_col_out})
    )

    if per_match_cap and "match_id" in group_cols:
        tmp[minutes_col_out] = tmp[minutes_col_out].clip(upper=per_match_cap)

    return tmp


def approx_team_minutes_from_matches(
    events: pd.DataFrame,
    team_col: str = "team_id",
    match_col: str = "match_id",
    minute_col: str = "minute",
    second_col: Optional[str] = "second",
    minutes_col_out: str = "minutes_played",
    per_match_cap: int = 120,
) -> pd.DataFrame:
    """
    Robust TEAM fallback:
    1) Compute each match's duration from ALL events in that match (max minute+second).
    2) Attribute that duration to each team that appeared in the match.
    3) Sum across matches for team totals.

    Returns: DataFrame[[team_col, minutes_col_out]]
    """
    needed = {team_col, match_col, minute_col}
    if not needed.issubset(events.columns):
        missing = needed - set(events.columns)
        raise ValueError(f"events missing columns: {missing}")

    ev = events[[team_col, match_col, minute_col] + ([second_col] if second_col and second_col in events.columns else [])].copy()

    # 1) Per-match duration (use seconds if available for better precision)
    if second_col and second_col in ev.columns:
        ev["_minute_exact"] = ev[minute_col].astype(float) + (ev[second_col].astype(float) / 60.0)
    else:
        ev["_minute_exact"] = ev[minute_col].astype(float)

    per_match_minutes = (
        ev.groupby(match_col, as_index=False)["_minute_exact"].max()
        .rename(columns={"_minute_exact": "match_minutes"})
    )
    per_match_minutes["match_minutes"] = per_match_minutes["match_minutes"].clip(upper=float(per_match_cap))

    # 2) Teams per match
    teams_in_match = ev[[match_col, team_col]].drop_duplicates()

    team_match_minutes = teams_in_match.merge(per_match_minutes, on=match_col, how="left")

    # 3) Sum per team
    team_minutes = (
        team_match_minutes.groupby(team_col, as_index=False)["match_minutes"].sum()
        .rename(columns={"match_minutes": minutes_col_out})
    )
    return team_minutes
