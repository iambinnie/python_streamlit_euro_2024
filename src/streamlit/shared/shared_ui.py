import os
import sys
import streamlit as st

def ensure_project_root():
    """Ensure the project root is in sys.path for all Streamlit pages."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

def render_shared_header():
    """Render a consistent header for all Streamlit pages."""
    st.markdown("## Euro 2024 Analysis Tool")
    st.markdown("---")

def shared_filters(events: list):
    """
    Shared filtering: Team + Player + Period (if present).
    Returns a filtered list of event objects.
    """
    teams = sorted(set(e.team for e in events))
    team = st.selectbox("Select Team", teams)
    filtered = [e for e in events if e.team == team]

    players = sorted(set(e.player for e in filtered))
    player = st.selectbox("Select Player", players)
    filtered = [e for e in filtered if e.player == player]

    # Optional: Period filter (only if period exists)
    periods = sorted(set(getattr(e, "period", None) for e in filtered if getattr(e, "period", None) is not None))
    if periods:
        period_selected = st.multiselect("Period(s)", periods, default=periods)
        filtered = [e for e in filtered if e.period in period_selected]

    return filtered
