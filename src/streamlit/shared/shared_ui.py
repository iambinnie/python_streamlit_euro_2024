"""
Shared UI components for Streamlit event viewers:
- render_shared_header: Consistent page title styling.
- shared_filters: Hierarchical match → team → player filtering.
"""
import os
import sys

import streamlit as st
import pandas as pd
import matplotlib.patches as mpatches
from matplotlib import pyplot as plt

# Determine and add the project root (only once)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.events.event_models import ShotEvent

def render_shared_header(title: str):
    st.markdown(f"## {title}")
    st.markdown("---")


def shared_filters(df: pd.DataFrame, enable_player_toggle: bool = True):
    """
    Hierarchical filters: Match → Team → Player (optional).
    Returns: (filtered_df, team, player, match)
    """
    match_options = sorted(df["match_name"].dropna().unique().tolist())
    match_options.insert(0, "All matches")
    match_selected = st.selectbox("Match", match_options, index=0)

    filtered_df = df.copy()
    if match_selected != "All matches":
        filtered_df = filtered_df[filtered_df["match_name"] == match_selected]

    team_options = sorted(filtered_df["team"].dropna().unique().tolist())
    team = st.selectbox("Team", team_options)
    filtered_df = filtered_df[filtered_df["team"] == team]

    # === Period filter (segmented control or fallback) ===
    periods = sorted(df["period"].dropna().unique().tolist())
    if hasattr(st, "segmented_control"):
        period_selected = st.segmented_control("Period", periods, selection_mode='multi', default=periods)
    else:
        period_selected = st.multiselect("Period(s)", periods, default=periods)
    df = df[df["period"].isin(period_selected)]

    player = None
    if enable_player_toggle:
        player_toggle = st.checkbox("Filter by player", value=False)
        if player_toggle:
            player_options = sorted(filtered_df["player"].dropna().unique().tolist())
            player = st.selectbox("Player", player_options)
            filtered_df = filtered_df[filtered_df["player"] == player]

    return filtered_df, team, player, match_selected

def render_shot_legend(ax, show: bool = True):
    """
    Attaches or removes a standardized shot outcome legend to a Matplotlib Axes,
    using the ShotEvent model's get_legend_patches() method.
    """
    # Always remove existing legend to prevent stale handles
    existing_legend = ax.get_legend()
    if existing_legend:
        existing_legend.remove()

    # Only add a new legend if the toggle is active
    if show:
        try:
            from src.events.event_models import ShotEvent
            legend_handles = ShotEvent.get_legend_patches()
            ax.legend(handles=legend_handles, loc="upper right", frameon=True)
        except Exception as e:
            print(f"Failed to render legend: {e}")
