# === File: download_and_flatten_statsbomb_data/combine_flattened_event_csvs.py ===

"""
Combines all per-match flattened event CSVs into a single master file.
- Reads from FLATTENED_DIR (e.g. data/flattened/)
- Writes to euro24_all_events_combined.csv in BASE_DATA_DIR
"""

import os
import pandas as pd
from src.config.constants import FLATTENED_DIR, BASE_DATA_DIR

COMBINED_PATH = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")


def run():
    """Combines all match-level event CSVs into one combined CSV."""
    if not os.path.exists(FLATTENED_DIR):
        print(f"Directory not found: {FLATTENED_DIR}")
        return

    csv_files = [f for f in os.listdir(FLATTENED_DIR) if f.endswith(".csv")]
    if not csv_files:
        print(f"No CSV files found in {FLATTENED_DIR}. Nothing to combine.")
        return

    all_events = []
    for f in csv_files:
        full_path = os.path.join(FLATTENED_DIR, f)
        df = pd.read_csv(full_path)

        # Optionally inject filename-based match name if not present
        if "match_name" not in df.columns:
            df["match_name"] = f.replace(".csv", "")

        all_events.append(df)

    combined_df = pd.concat(all_events, ignore_index=True)
    combined_df.to_csv(COMBINED_PATH, index=False)

    print(f"Combined {len(csv_files)} event files into: {COMBINED_PATH}")
    print(f"Total events written: {len(combined_df)}")
