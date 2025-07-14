# === File: download_and_flatten_statsbomb_data/create_directories_if_not_exists.py ===

"""
Creates required directories for the StatsBomb ETL pipeline.
Appends setup status to a log file with timestamps.

Directories:
- raw/
- flattened/
- errors/
- base data dir (if not already created)
"""

import os
from datetime import datetime
from src.config.constants import BASE_DATA_DIR

# Define full paths for all subdirectories
REQUIRED_DIRS = [
    BASE_DATA_DIR,
    os.path.join(BASE_DATA_DIR, "raw"),
    os.path.join(BASE_DATA_DIR, "flattened"),
    os.path.join(BASE_DATA_DIR, "errors")
]

LOG_PATH = os.path.join(BASE_DATA_DIR, "setup.log")


def run():
    """Creates necessary directories if they don't exist, and logs the outcome."""
    log_lines = [f"[{datetime.now().isoformat()}] Directory setup check:\n"]

    for directory in REQUIRED_DIRS:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            log_lines.append(f"  CREATED: {directory}\n")
        else:
            log_lines.append(f"  EXISTS:  {directory}\n")

    with open(LOG_PATH, "a", encoding="utf-8") as log_file:
        log_file.writelines(log_lines)

    print("Directory check complete. Log written to:", LOG_PATH)
