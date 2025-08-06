# src/streamlit/shared/team_helpers.py
import pandas as pd
from src.config.team_flag_mapping import TEAM_TO_FLAG_CODE  # We'll define this
from typing import Literal

def flag_emoji_from_code(code: str) -> str:
    """Convert ISO 3166 alpha-2 country code to emoji flag."""
    if not code or len(code) != 2:
        return ""
    return chr(127397 + ord(code[0].upper())) + chr(127397 + ord(code[1].upper()))

from src.config.team_flag_mapping import TEAM_TO_FLAG_CODE

def add_team_flag_column(
    df: pd.DataFrame,
    team_col: str = "team",
    new_col: str = "team_flag",
    position: Literal["before", "after", "replace"] = "before",
) -> pd.DataFrame:
    df = df.copy()
    flag_series = df[team_col].map(
        lambda name: cdn_flag_img(TEAM_TO_FLAG_CODE.get(str(name), ""))
    )

    if position == "replace":
        df[team_col] = flag_series + " " + df[team_col]
    else:
        df[new_col] = flag_series
        cols = df.columns.tolist()
        idx = cols.index(team_col)
        if position == "before":
            new_order = cols[:idx] + [new_col] + cols[idx:]
        else:
            new_order = cols[:idx + 1] + [new_col] + cols[idx + 1:]
        df = df[new_order]

    return df



# def add_team_flag_column(
#     df: pd.DataFrame,
#     team_col: str = "team",
#     new_col: str = "team_flag",
#     position: Literal["before", "after", "replace"] = "before",
# ) -> pd.DataFrame:
#     """
#     Adds a new column with emoji flags based on team names using TEAM_TO_FLAG_CODE.
#     `position` can be 'before', 'after', or 'replace' relative to team_col.
#     """
#     df = df.copy()
#
#     flag_series = df[team_col].map(lambda name: flag_emoji_from_code(TEAM_TO_FLAG_CODE.get(str(name), "")))
#
#     if position == "replace":
#         df[team_col] = flag_series + " " + df[team_col]
#     else:
#         df[new_col] = flag_series
#         cols = df.columns.tolist()
#         idx = cols.index(team_col)
#         if position == "before":
#             new_order = cols[:idx] + [new_col] + cols[idx:]
#         else:
#             new_order = cols[:idx + 1] + [new_col] + cols[idx + 1:]
#         df = df[new_order]
#
#     return df

def cdn_flag_img(code: str, width: int = 28, height: int = 21) -> str:
    """
    Return an HTML <img> tag for the country flag using the CDN.
    Example: 'gb' → 🇬🇧
    """
    if not code:
        return ""
    #return f'<img src="https://flagcdn.com/w{height}/{code.lower()}.png" height="{height}" style="vertical-align:middle; margin-right:4px;">'
    return f'<img src="https://flagcdn.com/28x21/{code.lower()}.png" width="{width}" height="{height}" style="vertical-align:middle; margin-right:4px;">'


def local_flag_img(code: str, height: int = 20) -> str:
    """Return an HTML img tag for a local flag image from src/streamlit/static/flags/."""
    if not code:
        return ""
    return f'<img src="flags/{code.lower()}.png" height="{height}" style="vertical-align:middle; margin-right:4px;">'
