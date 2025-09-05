# src/streamlit/main_viewer.py
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
from src.metrics.shared.filters import filter_open_play
from src.metrics.shared.minutes import MinutesPlayedCalculator



# ── Page config ─────────────────────────────────────────────────
st.set_page_config(page_title="Pass Metrics — Sandbox", layout="wide")
st.title("Pass Metrics — Phase 1 Sandbox")

# ── Load data ───────────────────────────────────────────────────
@st.cache_data
def load_events():
    return pd.read_csv(COMBINED_EVENTS_CSV, low_memory=False)

df = load_events()

include_set_pieces = st.sidebar.checkbox("Include set pieces", value=False)
if not include_set_pieces:
    df = filter_open_play(df)

# ── Sidebar controls ────────────────────────────────────────────
granularity = st.sidebar.radio("Granularity", ["Competition", "Team", "Match", "Player"], index=0)

# Options
teams = sorted(df["team"].dropna().unique()) if "team" in df.columns else []
players_all = sorted(df["player"].dropna().unique()) if "player" in df.columns else []

selected_team = None
selected_player = None
selected_match = None

if granularity == "Team":
    selected_team = st.sidebar.selectbox("Team", teams) if teams else None
    player_opts = sorted(df.loc[df["team"] == selected_team, "player"].dropna().unique()) if selected_team else []
    selected_player = st.sidebar.selectbox("(Optional) Player filter", ["<All>"] + player_opts) if player_opts else "<All>"

elif granularity == "Match":
    # Prefer match_name if present; fallback to numeric match_id
    if "match_name" in df.columns:
        match_opts = sorted(df["match_name"].dropna().unique())
        selected_match = st.sidebar.selectbox("Match", match_opts) if match_opts else None
    else:
        match_ids = sorted(df["match_id"].dropna().unique()) if "match_id" in df.columns else []
        selected_match = st.sidebar.selectbox("Match ID", match_ids) if match_ids else None

    # Optional in-match filters
    if selected_match is not None:
        in_match = df[df["match_name"].eq(selected_match)] if "match_name" in df.columns \
                   else df[df["match_id"].eq(selected_match)]
        team_opts = sorted(in_match["team"].dropna().unique()) if "team" in in_match.columns else []
        selected_team = st.sidebar.selectbox("(Optional) Team filter", ["<All>"] + team_opts) if team_opts else "<All>"

        if selected_team and selected_team != "<All>":
            player_opts = sorted(in_match.loc[in_match["team"] == selected_team, "player"].dropna().unique())
        else:
            player_opts = sorted(in_match["player"].dropna().unique()) if "player" in in_match.columns else []
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
        metrics = TeamPassMetrics(df[df["player"] == selected_player], selected_team)
        scope_label += f" • Player • {selected_player}"

elif granularity == "Match" and selected_match is not None:
    metrics = MatchPassMetrics(df, selected_match)  # filter_by_match should accept name or id
    scope_label = "Match • "
    scope_label += f"{selected_match}"  # already human-readable if it's match_name
    if selected_team and selected_team != "<All>":
        metrics = MatchPassMetrics(
            df[(df.get("match_name", pd.Series(index=df.index)).eq(selected_match) if "match_name" in df.columns
                else df.get("match_id", pd.Series(index=df.index)).eq(selected_match)) & (df["team"] == selected_team)],
            selected_match,
        )
        scope_label += f" • Team • {selected_team}"
    if selected_player and selected_player != "<All>":
        metrics = MatchPassMetrics(
            df[(df.get("match_name", pd.Series(index=df.index)).eq(selected_match) if "match_name" in df.columns
                else df.get("match_id", pd.Series(index=df.index)).eq(selected_match)) & (df["player"] == selected_player)],
            selected_match,
        )
        scope_label += f" • Player • {selected_player}"

elif granularity == "Player" and selected_player:
    metrics = PlayerPassMetrics(df, selected_player)
    scope_label = f"Player • {selected_player}"

if metrics is None:
    st.warning("No valid selection for this granularity.")
    st.stop()

# Subtitle / scope context
st.caption(scope_label)

# Helper to optionally pass player argument where supported
def maybe_player_arg():
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

