"""
Reusable DataFrame filters for metric sets.
"""

import pandas as pd


def filter_by_team(df: pd.DataFrame, team: str) -> pd.DataFrame:
    return df[df["team"] == team].copy()

def filter_by_match(df: pd.DataFrame, match_id: int) -> pd.DataFrame:
    col = "match_id" if "match_id" in df.columns else "matchid"
    return df[df[col] == match_id].copy()

def filter_by_player(df: pd.DataFrame, player: str) -> pd.DataFrame:
    return df[df["player"] == player].copy()

def filter_by_match(df: pd.DataFrame, match_key) -> pd.DataFrame:
    """
    Accepts either a numeric match_id or a string match_name.
    """
    if isinstance(match_key, str) and "match_name" in df.columns:
        return df[df["match_name"] == match_key].copy()
    col = "match_id" if "match_id" in df.columns else "matchid"
    return df[df[col] == match_key].copy()

import pandas as pd

SET_PIECES = {"Corner", "Free Kick", "Throw-in"}
PATTERNS_SP = {"From Corner", "From Free Kick", "From Throw In"}

def filter_open_play(df: pd.DataFrame) -> pd.DataFrame:
    """Return only open-play rows when we can detect set pieces."""
    if "pass_type" in df.columns:
        return df[~df["pass_type"].isin(SET_PIECES)].copy()
    if "play_pattern" in df.columns:
        return df[~df["play_pattern"].isin(PATTERNS_SP)].copy()
    # If we can't detect, just return as-is
    return df.copy()

