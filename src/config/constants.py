import os

BASE_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))

# TODO tidy errors dirs to make sure things aren't being repeated under different names. move to specific logging dir?

RAW_DIR = os.path.join(BASE_DATA_DIR, "raw")
ERRORS_DIR = os.path.join(BASE_DATA_DIR, "errors")
MATCH_META_PATH = os.path.join(BASE_DATA_DIR, "euro24_matches.csv")
ERROR_LOG_PATH = os.path.join(ERRORS_DIR, "download_errors.txt")
FLATTENED_DIR = os.path.join(BASE_DATA_DIR, "flattened")

COMP_ID = 55     # Euro Championship
SEASON_ID = 282  # Euro 2024

