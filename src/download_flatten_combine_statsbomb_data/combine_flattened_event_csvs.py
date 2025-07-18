# === File: src/download_flatten_combine_statsbomb_data/combine_flattened_event_csvs.py ===

"""
Combines all match-level flattened event CSVs into a single CSV for analysis.
Final output saved as 'euro24_all_events_combined.csv' in the data directory.
"""

import os
import pandas as pd
from glob import glob

from src.config.constants import FLATTENED_DIR, BASE_DATA_DIR


def run():
    """Combines all match-level CSVs in FLATTENED_DIR into one CSV."""
    csv_paths = sorted(glob(os.path.join(FLATTENED_DIR, "*.csv")))
    if not csv_paths:
        print(f"No CSV files found in {FLATTENED_DIR}. Nothing to combine.")
        return

    combined_df = pd.concat([pd.read_csv(path) for path in csv_paths], ignore_index=True)

    output_csv = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")
    combined_df.to_csv(output_csv, index=False)

    print(f"[DONE] Combined {len(csv_paths)} CSVs → {output_csv}")
    print(f"Total rows combined: {len(combined_df):,}")


if __name__ == "__main__":
    run()
