# === File: src/streamlit/pass_viewer.py ===

import os
import sys

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# Add project root to PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.events.parsers.parse_pass_events import parse_pass_events
from src.config.constants import BASE_DATA_DIR

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")


@st.cache_data
def load_pass_events(path: str):
    df = pd.read_csv(path, low_memory=False)
    df_pass = df[df["type"] == "Pass"].copy()
    return parse_pass_events(df_pass)


# === Load and filter ===
pass_events_dict = load_pass_events(DATA_PATH)
pass_events = list(pass_events_dict.values())

st.title("Euro 2024 – Pass Viewer (Model-Based)")

teams = sorted(set(e.team for e in pass_events))
team = st.selectbox("Select Team", teams)

filtered = [e for e in pass_events if e.team == team]

players = sorted(set(e.player for e in filtered))
player = st.selectbox("Select Player", players)

filtered = [e for e in filtered if e.player == player]

# === Draw pitch and plot passes ===
if filtered:
    event = filtered[0]
    pitch = VerticalPitch(pitch_type="statsbomb", half=event.pitch_view.use_half_pitch())
    fig, ax = pitch.draw(figsize=(9, 6))

    for e in filtered:
        coords = e.to_arrow_coords()
        if coords:
            color = "green" if e.is_completed() else "red"
            pitch.arrows(*coords, ax=ax, width=1.5, headwidth=6, color=color, alpha=0.8)

    st.pyplot(fig)

    # Optional table
    with st.expander("Show Event Data"):
        st.dataframe([e.model_dump() for e in filtered])
else:
    st.warning("No events to display.")
