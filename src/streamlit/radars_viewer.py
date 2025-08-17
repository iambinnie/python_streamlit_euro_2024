# src/streamlit/radars_viewer.py
import os, sys
import streamlit as st
import plotly.graph_objects as go
import pandas as pd

# Ensure project root (your existing pattern)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

st.set_page_config(page_title="Passing Radars (Demo)", layout="wide")
st.title("Passing Radars — Demo (Hardcoded Values)")

# --- Hardcoded demo metrics (per 90) ---
# Adjust values to taste; these are just placeholders to prove the chart renders.
players = {
    "Player A": {
        "OP F3 passes per 90": 2.4,
        "Passes into box per 90": 1.1,
        "Deep progressions per 90": 3.2,
        "Throughballs per 90": 0.4,
    },
    "Player B": {
        "OP F3 passes per 90": 1.8,
        "Passes into box per 90": 0.9,
        "Deep progressions per 90": 2.6,
        "Throughballs per 90": 0.2,
    },
}

# dropdowns
col1, col2 = st.columns(2)
with col1:
    p1 = st.selectbox("Player A", list(players.keys()), index=0)
with col2:
    p2 = st.selectbox("Player B", list(players.keys()), index=1)

m1 = players[p1]
m2 = players[p2]

# consistent metric order
metrics_order = list(next(iter(players.values())).keys())

def radar_trace(name: str, metric_dict: dict):
    return go.Scatterpolar(
        r=[float(metric_dict.get(k, 0.0) or 0.0) for k in metrics_order],
        theta=metrics_order,
        fill="toself",
        name=name,
    )

fig = go.Figure()
fig.add_trace(radar_trace(p1, m1))   # NOTE: add_trace (not fig.add)
fig.add_trace(radar_trace(p2, m2))

fig.update_layout(
    polar=dict(radialaxis=dict(visible=True)),
    legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    margin=dict(l=40, r=40, t=40, b=60),
    showlegend=True,
)

st.plotly_chart(fig, use_container_width=True)

# small table of values
df = pd.DataFrame({p1: m1, p2: m2})
st.subheader("Values")
st.dataframe(df.T, use_container_width=True)
