# src/metrics/shared/minutes.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import pandas as pd

# Period offsets in minutes from actual match start
# 1: 0–45, 2: 45–90, 3: 90–105 (ET1), 4: 105–120 (ET2), 5: penalties (ignored for minutes on pitch)
PERIOD_OFFSET = {1: 0.0, 2: 45.0, 3: 90.0, 4: 105.0, 5: 120.0}

def _abs_minute(row: pd.Series) -> float:
    """Absolute minute from match start using period + minute + second."""
    period = int(row.get("period", 1)) if pd.notna(row.get("period", None)) else 1
    minute = float(row.get("minute", 0) or 0)
    second = float(row.get("second", 0) or 0)
    return PERIOD_OFFSET.get(period, 0.0) + minute + (second / 60.0)

def _col(df: pd.DataFrame, candidates: Tuple[str, ...]) -> Optional[str]:
    """Pick the first existing column among candidates."""
    for c in candidates:
        if c in df.columns:
            return c
    return None

@dataclass
class MinutesPlayedCalculator:
    """
    Compute minutes-on-pitch per player, per match, from event data.
    - Supports starters, substitutions, red cards.
    - Handles extra time via period offsets.
    - Ignores penalties (period=5) for minutes on pitch.
    """

    # Column names (auto-detected if None)
    player_col: Optional[str] = None
    team_col: Optional[str] = None
    match_key_col: Optional[str] = None  # prefers "match_name", falls back to "match_id"

    def compute(self, df: pd.DataFrame) -> Dict[str, float]:
        """
        Compute total minutes per player across the provided scope (can be one match or many).
        Returns: {player: minutes_played}
        """
        if df.empty:
            return {}

        # Resolve columns
        player_c = self.player_col or _col(df, ("player", "player_name"))
        team_c   = self.team_col   or _col(df, ("team", "team_name"))
        match_c  = self.match_key_col or _col(df, ("match_name", "match_id", "matchid"))
        type_c   = _col(df, ("type",))
        card_c   = _col(df, ("card_type", "foul_card", "foul_card_type"))
        subs_in_c  = _col(df, ("substitution_replacement", "substitution_replacement_name", "substitution_in"))
        # for robustness, the "player" on a Substitution row is commonly the player going OFF

        if not player_c or not type_c or not match_c:
            # Not enough info to compute minutes
            return {}

        # Work per match to avoid cross-match time overlaps
        minutes_total: Dict[str, float] = {}

        for match_key, mdf in df.groupby(match_c, dropna=False):
            # Track windows per player: (t_on, t_off)
            on_time: Dict[str, float] = {}
            off_time: Dict[str, float] = {}

            # 1) Assume all "Starting XI" players are on from 0:00 (period 1 start)
            starters = mdf[mdf[type_c] == "Starting XI"]
            if not starters.empty:
                for p in starters[player_c].dropna().unique():
                    on_time.setdefault(p, 0.0)

            # 2) Process events chronologically for subs and red cards
            mdf_sorted = mdf.sort_values(by=[match_c, "period", "minute", "second"], kind="mergesort")

            for _, row in mdf_sorted.iterrows():
                ev_type = row[type_c]
                p       = row.get(player_c, None)
                t_abs   = _abs_minute(row)

                # Substitution: player on this row is typically going OFF
                if ev_type == "Substitution":
                    # OFF: the event's player
                    if isinstance(p, str) and p:
                        # Only set if they were on; else ignore
                        if p in on_time and p not in off_time:
                            off_time[p] = max(off_time.get(p, 0.0), t_abs)

                    # ON: the replacement (if column exists)
                    if subs_in_c:
                        p_in = row.get(subs_in_c, None)
                        if isinstance(p_in, str) and p_in:
                            # Sub-on time cannot be before kickoff
                            on_time.setdefault(p_in, t_abs)

                # Red card / second yellow: treat as instant OFF
                if card_c and isinstance(row.get(card_c, None), str):
                    ct = row[card_c]
                    if ct in ("Red Card", "Second Yellow"):
                        if isinstance(p, str) and p:
                            if p in on_time and p not in off_time:
                                off_time[p] = max(off_time.get(p, 0.0), t_abs)

            # 3) Close any still-on players at match end (including extra time)
            # Match end = latest absolute minute seen in this match, clamped to <= 120
            if not mdf_sorted.empty:
                last_row = mdf_sorted.iloc[-1]
                match_end = min(_abs_minute(last_row), 120.0)
            else:
                match_end = 90.0

            for p, t_on in on_time.items():
                t_off = off_time.get(p, match_end)
                played = max(0.0, t_off - t_on)
                minutes_total[p] = minutes_total.get(p, 0.0) + played

        return minutes_total
