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


def render_event_legend(ax, event_cls, show: bool = True):
    """
    Generic legend renderer for event types using the model's get_legend_patches() method.

    Parameters:
        ax: Matplotlib Axes to draw on
        event_cls: A class like ShotEvent or PassEvent, with get_legend_patches() method
        show: Whether to display the legend
    """
    # Remove any existing legend
    if ax.get_legend():
        ax.get_legend().remove()

    # Add new legend if toggle is on
    if show:
        try:
            legend_handles = event_cls.get_legend_patches()
            ax.legend(handles=legend_handles, loc="upper right", frameon=True)
        except Exception as e:
            print(f"Failed to render legend: {e}")
