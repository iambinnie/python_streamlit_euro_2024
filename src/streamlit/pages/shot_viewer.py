# === File: src/streamlit/pages/2_Shot_Viewer.py ===
"""
Shot Event Viewer – displays shots with start/end arrows,
tournament or match filtering, and optional player selection.
"""

import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch
from matplotlib.patches import Patch

# Determine and add the project root (only once)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.constants import BASE_DATA_DIR
from src.events.parsers.parse_shot_events import parse_shot_events
from src.streamlit.shared.shared_ui import (
    render_shared_header,
    shared_filters,
    render_event_legend,
)
from src.events.event_models import ShotEvent

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")


@st.cache_data
def load_shot_events(path: str):
    df = pd.read_csv(path, low_memory=False)
    df_shot = df[df["type"] == "Shot"].copy()
    return parse_shot_events(df_shot)


# === Load and filter data ===
shot_events_dict = load_shot_events(DATA_PATH)
render_shared_header("Euro 2024 – Shot Viewer (Model-Based)")

# Shared filters (player toggle enabled)
df = pd.read_csv(DATA_PATH, low_memory=False)
df_shot = df[df["type"] == "Shot"].copy()
filtered_df, team, player, match = shared_filters(df_shot, enable_player_toggle=True)

# Convert filtered DataFrame back to ShotEvent objects (using stable IDs)
filtered_events = [
    shot_events_dict.get(row["id"])
    for _, row in filtered_df.iterrows()
    if row["id"] in shot_events_dict
]

# === Pitch Visualization ===
if filtered_events:
    event = filtered_events[0]
    pitch = VerticalPitch(pitch_type="statsbomb", half=event.pitch_view.use_half_pitch())
    fig, ax = pitch.draw(figsize=(9, 6))

    # Start/end toggle
    view_mode = st.radio("Shot location mode", options=["Location Only", "Direction Arrow"], horizontal=True)
    use_end = view_mode == "Direction Arrow"

    for e in filtered_events:
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

    # === Show legend toggle ===
    show_legend = st.checkbox("Show Legend", value=True)
    render_event_legend(ax, ShotEvent, show_legend)

    st.pyplot(fig)

    with st.expander("Show Shot Event Data"):
        st.dataframe([e.model_dump() for e in filtered_events])
else:
    st.warning("No shot events for this selection.")