c1, c2, c3 = st.columns(3)
c1.metric("Throughballs (attempted)", metrics.throughballs_attempted(p_arg) if p_arg is not None else metrics.throughballs_attempted())
c2.metric("Throughballs (completed)", metrics.throughballs(p_arg) if p_arg is not None else metrics.throughballs())
tb_pct = metrics.throughballs_completion_percentage(p_arg) if p_arg is not None else metrics.throughballs_completion_percentage()
c3.metric("Through-ball Completion%", f"{tb_pct:.1%}")

st.divider()

# ── Optional top tables ─────────────────────────────────────────
show_tops = st.checkbox("Show Top Passers / Assisters tables", value=(granularity in ("Competition", "Team", "Match")))
if show_tops:
    try:
        tcol1, tcol2 = st.columns(2)
        top_p = metrics.top_n("player", n=5, value_name="passes")  # generic top-N by player for passes
        top_a = metrics.top_by_bool("pass_goal_assist", true_value=True, group_column="player", n=5, value_name="assists")
        tcol1.subheader("Top Passers")
        tcol1.dataframe(top_p, use_container_width=True)
        tcol2.subheader("Top Assisters")
        tcol2.dataframe(top_a, use_container_width=True)
    except Exception as e:
        st.info(f"Top tables not available for this scope: {e}")

# Through-ball creators leaderboard (useful at Comp/Team/Match)
if granularity in ("Competition", "Team", "Match"):
    st.subheader("Top Through-ball Creators")
    st.dataframe(metrics.top_throughball_creators(10), use_container_width=True)

st.caption("This page is a sandbox for Phase-1 passing metrics. It doesn’t affect your main viewer.")

st.divider()
st.subheader("Final Third — Direction Splits")

c1, c2, c3 = st.columns(3)
c1.metric("F3 Pass Forward%", f"{(metrics.f3_pass_forward_percentage(p_arg) if p_arg is not None else metrics.f3_pass_forward_percentage()):.1%}")
c2.metric("F3 Pass Sideways%", f"{(metrics.f3_pass_sideways_percentage(p_arg) if p_arg is not None else metrics.f3_pass_sideways_percentage()):.1%}")
c3.metric("F3 Pass Backward%", f"{(metrics.f3_pass_backward_percentage(p_arg) if p_arg is not None else metrics.f3_pass_backward_percentage()):.1%}")

c4, c5 = st.columns(2)
c4.metric("Final Third Passes (completed)", metrics.final_third_passes(p_arg) if p_arg is not None else metrics.final_third_passes())
c5.metric("OP Final Third Passes (completed)", metrics.op_final_third_passes(p_arg) if p_arg is not None else metrics.op_final_third_passes())

st.subheader("Whole Pitch — Direction Splits")
d1, d2, d3 = st.columns(3)
d1.metric("Pass Forward%", f"{(metrics.pass_forward_percentage(p_arg) if p_arg is not None else metrics.pass_forward_percentage()):.1%}")
d2.metric("Pass Sideways%", f"{(metrics.pass_sideways_percentage(p_arg) if p_arg is not None else metrics.pass_sideways_percentage()):.1%}")
d3.metric("Pass Backward%", f"{(metrics.pass_backward_percentage(p_arg) if p_arg is not None else metrics.pass_backward_percentage()):.1%}")

sp_mask = (~metrics.mask_open_play(metrics.df))  # True where set piece
total = len(metrics.df)
sp = int(sp_mask.sum())
op = total - sp
st.caption(f"Event mix in scope — Open play: {op}  |  Set pieces: {sp}  |  Total: {total}")

st.divider()
st.subheader("Pressure — Passing")

p1, p2, p3 = st.columns(3)
p1.metric("Passes Pressured%", f"{(metrics.passes_pressured_percentage(p_arg) if p_arg is not None else metrics.passes_pressured_percentage()):.1%}")
p2.metric("Pr. Pass%", f"{(metrics.pressured_pass_percentage(p_arg) if p_arg is not None else metrics.pressured_pass_percentage()):.1%}")
p3.metric("Pr. Pass% Dif.", f"{(metrics.pressured_pass_percent_difference(p_arg) if p_arg is not None else metrics.pressured_pass_percent_difference()):.1%}")

