# === File: download_flatten_combine_statsbomb_data/flatten_statsbomb_events.py ===
"""
Flattens raw StatsBomb Euro‑24 JSON event files into per‑match CSVs,
validates Pass/Carry/Shot coordinates, injects match metadata, and produces
a combined master CSV.

Output:
- Individual CSVs → data/flattened/
- Combined CSV → data/euro24_all_events_combined.csv
- Validation log → data/errors/flatten_report.txt
"""

import os
import glob
import json
from datetime import datetime
from typing import List

import pandas as pd

from src.config.constants import (
    RAW_DIR,
    FLATTENED_DIR,
    BASE_DATA_DIR,
    MATCH_META_PATH,
    ERRORS_DIR,
)

COMBINED_CSV = os.path.join(BASE_DATA_DIR, "euro24_all_events_combined.csv")
REPORT_PATH = os.path.join(ERRORS_DIR, "flatten_report.txt")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def extract_coord(val, idx):
    """Safely return coordinate from list or None."""
    return val[idx] if isinstance(val, list) and len(val) > idx else None


def safe_load_ndjson(json_path: str) -> pd.DataFrame:
    """Reads StatsBomb NDJSON without triggering Pandas dtype inference warnings."""
    with open(json_path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f]
    return pd.json_normalize(records, sep=".")


def flatten_single(json_path: str, csv_path: str, meta_df: pd.DataFrame, report_lines: List[str]) -> bool:
    """Flattens one raw JSON match file into a CSV; always writes CSV but reports validation issues."""
    try:
        df = safe_load_ndjson(json_path)

        # Basic location (start coordinates)
        if "location" in df.columns:
            df["x"] = df["location"].apply(lambda loc: extract_coord(loc, 0))
            df["y"] = df["location"].apply(lambda loc: extract_coord(loc, 1))

        if "pass_end_location" in df.columns:
            df["pass_end_x"] = df["pass_end_location"].apply(lambda loc: extract_coord(loc, 0))
            df["pass_end_y"] = df["pass_end_location"].apply(lambda loc: extract_coord(loc, 1))

        if "carry_end_location" in df.columns:
            df["carry_end_x"] = df["carry_end_location"].apply(lambda loc: extract_coord(loc, 0))
            df["carry_end_y"] = df["carry_end_location"].apply(lambda loc: extract_coord(loc, 1))

        if "shot_end_location" in df.columns:
            df["shot_end_x"] = df["shot_end_location"].apply(lambda loc: extract_coord(loc, 0))
            df["shot_end_y"] = df["shot_end_location"].apply(lambda loc: extract_coord(loc, 1))
            df["shot_end_z"] = df["shot_end_location"].apply(lambda loc: extract_coord(loc, 2))

        # General-purpose end_x, end_y (Pass → Carry → Shot priority)
        df["end_x"] = None
        df["end_y"] = None
        for event_type, (x_col, y_col) in {
            "Pass": ("pass_end_x", "pass_end_y"),
            "Carry": ("carry_end_x", "carry_end_y"),
            "Shot": ("shot_end_x", "shot_end_y"),
        }.items():
            if x_col in df and y_col in df:
                mask = df["type"] == event_type
                df.loc[mask, "end_x"] = df.loc[mask, x_col]
                df.loc[mask, "end_y"] = df.loc[mask, y_col]

        # Inject match metadata
        match_id = int(os.path.basename(json_path).split("_")[0])
        meta_row = meta_df.loc[meta_df["match_id"] == match_id]
        if meta_row.empty:
            report_lines.append(f"[{match_id}]  ERROR  Metadata not found\n")
        else:
            home, away = meta_row.iloc[0][["home_team", "away_team"]]
            df["match_id"] = match_id
            df["match_name"] = f"{home} vs {away}"
            df["home_team"] = home
            df["away_team"] = away

        # Validation (non-blocking): Log missing pass/carry coords
        pass_carry = df[df["type"].isin(["Pass", "Carry"])]
        missing = pass_carry[pass_carry[["end_x", "end_y"]].isna().any(axis=1)]
        if not missing.empty:
            report_lines.append(f"[{match_id}]  WARN  {len(missing)} Pass/Carry rows missing end coords\n")
        else:
            report_lines.append(f"[{match_id}]  OK    Flattened {len(df)} rows\n")

        df.to_csv(csv_path, index=False)
        return True

    except Exception as exc:
        report_lines.append(f"[ERROR]  {os.path.basename(json_path)} :: {exc}\n")
        return False


# ----------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------
def run():
    """Flattens all raw matches and writes a combined CSV."""
    os.makedirs(FLATTENED_DIR, exist_ok=True)
    os.makedirs(ERRORS_DIR, exist_ok=True)

    meta_df = pd.read_csv(MATCH_META_PATH)
    raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))

    report = [f"Flatten run {datetime.now().isoformat()}\n", "-" * 60 + "\n"]
    ok_count = 0

    for raw in raw_files:
        match_id = os.path.basename(raw).split("_")[0]
        csv_path = os.path.join(FLATTENED_DIR, f"{match_id}_events.csv")

        if os.path.exists(csv_path):
            report.append(f"[{match_id}]  SKIP  already exists\n")
            ok_count += 1
            continue

        if flatten_single(raw, csv_path, meta_df, report):
            ok_count += 1

    report.append("-" * 60 + "\n")
    report.append(f"Flattened: {ok_count} matches\n")
    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.writelines(report)

    # Combine CSVs
    all_csvs = glob.glob(os.path.join(FLATTENED_DIR, "*.csv"))
    if not all_csvs:
        print("No CSV files to combine.")
        return

    combined_df = pd.concat((pd.read_csv(p) for p in all_csvs), ignore_index=True)
    combined_df.to_csv(COMBINED_CSV, index=False)
    print(f"[DONE] Combined {len(all_csvs)} CSVs → {COMBINED_CSV}")
    print(f"Total rows combined: {len(combined_df):,}")


if __name__ == "__main__":
    run()
