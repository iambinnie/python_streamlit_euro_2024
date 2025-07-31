import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.patches as mpatches
from matplotlib import pyplot as plt

# Determine and add the project root (only once)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.constants import BASE_DATA_DIR
from src.events.parsers.parse_shot_events import parse_shot_events
from src.streamlit.shared.shared_ui import render_shared_header, shared_filters, render_event_legend
from src.events.event_models import ShotEvent

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")


@st.cache_data
def load_shot_events(path: str):
    df = pd.read_csv(path, low_memory=False)
    df_shot = df[df["type"] == "Shot"].copy()
    return parse_shot_events(df_shot)


# === Load & filter data ===
shot_events_dict = load_shot_events(DATA_PATH)
df = pd.read_csv(DATA_PATH, low_memory=False)
df_shot = df[df["type"] == "Shot"].copy()

render_shared_header("Euro 2024 – Goal View Shot Map")

filtered_df, team, player, match = shared_filters(df_shot, enable_player_toggle=False)

# Convert filtered DataFrame back to ShotEvent objects (using stable IDs)
filtered_events = [
    shot_events_dict.get(row["id"])
    for _, row in filtered_df.iterrows()
    if row["id"] in shot_events_dict
]

if filtered_events:
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title(f"{team} – Goal View", fontsize=14)

    # === Goal dimensions ===
    goal_width = 7.32
    crossbar_height = 2.44

    # Thicker posts & white fill
    ax.fill_betweenx([0, crossbar_height], 0, goal_width, color="white", zorder=0, alpha=1.0)
    ax.plot([0, goal_width, goal_width, 0, 0],
            [0, 0, crossbar_height, crossbar_height, 0],
            color="black", lw=3, zorder=1)

    # Correct aspect ratio
    ax.set_xlim(-0.2, goal_width + 0.2)
    ax.set_ylim(-0.2, crossbar_height + 0.2)
    ax.set_aspect('equal', adjustable='box')

    # Gridlines (net simulation)
    net_spacing_x = 0.5
    net_spacing_y = 0.5
    for x in [i * net_spacing_x for i in range(int(goal_width // net_spacing_x) + 1)]:
        ax.plot([x, x], [0, crossbar_height], color="lightgray", lw=0.8, alpha=0.7, zorder=1)
    for y in [i * net_spacing_y for i in range(int(crossbar_height // net_spacing_y) + 1)]:
        ax.plot([0, goal_width], [y, y], color="lightgray", lw=0.8, alpha=0.7, zorder=1)

    # Plot shots
    for e in filtered_events:
        if e.shot_end_y is None or e.shot_end_x is None:
            continue

        gx, gy = e.get_goal_coordinates()
        if gx is None or gy is None:
            continue

        ax.scatter(
            gx, gy,
            s=e.get_radius(),
            color=e.get_color(),
            edgecolors="black",
            alpha=0.8,
            zorder=2
        )

    # === Show legend toggle ===
    show_legend = st.checkbox("Show Legend", value=True)
    render_event_legend(ax, ShotEvent, show_legend)
    st.pyplot(fig)

    with st.expander("Show Shot Event Data"):
        st.dataframe([e.model_dump() for e in filtered_events])
else:
    st.warning("No shot events for this selection.")
