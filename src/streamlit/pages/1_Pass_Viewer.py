# === File: src/streamlit/pages/1_Pass_Viewer.py ===
"""
Pass Event Viewer – displays completed/incomplete passes on a pitch,
with tournament or match filtering and optional player selection.
"""

import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch, Pitch

# Ensure project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.streamlit.shared.shared_ui import (
    render_shared_header,
    shared_filters,
)
from src.config.constants import BASE_DATA_DIR
from src.events.parsers.parse_pass_events import parse_pass_events

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")

@st.cache_data
def load_pass_events(path: str):
    df = pd.read_csv(path, low_memory=False)
    df_pass = df[df["type"] == "Pass"].copy()
    return parse_pass_events(df_pass)

# === Load and filter data ===
pass_events_dict = load_pass_events(DATA_PATH)
pass_events = list(pass_events_dict.values())

render_shared_header("Euro 2024 – Pass Viewer")

# Shared filters (hierarchical)
df = pd.read_csv(DATA_PATH, low_memory=False)
df_pass = df[df["type"] == "Pass"].copy()
filtered_df, team, player, match = shared_filters(df_pass, enable_player_toggle=True)

# Convert filtered DataFrame back to PassEvent objects
filtered_events = [
    pass_events_dict.get(row["id"])
    for _, row in filtered_df.iterrows()
    if row["id"] in pass_events_dict
]


# === Pitch Visualization ===
if filtered_events:
    pitch = Pitch(pitch_type="statsbomb", goal_type= 'box', half=False)
    fig, ax = pitch.draw(figsize=(9, 6))

    for e in filtered_events:
        coords = e.to_arrow_coords()
        if coords:
            pitch.arrows(
                *coords,
                color=e.get_color(),
                alpha=0.7,
                width=2,
                headwidth=6,
                ax=ax
            )
    st.pyplot(fig)

    with st.expander("Show Pass Event Data"):
        st.dataframe([e.model_dump() for e in filtered_events])
else:
    st.warning("No pass events for this selection.")
