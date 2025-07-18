# === File: src/download_flatten_combine_statsbomb_data/remove_any_non_raw_statsbomb_data_if_exists.py ===

"""
Removes any non-raw (intermediate) files to reset the pipeline cleanly.
"""

import os
import shutil
from src.config.constants import FLATTENED_DIR


def run():
    if os.path.exists(FLATTENED_DIR):
        files = os.listdir(FLATTENED_DIR)
        if files:
            print(f"Removing {len(files)} files from {FLATTENED_DIR}...")
            shutil.rmtree(FLATTENED_DIR)
            os.makedirs(FLATTENED_DIR, exist_ok=True)
        else:
            print(f"No files to remove in: {FLATTENED_DIR}")
    else:
        print(f"Flattened directory does not exist. Creating it now.")
        os.makedirs(FLATTENED_DIR, exist_ok=True)
