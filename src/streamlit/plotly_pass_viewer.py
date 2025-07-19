# === File: src/streamlit/shot_viewer.py ===

import os
import sys

import pandas as pd
import streamlit as st
import plotly.express as px

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

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

st.title("Euro 2024 – Shot Viewer (Interactive Tooltips)")

teams = sorted(set(e.team for e in shot_events))
team = st.selectbox("Select Team", teams)
filtered = [e for e in shot_events if e.team == team]

players = sorted(set(e.player for e in filtered))
player = st.selectbox("Select Player", players)
filtered = [e for e in filtered if e.player == player]

# Build Plotly DataFrame
if filtered:
    data = []
    for e in filtered:
        x_start, y_start = e.get_location(use_end=False)
        x_end, y_end = e.get_location(use_end=True)
        data.append({
            "x": x_start,
            "y": y_start,
            "x_end": x_end,
            "y_end": y_end,
            "xG": e.shot_xg,
            "minute": e.minute,
            "outcome": e.shot_outcome,
            "color": e.get_color(),
            "radius": e.get_radius(),
            "player": e.player
        })
    df_vis = pd.DataFrame(data)

    view_mode = st.radio(
        "Shot location mode",
        options=["Location Only", "Direction Arrow"],
        horizontal=True
    )
    use_arrows = view_mode == "Direction Arrow"

    # Create plot
    fig = px.scatter(
        df_vis,
        x="x", y="y",
        size="radius",
        color="color",
        color_discrete_map="identity",
        hover_data=["player", "xG", "minute", "outcome"],
    )

    fig.update_yaxes(autorange="reversed")  # StatsBomb pitch flips Y
    fig.update_layout(
        width=800, height=550,
        title=f"Shots by {player}",
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
        plot_bgcolor="white"
    )

    # Optionally add arrows
    if use_arrows:
        for _, row in df_vis.iterrows():
            if pd.notna(row["x_end"]) and pd.notna(row["y_end"]):
                fig.add_annotation(
                    x=row["x_end"],
                    y=row["y_end"],
                    ax=row["x"],
                    ay=row["y"],
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True,
                    arrowhead=3,
                    arrowwidth=2,
                    arrowcolor=row["color"],
                )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No shot events for this selection.")
