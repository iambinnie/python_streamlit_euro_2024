# === File: run_download_flatten_and_combine.py ===

"""
Orchestrates the full StatsBomb data ETL pipeline...
"""

import os
import sys

# 🔧 Force project root into sys.path (not just src/)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
sys.path.insert(0, PROJECT_ROOT)

# 🔍 (optional) print to confirm
print("PYTHONPATH entries:")
for p in sys.path:
    print("-", p)

from src.download_flatten_combine_statsbomb_data import (
    create_directories_if_not_exists,
    download_statsbomb_data_if_not_exists,
    remove_any_non_raw_statsbomb_data_if_exists,
    flatten_statsbomb_events,
    combine_flattened_event_csvs,
)

from config.constants import COMP_ID, SEASON_ID


def run(
    create_dirs: bool = True,
    download_data: bool = True,
    clear_non_raw: bool = True,
    flatten_data: bool = True,
    combine_data: bool = True,
):
    """
    Runs the full StatsBomb data pipeline with optional steps.

    Parameters:
        create_dirs (bool): Create required data folders if missing
        download_data (bool): Download raw JSON files (if not already present)
        clear_non_raw (bool): Delete any non-raw data (e.g. partial outputs)
        flatten_data (bool): Flatten raw event JSONs to CSV format
        combine_data (bool): Combine individual match CSVs into a single DataFrame
    """
    if create_dirs:
        print("Step 1: Creating required directories...")
        create_directories_if_not_exists.run()

    if download_data:
        print("Step 2: Downloading raw data (if not already downloaded)...")
        download_statsbomb_data_if_not_exists.run(COMP_ID, SEASON_ID)

    if clear_non_raw:
        print("Step 3: Cleaning any non-raw data from previous runs...")
        remove_any_non_raw_statsbomb_data_if_exists.run()

    if flatten_data:
        print("Step 4: Flattening event data to CSV...")
        flatten_statsbomb_events.run()

    if combine_data:
        print("Step 5: Combining all match-level CSVs into one CSV...")
        combine_flattened_event_csvs.run()


if __name__ == "__main__":
    run()
