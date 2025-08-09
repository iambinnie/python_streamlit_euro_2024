import os
import sys
import pandas as pd
import streamlit as st

# ── Ensure project root on sys.path ─────────────────────────────
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# ── Imports from your project ───────────────────────────────────
from src.config.constants import COMBINED_EVENTS_CSV
from src.metrics.competition.passes import CompetitionPassMetrics
from src.metrics.team.passes import TeamPassMetrics
from src.metrics.match.passes import MatchPassMetrics
from src.metrics.player.passes import PlayerPassMetrics

# ── Page config ─────────────────────────────────────────────────
st.set_page_config(page_title="Pass Metrics — Sandbox", layout="wide")
st.title("Pass Metrics — Phase 1 Sandbox")

# ── Load data ───────────────────────────────────────────────────
@st.cache_data
def load_events():
    return pd.read_csv(COMBINED_EVENTS_CSV, low_memory=False)

df = load_events()

# ── Sidebar controls ────────────────────────────────────────────
granularity = st.sidebar.radio("Granularity", ["Competition", "Team", "Match", "Player"], index=0)

# Basic guards for option lists
teams = sorted(df["team"].dropna().unique()) if "team" in df.columns else []
players_all = sorted(df["player"].dropna().unique()) if "player" in df.columns else []
matches = sorted(df["match_id"].dropna().unique()) if "match_id" in df.columns else []

selected_team = None
selected_player = None
selected_match = None

if granularity == "Team":
    selected_team = st.sidebar.selectbox("Team", teams) if teams else None
    player_opts = sorted(df.loc[df["team"] == selected_team, "player"].dropna().unique()) if selected_team else []
    selected_player = st.sidebar.selectbox("(Optional) Player filter", ["<All>"] + player_opts) if player_opts else "<All>"

elif granularity == "Match":
    selected_match = st.sidebar.selectbox("Match ID", matches) if matches else None
    # Optional extra filters in context of the match
    team_opts = sorted(df.loc[df["match_id"] == selected_match, "team"].dropna().unique()) if selected_match is not None else []
    selected_team = st.sidebar.selectbox("(Optional) Team filter", ["<All>"] + team_opts) if team_opts else "<All>"
    if selected_team and selected_team != "<All>":
        player_opts = sorted(df[(df["match_id"] == selected_match) & (df["team"] == selected_team)]["player"].dropna().unique())
    else:
        player_opts = sorted(df[df["match_id"] == selected_match]["player"].dropna().unique()) if selected_match is not None else []
    selected_player = st.sidebar.selectbox("(Optional) Player filter", ["<All>"] + player_opts) if player_opts else "<All>"

elif granularity == "Player":
    selected_player = st.sidebar.selectbox("Player", players_all) if players_all else None

# ── Construct the metric object for the chosen scope ────────────
metrics = None
scope_label = "Competition"

if granularity == "Competition":
    metrics = CompetitionPassMetrics(df)
    scope_label = "Competition"

elif granularity == "Team" and selected_team:
    metrics = TeamPassMetrics(df, selected_team)
    scope_label = f"Team • {selected_team}"
    if selected_player and selected_player != "<All>":
        # Re-scope metrics to that single player's rows while staying at team level
        metrics = TeamPassMetrics(df[df["player"] == selected_player], selected_team)
        scope_label += f" • Player • {selected_player}"

elif granularity == "Match" and selected_match is not None:
    # Base: match scope
    metrics = MatchPassMetrics(df, selected_match)
    scope_label = f"Match • {selected_match}"
    # Optional team filter in match
    if selected_team and selected_team != "<All>":
        metrics = MatchPassMetrics(df[(df["match_id"] == selected_match) & (df["team"] == selected_team)], selected_match)
        scope_label += f" • Team • {selected_team}"
    # Optional player filter in match
    if selected_player and selected_player != "<All>":
        metrics = MatchPassMetrics(df[(df["match_id"] == selected_match) & (df["player"] == selected_player)], selected_match)
        scope_label += f" • Player • {selected_player}"

elif granularity == "Player" and selected_player:
    metrics = PlayerPassMetrics(df, selected_player)
    scope_label = f"Player • {selected_player}"

if metrics is None:
    st.warning("No valid selection for this granularity.")
    st.stop()

st.caption(scope_label)

# Helper to optionally pass player argument where supported
def maybe_player_arg():
    # Competition/Team/Match classes support an optional player param in many methods.
    # Player-level class has no player argument (already scoped).
    if granularity in ("Competition", "Team", "Match"):
        if granularity == "Team" and selected_player and selected_player != "<All>":
            return selected_player
        if granularity == "Match" and selected_player and selected_player != "<All>":
            return selected_player
        return None
    return None

p_arg = maybe_player_arg()

# ── Metrics grid (Phase-1) ──────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Passing%", f"{metrics.passing_percentage(p_arg):.1%}" if p_arg is not None else f"{metrics.passing_percentage():.1%}")
col2.metric("Pass Length (avg)", f"{metrics.pass_length(p_arg):.2f}" if p_arg is not None else f"{metrics.pass_length():.2f}")
col3.metric("Successful Pass Length (avg)", f"{metrics.successful_pass_length(p_arg):.2f}" if p_arg is not None else f"{metrics.successful_pass_length():.2f}")

col4, col5, col6 = st.columns(3)
col4.metric("Long Balls (≥35, completed)", metrics.long_balls(p_arg) if p_arg is not None else metrics.long_balls())
col5.metric("Long Ball%", f"{metrics.long_ball_percentage(p_arg):.1%}" if p_arg is not None else f"{metrics.long_ball_percentage():.1%}")
col6.metric("Open Play Passes", metrics.open_play_passes(p_arg) if p_arg is not None else metrics.open_play_passes())

col7, col8, col9 = st.columns(3)
col7.metric("Passes Into Box", metrics.passes_into_box(p_arg) if p_arg is not None else metrics.passes_into_box())
col8.metric("OP Passes Into Box", metrics.op_passes_into_box(p_arg) if p_arg is not None else metrics.op_passes_into_box())
col9.metric("Passes Inside Box", metrics.passes_inside_box(p_arg) if p_arg is not None else metrics.passes_inside_box())

st.metric("Throughballs (completed)", metrics.throughballs(p_arg) if p_arg is not None else metrics.throughballs())

st.divider()

# ── Optional top tables where they make sense ───────────────────
show_tops = st.checkbox("Show Top Passers / Assisters tables", value=(granularity in ("Competition", "Team", "Match")))
if show_tops:
    try:
        tcol1, tcol2 = st.columns(2)
        top_p = metrics.top_passers(n=5)
        top_a = metrics.top_assisters(n=5)
        tcol1.subheader("Top Passers")
        tcol1.dataframe(top_p, use_container_width=True)
        tcol2.subheader("Top Assisters")
        tcol2.dataframe(top_a, use_container_width=True)
    except Exception as e:
        st.info(f"Top tables not available for this scope: {e}")

if granularity in ("Competition", "Team", "Match"):
    st.subheader("Top Through-ball Creators")
    st.dataframe(metrics.top_throughball_creators(10), use_container_width=True)


st.caption("This page is a sandbox for Phase-1 passing metrics. It doesn’t affect your main viewer.")

# What values do we have?
st.write(df["pass_technique"].dropna().value_counts().head(10))
st.write(df["pass_through_ball"].dropna().value_counts())

st.metric("Throughballs (attempted)", metrics.throughballs_attempted(p_arg) if p_arg is not None else metrics.throughballs_attempted())
st.metric("Throughballs (completed)", metrics.throughballs(p_arg) if p_arg is not None else metrics.throughballs())

