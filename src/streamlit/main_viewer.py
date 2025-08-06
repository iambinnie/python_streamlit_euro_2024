import os
import sys
import pandas as pd
import streamlit as st

# Ensure project root
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.constants import COMBINED_EVENTS_CSV
from src.streamlit.shared.visual_templates import render_stat_table
from src.streamlit.shared.team_helpers import add_team_flag_column, local_flag_img

# Load combined event data
df = pd.read_csv(COMBINED_EVENTS_CSV, low_memory=False)

# ─────────────────────────────────────────────────────────────
# Top N summary functions
# ─────────────────────────────────────────────────────────────

def top_goals(df: pd.DataFrame) -> pd.DataFrame:
    goals = df[df["shot_outcome"].str.lower().str.contains("goal", na=False)]
    grouped = goals.groupby(["player", "team"]).size().reset_index(name="goals")
    return grouped.sort_values("goals", ascending=False).head(5)

# def top_assists(df):
#     assisted = df[df["pass_outcome"].isna() & df["pass_recipient"].notna()]
#     return assisted["player"].value_counts().head(5).reset_index(name="assists")

def top_assists(df):
    assisted = df[df["pass_goal_assist"] == True]
    return assisted["player"].value_counts().head(5).reset_index(name="assists")

def most_passes(df):
    passes = df[df["type"] == "Pass"]
    return passes["player"].value_counts().head(5).reset_index(name="passes")

def most_interceptions(df):
    interceptions = df[df["type"] == "Interception"]
    return interceptions["player"].value_counts().head(5).reset_index(name="interceptions")

def top_xg(df):
    shots = df[df["type"] == "Shot"]
    return shots.groupby("player")["shot_statsbomb_xg"].sum().sort_values(ascending=False).head(5).reset_index(name="xG")

# ─────────────────────────────────────────────────────────────
# Streamlit layout
# ─────────────────────────────────────────────────────────────

st.set_page_config(page_title="EURO 2024 Summary Viewer", layout="wide")
st.title("EURO 2024 Summary Viewer")
st.markdown("Top performers by goals, assists, passes, interceptions, and xG.")

# Top row metrics
col1, col2, col3 = st.columns(3)
col1.metric("Most Goals", top_goals(df).iloc[0]["player"], f'{top_goals(df).iloc[0]["goals"]} goals')
col2.metric("Top Assister", top_assists(df).iloc[0]["player"], f'{top_assists(df).iloc[0]["assists"]} assists')
col3.metric("Most Passes", most_passes(df).iloc[0]["player"], f'{most_passes(df).iloc[0]["passes"]} passes')

st.divider()

# Grid of data tables
col1, col2, col3 = st.columns(3)
col1.subheader("Top Scorers")
col1.dataframe(top_goals(df), use_container_width=True)

col2.subheader("Top Assisters")
col2.dataframe(top_assists(df), use_container_width=True)

col3.subheader("Most Passes")
col3.dataframe(most_passes(df), use_container_width=True)

st.markdown("---")

col4, col5, _ = st.columns(3)
col4.subheader("Top xG Contributors")
col4.dataframe(top_xg(df), use_container_width=True)

col5.subheader("Most Interceptions")
col5.dataframe(most_interceptions(df), use_container_width=True)


#st.markdown(f'<img src="https://flagcdn.com/w40/ad.png">', unsafe_allow_html=True)

goals_df = top_goals(df)
goals_df_with_flags = add_team_flag_column(goals_df, team_col="team", position="replace")
render_stat_table("Top Goal Scorers", goals_df_with_flags, col_map={"player": "Player", "goals": "Goals"})
