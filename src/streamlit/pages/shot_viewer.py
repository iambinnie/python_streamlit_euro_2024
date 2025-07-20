# === File: src/streamlit/shot_viewer.py ===

import os
import sys

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# Add project root to path
# Determine and add the project root (only once)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.constants import BASE_DATA_DIR
from src.events.parsers.parse_shot_events import parse_shot_events

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")

@st.cache_data
def load_shot_events(path: str):
    df = pd.read_csv(path, low_memory=False)
    df_shot = df[df["type"] == "Shot"].copy()
    return parse_shot_events(df_shot)

# === Load data ===
shot_events_dict = load_shot_events(DATA_PATH)
shot_events = list(shot_events_dict.values())

st.title("Euro 2024 – Shot Viewer (Model-Based)")

teams = sorted(set(e.team for e in shot_events))
team = st.selectbox("Select Team", teams)
filtered = [e for e in shot_events if e.team == team]

players = sorted(set(e.player for e in filtered))
player = st.selectbox("Select Player", players)
filtered = [e for e in filtered if e.player == player]

# === Pitch config based on model ===
if filtered:
    event = filtered[0]
    pitch = VerticalPitch(pitch_type="statsbomb", half=event.pitch_view.use_half_pitch())
    fig, ax = pitch.draw(figsize=(9, 6))

    # Start/end toggle
    view_mode = st.radio("Shot location mode", options=["Location Only", "Direction Arrow"], horizontal=True)
    use_end = view_mode == "Direction Arrow"

    for e in filtered:
        # Always plot start dot
        x_start, y_start = e.get_location(use_end=False)
        pitch.scatter(
            x_start, y_start,
            s=e.get_radius(),
            color=e.get_color(),
            edgecolors="black",
            alpha=0.85,
            zorder=2,
            ax=ax
        )

        if use_end:
            # Draw arrow from start to end location
            x_end, y_end = e.get_location(use_end=True)
            if x_end is not None and y_end is not None:
                pitch.arrows(
                    x_start, y_start,
                    x_end, y_end,
                    color=e.get_color(),
                    width=2,
                    headwidth=6,
                    ax=ax,
                    zorder=1,
                    alpha=0.8,
                )

    st.pyplot(fig)

    with st.expander("Show Shot Event Data"):
        st.dataframe([e.model_dump() for e in filtered])
else:
    st.warning("No shot events for this selection.")
