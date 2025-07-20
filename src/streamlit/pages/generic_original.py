import os
import sys
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from mplsoccer import VerticalPitch

# Fix import path
# Determine and add the project root (only once)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.constants import BASE_DATA_DIR

DATA_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")

@st.cache_data
def load_data(path: str):
    return pd.read_csv(path, low_memory=False)

df = load_data(DATA_PATH)

# === Basic checks ===
required_cols = {"x", "y", "team", "player", "type", "period", "match_name"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Missing columns in combined CSV: {missing}")
    st.stop()

# === UI Filters ===
st.title("Euro 2024 – Event Explorer")
st.caption("Select team, player, event type, and period(s).")

team = st.selectbox("Team", sorted(df["team"].dropna().unique()))
players = sorted(df[df["team"] == team]["player"].dropna().unique())
player = st.selectbox("Player", players)

event_types = sorted(df[df["player"] == player]["type"].dropna().unique())
etype = st.selectbox("Event Type", event_types)

period_options = sorted(df["period"].dropna().unique().tolist())
period_selected = st.multiselect("Period(s)", period_options, default=period_options)

# === Filter data ===
mask = (
    (df["team"] == team)
    & (df["player"] == player)
    & (df["type"] == etype)
    & (df["period"].isin(period_selected))
)
df_plot = df[mask].copy()

if df_plot.empty:
    st.warning("No events match your filters.")
    st.stop()

# === Plot setup ===
pitch = VerticalPitch(pitch_type="statsbomb", half=True)
fig, ax = pitch.draw(figsize=(9, 9))

has_end_coords = {"end_x", "end_y"}.issubset(df_plot.columns) and not df_plot[["end_x", "end_y"]].isna().all().all()

if has_end_coords:
    for _, row in df_plot.iterrows():
        if pd.notna(row["x"]) and pd.notna(row["y"]) and pd.notna(row["end_x"]) and pd.notna(row["end_y"]):
            if row["type"] in ("Pass", "Carry"):
                # Use correct flat column for outcome
                incomplete = pd.notna(row.get("pass_outcome"))
                color = "red" if incomplete else "green"
            else:
                color = "blue"

            pitch.arrows(
                row["x"], row["y"], row["end_x"], row["end_y"],
                ax=ax, width=1.5, headwidth=6, color=color, alpha=0.8, zorder=2
            )

    st.caption("Green = completed • Red = incomplete (passes/carries) • Blue = other arrows")
else:
    pitch.scatter(
        df_plot["x"], df_plot["y"],
        s=80, color="red", edgecolors="black", alpha=0.7, zorder=2, ax=ax
    )
    st.caption("Red dots show event locations (no end coordinates provided)")

st.pyplot(fig)