q1, q2, q3 = st.columns(3)
q1.metric("Pr. Pass Length (avg)", f"{(metrics.pressured_pass_length(p_arg) if p_arg is not None else metrics.pressured_pass_length()):.2f}")
q2.metric("Succ. Pr. Pass Length (avg)", f"{(metrics.successful_pressured_pass_length(p_arg) if p_arg is not None else metrics.successful_pressured_pass_length()):.2f}")
q3.metric("Pr. Pass Length Dif.", f"{(metrics.pressured_pass_length_difference(p_arg) if p_arg is not None else metrics.pressured_pass_length_difference()):+.2f}")


st.subheader("Box Passing — Attempted / Completed / %")

bx1, bx2, bx3 = st.columns(3)
bx1.metric("Into Box — Attempted", metrics.passes_into_box_attempted(p_arg) if p_arg is not None else metrics.passes_into_box_attempted())
bx2.metric("Into Box — Completed", metrics.passes_into_box_completed(p_arg) if p_arg is not None else metrics.passes_into_box_completed())
bx3.metric("Into Box — Completion%", f"{(metrics.passes_into_box_completion_percentage(p_arg) if p_arg is not None else metrics.passes_into_box_completion_percentage()):.1%}")

ib1, ib2, ib3 = st.columns(3)
ib1.metric("Inside Box — Attempted", metrics.passes_inside_box_attempted(p_arg) if p_arg is not None else metrics.passes_inside_box_attempted())
ib2.metric("Inside Box — Completed", metrics.passes_inside_box_completed(p_arg) if p_arg is not None else metrics.passes_inside_box_completed())
ib3.metric("Inside Box — Completion%", f"{(metrics.passes_inside_box_completion_percentage(p_arg) if p_arg is not None else metrics.passes_inside_box_completion_percentage()):.1%}")

# If set pieces are included globally, you can also show OP variants for Into Box:
# bx1.metric("OP Into Box — Attempted", ...)
# ...

st.subheader("Deep Progressions (Pass-only) — Attempted / Completed / %")

dp1, dp2, dp3 = st.columns(3)
dp1.metric("DP — Attempted", metrics.pass_deep_progressions_attempted(p_arg) if p_arg is not None else metrics.pass_deep_progressions_attempted())
dp2.metric("DP — Completed", metrics.pass_deep_progressions(p_arg) if p_arg is not None else metrics.pass_deep_progressions())
dp3.metric("DP — Completion%", f"{(metrics.pass_deep_progressions_completion_percentage(p_arg) if p_arg is not None else metrics.pass_deep_progressions_completion_percentage()):.1%}")

if granularity in ("Competition", "Team", "Match"):
    st.subheader("Top Deep Progressors (Pass-only)")
    st.dataframe(metrics.top_pass_deep_progressors(10), use_container_width=True)

# Compute minutes for the current scoped df and attach to metrics
mpc = MinutesPlayedCalculator()
minutes_map = mpc.compute(df)     # df here should match the current scope
metrics.set_minutes_map(minutes_map)

# ---- Per-90 quick test block (show only when a player is selected) ----
if (granularity == "Player" and selected_player) or (
    granularity in ("Team", "Match") and selected_player and selected_player != "<All>"
):
    player_name = selected_player if selected_player and selected_player != "<All>" else selected_player

    st.subheader("Per-90 (Player)")
    r1, r2, r3 = st.columns(3)
    r1.metric("OP F3 Passes /90", f"{metrics.op_final_third_passes_per90(player_name):.2f}")
    r2.metric("Into Box (completed) /90", f"{metrics.passes_into_box_completed_per90(player_name):.2f}")
    r3.metric("Through-balls (completed) /90", f"{metrics.throughballs_per90(player_name):.2f}")

    r4, r5, r6 = st.columns(3)
    r4.metric("Passes Inside Box (completed) /90", f"{metrics.passes_inside_box_completed_per90(player_name):.2f}")
    r5.metric("Deep Progressions (attempted) /90", f"{metrics.op_pass_deep_progressions_attempted_per90(player_name):.2f}")
    r6.metric("Deep Progressions (completed) /90", f"{metrics.op_pass_deep_progressions_per90(player_name):.2f}")
