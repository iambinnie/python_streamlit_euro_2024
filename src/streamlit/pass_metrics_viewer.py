"""
passes_metrics_viewer.py
------------------------
Test viewer for passing metrics.

- When grouping by TEAM (and no minutes file provided): uses robust match-duration fallback so team minutes ≈ real match time (not event-sparse).
- When grouping by PLAYER without a minutes file: uses coarse event-based minutes (acceptable for quick checks, but supply a minutes file for accuracy).

Run:
    streamlit run src/streamlit/pages/passes_metrics_viewer.py
"""

# Ensure project root
import os, sys
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
import pandas as pd

from src.metrics.shared.per_90 import (
    apply_per90,
    approx_minutes_from_events,
    approx_team_minutes_from_matches,
)
from src.metrics.passes.directional_and_thirds import (
    prepare_pass_df,
    aggregate_passing_metrics,
)

st.set_page_config(page_title="Passing Metrics Viewer", layout="wide")
st.title("Passing Metrics — Direction & Thirds (Test Viewer)")

with st.sidebar:
    st.header("Inputs")

    data_path = st.text_input("Events file path (.csv or .parquet)", value="")
    minutes_path = st.text_input("Minutes file path (optional)", value="")
    x_max = st.number_input("Pitch length (x_max)", value=120.0, step=1.0)
    x_flip_col = st.text_input("Flip column (optional bool)", value="")

    st.markdown("---")
    st.subheader("Columns (override if needed)")
    type_col = st.text_input("Event type column", value="type")
    pass_label = st.text_input("Label for 'Pass' in type column", value="Pass")

    x_candidates = st.text_input("Start x candidates (comma)", value="x,location_x,start_x")
    y_candidates = st.text_input("Start y candidates (comma)", value="y,location_y,start_y")
    ex_candidates = st.text_input("End x candidates (comma)", value="end_x,pass_end_x")
    ey_candidates = st.text_input("End y candidates (comma)", value="end_y,pass_end_y")

    st.markdown("---")
    st.subheader("Grouping")
    group_by_team = st.checkbox("Group by team", value=True)
    group_by_player = st.checkbox("Also group by player", value=False)

    st.markdown("---")
    st.subheader("Per90")
    do_per90 = st.checkbox("Compute per90", value=True)
    minutes_col = st.text_input("Minutes column name (in minutes file)", value="minutes_played")

def load_df(path: str) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    if not os.path.exists(path):
        st.error(f"File not found: {path}")
        return pd.DataFrame()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path)
    if ext == ".parquet":
        return pd.read_parquet(path)
    st.error("Unsupported file type. Use .csv or .parquet")
    return pd.DataFrame()

events_df = load_df(data_path)
if events_df.empty:
    st.info("Provide an events file to begin.")
    st.stop()

passes_df = prepare_pass_df(
    events_df,
    type_col=type_col,
    pass_label=pass_label,
    x_col_candidates=tuple([c.strip() for c in x_candidates.split(",") if c.strip()]),
    y_col_candidates=tuple([c.strip() for c in y_candidates.split(",") if c.strip()]),
    end_x_col_candidates=tuple([c.strip() for c in ex_candidates.split(",") if c.strip()]),
    end_y_col_candidates=tuple([c.strip() for c in ey_candidates.split(",") if c.strip()]),
    x_max=float(x_max),
    x_flip_col=x_flip_col if x_flip_col else None,
)

# Choose grouping
group_cols = []
if group_by_team and "team_id" in events_df.columns:
    group_cols.append("team_id")
if group_by_player and "player_id" in events_df.columns:
    group_cols.append("player_id")

if not group_cols:
    st.warning("No grouping columns found. Enable at least one grouping and ensure columns exist in data (team_id/player_id).")
    st.stop()

# Aggregate metrics
agg = aggregate_passing_metrics(passes_df, group_cols=group_cols)

# Minutes / per90
if do_per90:
    if minutes_path:
        minutes_df = load_df(minutes_path)
        missing = set(group_cols + [minutes_col]) - set(minutes_df.columns)
        if missing:
            st.error(f"Minutes file missing columns: {missing}")
            st.stop()
    else:
        # Auto-select best fallback:
        if group_cols == ["team_id"]:
            # Robust: per-team minutes from per-match durations (all events in match)
            needed = {"team_id", "match_id", "minute"}
            missing = needed - set(events_df.columns)
            if missing:
                st.warning(
                    f"Using coarse fallback because events file missing {missing}. "
                    "For accurate team minutes, include match_id & minute (and ideally second)."
                )
                minutes_df = approx_minutes_from_events(events_df, group_cols=group_cols, minute_col="minute")
            else:
                minutes_df = approx_team_minutes_from_matches(
                    events_df,
                    team_col="team_id",
                    match_col="match_id",
                    minute_col="minute",
                    second_col="second" if "second" in events_df.columns else None,
                )
        else:
            # Coarse: OK for quick player checks; provide minutes file for accuracy.
            minutes_df = approx_minutes_from_events(events_df, group_cols=group_cols, minute_col="minute")

    per90_df = apply_per90(agg, minutes_df, group_cols=group_cols, minutes_col=minutes_col)
    st.subheader("Passing Metrics (per90 included)")
    st.dataframe(per90_df, use_container_width=True)
else:
    st.subheader("Passing Metrics (raw counts)")
    st.dataframe(agg, use_container_width=True)

st.markdown("---")
st.caption(
    "Team grouping uses robust match-duration minutes when no minutes file is provided. "
    "Player grouping uses a coarse event-based estimate — supply a minutes file for accuracy."
)
