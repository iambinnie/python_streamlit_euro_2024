# === File: download_and_flatten_statsbomb_data/download_statsbomb_data_if_not_exists.py ===

"""
Downloads raw StatsBomb event data for Euro 2024.
- Loads existing match metadata from CSV if present.
- Otherwise, fetches match list via API and saves locally.
- Downloads raw event data as JSON per match, skipping existing files.
- Logs any errors to a timestamped log file.
"""

import os
import pandas as pd
from statsbombpy import sb
from datetime import datetime

from src.config.constants import (
    COMP_ID,
    SEASON_ID,
    MATCH_META_PATH,
    ERRORS_DIR,
    ERROR_LOG_PATH,
    RAW_DIR
)


def run():
    # Ensure error dir exists in case step 1 was skipped
    os.makedirs(ERRORS_DIR, exist_ok=True)

    # Step 1: Load or download match metadata
    if os.path.exists(MATCH_META_PATH):
        matches = pd.read_csv(MATCH_META_PATH)
        print(f"Loaded existing match metadata: {len(matches)} matches.")
    else:
        matches = sb.matches(competition_id=COMP_ID, season_id=SEASON_ID)
        matches.to_csv(MATCH_META_PATH, index=False)
        print(f"Downloaded and saved match metadata: {len(matches)} matches.")

    # Step 2: Download event data (if not already present)
    downloaded_count = 0
    for _, row in matches.iterrows():
        match_id = row["match_id"]
        home = row["home_team"]
        away = row["away_team"]
        filename = f"{match_id}_{home}_vs_{away}".replace(" ", "_") + ".json"
        filepath = os.path.join(RAW_DIR, filename)

        if os.path.exists(filepath):
            print(f"Exists: {filename}")
            continue

        try:
            print(f"Downloading: {home} vs {away} (match_id={match_id})")
            events = sb.events(match_id=match_id)
            events.to_json(filepath, orient="records", lines=True)
            downloaded_count += 1
        except Exception as e:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now().isoformat()}] {match_id} - {home} vs {away} - ERROR: {str(e)}\n")
            print(f"ERROR downloading match {match_id}: {e}")

    print(f"\nDownload complete. {downloaded_count} new files saved.")
    print(f"Raw files located in: {RAW_DIR}")
