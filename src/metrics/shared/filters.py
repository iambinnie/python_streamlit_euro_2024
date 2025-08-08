"""
Reusable DataFrame filters for metric sets.
"""

import pandas as pd


def filter_by_team(df: pd.DataFrame, team_name: str) -> pd.DataFrame:
    return df[df["team"] == team_name]


def filter_by_player(df: pd.DataFrame, player_name: str) -> pd.DataFrame:
    return df[df["player"] == player_name]


def filter_by_match(df: pd.DataFrame, match_id: int) -> pd.DataFrame:
    return df[df["match_id"] == match_id]
