import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

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

st.title("Euro 2024 – Goal View Shot Map")

teams = sorted(set(e.team for e in shot_events))
team = st.selectbox("Select Team", teams)
filtered = [e for e in shot_events if e.team == team]

if filtered:
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title(f"{team} – Goal View", fontsize=14)

    # Draw goal outline
    ax.plot([0, 7.32, 7.32, 0, 0], [0, 0, 2.44, 2.44, 0], color="black", lw=2)
    ax.set_xlim(-0.2, 7.5)
    ax.set_ylim(0, 2.7)
    ax.invert_yaxis()  # Optional: put crossbar at top

    for e in filtered:
        if e.shot_end_y is None or e.shot_end_x is None:
            continue

        # Normalize lateral position to goal width (StatsBomb y ≈ 36–44 near goal)
        gx = (e.shot_end_y - 36) / 8 * 7.32
        gy = e.shot_end_z if e.shot_end_z is not None else 0

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
