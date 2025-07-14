"""
Flattens raw StatsBomb Euro‑24 JSON event files into per‑match CSVs,
validates Pass/Carry coordinates, injects match metadata, and produces
a combined master CSV.

Modules and constants imported from config.constants.
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


def flatten_single(json_path: str, csv_path: str, meta_df: pd.DataFrame, report_lines: List[str]) -> bool:
    """Flattens one raw JSON match file into a CSV; returns True on success."""
    try:
        records = [json.loads(line) for line in open(json_path, "r", encoding="utf-8")]
        df = pd.json_normalize(records, sep=".")

        # Basic coordinates
        df["x"] = df["location"].apply(lambda loc: extract_coord(loc, 0))
        df["y"] = df["location"].apply(lambda loc: extract_coord(loc, 1))

        # Pass & Carry end locations (StatsBomb flat keys)
        df["end_x"] = (
            df["pass_end_location"].apply(lambda loc: extract_coord(loc, 0))
            if "pass_end_location" in df
            else None
        )
        df["end_y"] = (
            df["pass_end_location"].apply(lambda loc: extract_coord(loc, 1))
            if "pass_end_location" in df
            else None
        )

        if "carry_end_location" in df:
            carry_x = df["carry_end_location"].apply(lambda loc: extract_coord(loc, 0))
            carry_y = df["carry_end_location"].apply(lambda loc: extract_coord(loc, 1))
            df["end_x"] = df["end_x"].combine_first(carry_x)
            df["end_y"] = df["end_y"].combine_first(carry_y)

        # Shot end location (optional)
        if "shot.end_location" in df:
            df["shot_end_x"] = df["shot.end_location"].apply(lambda loc: extract_coord(loc, 0))
            df["shot_end_y"] = df["shot.end_location"].apply(lambda loc: extract_coord(loc, 1))

        # Inject match metadata
        match_id = int(os.path.basename(json_path).split("_")[0])
        meta_row = meta_df.loc[meta_df["match_id"] == match_id]
        if meta_row.empty:
            report_lines.append(f"[{match_id}]  ERROR  Metadata not found\n")
            return False

        home, away = meta_row.iloc[0][["home_team", "away_team"]]
        df["match_id"] = match_id
        df["match_name"] = f"{home} vs {away}"
        df["home_team"] = home
        df["away_team"] = away

        # Validation: Pass / Carry rows must have end_x & end_y
        pass_carry = df[df["type"].isin(["Pass", "Carry"])]
        missing = pass_carry[pass_carry[["end_x", "end_y"]].isna().any(axis=1)]
        if not missing.empty:
            report_lines.append(f"[{match_id}]  FAIL  {len(missing)} Pass/Carry rows missing end coords\n")
            return False

        df.to_csv(csv_path, index=False)
        report_lines.append(f"[{match_id}]  OK    Flattened {len(df)} rows\n")
        return True

    except Exception as exc:
        report_lines.append(f"[ERROR]  {os.path.basename(json_path)} :: {exc}\n")
        return False


# ----------------------------------------------------------------------
# Orchestrator
# ----------------------------------------------------------------------
def run():
    """Flattens all raw matches and writes a combined CSV if every match validates."""
    os.makedirs(FLATTENED_DIR, exist_ok=True)
    os.makedirs(ERRORS_DIR, exist_ok=True)

    meta_df = pd.read_csv(MATCH_META_PATH)
    raw_files = sorted(glob.glob(os.path.join(RAW_DIR, "*.json")))

    report = [f"Flatten run {datetime.now().isoformat()}\n", "-" * 60 + "\n"]
    ok_count = fail_count = 0

    for raw in raw_files:
        match_id = os.path.basename(raw).split("_")[0]
        csv_path = os.path.join(FLATTENED_DIR, f"{match_id}_events.csv")

        if os.path.exists(csv_path):
            report.append(f"[{match_id}]  SKIP  already exists\n")
            ok_count += 1
            continue

        success = flatten_single(raw, csv_path, meta_df, report)
        if success:
            ok_count += 1
        else:
            fail_count += 1

    # Write validation report
    report.append("-" * 60 + "\n")
    report.append(f"Success: {ok_count}   Failures: {fail_count}\n")
    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.writelines(report)

    if fail_count:
        print("Flatten completed with failures — see report for details.")
        return

    # Combine CSVs
    all_csvs = glob.glob(os.path.join(FLATTENED_DIR, "*.csv"))
    combined_df = pd.concat((pd.read_csv(p) for p in all_csvs), ignore_index=True)
    combined_df.to_csv(COMBINED_CSV, index=False)
    print(f"Combined CSV written to: {COMBINED_CSV}")


# ----------------------------------------------------------------------
# CLI entry‑point
# ----------------------------------------------------------------------
if __name__ == "__main__":
    run()
