# === File: src/config/constants.py ===

"""
Centralised constants for StatsBomb data ETL and Streamlit app.

All paths are relative to the project root, keeping data directories outside of src.
"""

import os

# ✅ Project root (two levels up from this file)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ✅ Base data directory (outside src)
BASE_DATA_DIR = os.path.join(PROJECT_ROOT, "data")

# Subdirectories & files
RAW_DIR = os.path.join(BASE_DATA_DIR, "raw")
ERRORS_DIR = os.path.join(BASE_DATA_DIR, "errors")
MATCH_META_PATH = os.path.join(BASE_DATA_DIR, "euro24_matches.csv")
ERROR_LOG_PATH = os.path.join(ERRORS_DIR, "download_errors.txt")
FLATTENED_DIR = os.path.join(BASE_DATA_DIR, "flattened")
COMBINED_EVENTS_CSV = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")

COMP_ID = 55     # Euro Championship
SEASON_ID = 282  # Euro 2024

