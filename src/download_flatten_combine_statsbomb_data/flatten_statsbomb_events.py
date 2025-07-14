"""
Flattens nested StatsBomb event JSON data into a tidy, analyzable DataFrame.
Adds event-specific coordinate fields (e.g., pass_end_x, shot_end_x),
plus general-purpose end_x/y for plotting.
"""

import pandas as pd
import numpy as np
import os
import json
from glob import glob


def load_event_data(json_path: str) -> pd.DataFrame:
    with open(json_path, encoding="utf-8") as f:
        raw = json.load(f)
    df = pd.json_normalize(raw, sep=".")
    return df


def extract_coord(location, index):
    if isinstance(location, list) and len(location) > index:
        return location[index]
    return np.nan


def add_end_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    if "pass.end_location" in df:
        df["pass_end_x"] = df["pass.end_location"].apply(lambda loc: extract_coord(loc, 0))
        df["pass_end_y"] = df["pass.end_location"].apply(lambda loc: extract_coord(loc, 1))

    if "carry.end_location" in df:
        df["carry_end_x"] = df["carry.end_location"].apply(lambda loc: extract_coord(loc, 0))
        df["carry_end_y"] = df["carry.end_location"].apply(lambda loc: extract_coord(loc, 1))

    if "shot_end_location" in df:
        df["shot_end_x"] = df["shot_end_location"].apply(lambda loc: extract_coord(loc, 0))
        df["shot_end_y"] = df["shot_end_location"].apply(lambda loc: extract_coord(loc, 1))

    return df


def assign_general_end_coords(df: pd.DataFrame) -> pd.DataFrame:
    df["end_x"] = None
    df["end_y"] = None

    mappings = {
        "Pass": ("pass_end_x", "pass_end_y"),
        "Carry": ("carry_end_x", "carry_end_y"),
        "Shot": ("shot_end_x", "shot_end_y"),
    }

    for event_type, (x_col, y_col) in mappings.items():
        if x_col in df and y_col in df:
            mask = df["type"] == event_type
            df.loc[mask, "end_x"] = df.loc[mask, x_col]
            df.loc[mask, "end_y"] = df.loc[mask, y_col]

    return df


def validate_end_coordinates(df: pd.DataFrame) -> None:
    for event_type in ["Pass", "Carry", "Shot"]:
        x_col = f"{event_type.lower()}_end_x"
        y_col = f"{event_type.lower()}_end_y"

        if x_col in df and y_col in df:
            missing = df[df["type"] == event_type][df[[x_col, y_col]].isna().any(axis=1)]
            if not missing.empty:
                print(f"[WARN] {len(missing)} {event_type} events missing {x_col}/{y_col} values.")


def flatten_events(json_path: str) -> pd.DataFrame:
    df = load_event_data(json_path)
    df = add_end_coordinates(df)
    df = assign_general_end_coords(df)
    validate_end_coordinates(df)
    return df


def run():
    """
    Batch flattens all match JSON files under data/raw/events/
    and writes CSVs to data/flattened/events/
    """
    input_dir = os.path.join("data", "raw", "events")
    output_dir = os.path.join("data", "flattened", "events")
    os.makedirs(output_dir, exist_ok=True)

    json_paths = sorted(glob(os.path.join(input_dir, "match_*.json")))
    if not json_paths:
        print("[INFO] No event JSON files found.")
        return

    for json_path in json_paths:
        match_id = os.path.splitext(os.path.basename(json_path))[0].replace("match_", "")
        output_csv = os.path.join(output_dir, f"match_{match_id}.csv")

        df = flatten_events(json_path)
        df.to_csv(output_csv, index=False)
        print(f"[OK] Flattened match {match_id} → {output_csv}")

    print("[DONE] All matches flattened.")


if __name__ == "__main__":
    run()
