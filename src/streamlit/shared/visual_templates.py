import pandas as pd
import streamlit as st

# def render_stat_table(title: str, df: pd.DataFrame, col_map: dict = None, max_rows: int = 5):
#     """
#     Displays a styled stat table in Streamlit with consistent formatting.
#
#     Args:
#         title (str): Table title to display.
#         df (pd.DataFrame): DataFrame containing stats (should already be filtered and sorted).
#         col_map (dict): Optional column rename map for display (e.g., {"player": "Player", "goals": "Goals"}).
#         max_rows (int): Number of rows to show (default 5).
#     """
#     st.markdown(f"**{title}**")
#
#     if col_map:
#         df = df.rename(columns=col_map)
#
#     st.dataframe(df.head(max_rows), use_container_width=True)

def render_stat_table(title: str, df: pd.DataFrame, col_map: dict = None, max_rows: int = 5):
    st.markdown(f"### {title}")

    if col_map:
        df = df.rename(columns=col_map)

    # Limit rows and prepare HTML table
    df = df.head(max_rows)
    headers = df.columns.tolist()
    rows = df.values.tolist()

    table_html = "<table style='width:100%; border-collapse: collapse;'>"

    # Header row
    table_html += "<thead><tr>"
    for col in headers:
        table_html += f"<th style='text-align:left; padding: 4px 8px; border-bottom: 1px solid #ccc;'>{col}</th>"
    table_html += "</tr></thead>"

    # Data rows
    table_html += "<tbody>"
    for row in rows:
        table_html += "<tr>"
        for cell in row:
            table_html += f"<td style='padding: 4px 8px; vertical-align: middle;'>{cell}</td>"
        table_html += "</tr>"
    table_html += "</tbody></table>"

    st.markdown(table_html, unsafe_allow_html=True)


