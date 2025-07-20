import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

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

st.title("Euro 2024 – Goal View Shot Map")

teams = sorted(set(e.team for e in shot_events))
team = st.selectbox("Select Team", teams)
filtered = [e for e in shot_events if e.team == team]

# === Period filter ===
if filtered:
    periods = sorted(set(e.period for e in filtered if e.period is not None))
    period_selected = st.multiselect("Period(s)", periods, default=periods)
    filtered = [e for e in filtered if e.period in period_selected]

if filtered:
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

    # Correct aspect ratio & Y orientation (0 = bottom, crossbar at top)
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
    for e in filtered:
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

    st.pyplot(fig)
else:
    st.warning("No shot events for this selection.")
