# === File: src/download_flatten_combine_statsbomb_data/create_directories_if_not_exists.py ===

"""
Creates required directories for StatsBomb data ETL if they don't exist.
"""

import os
from src.config.constants import BASE_DATA_DIR, RAW_DIR, ERRORS_DIR, FLATTENED_DIR


def run():
    os.makedirs(BASE_DATA_DIR, exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(ERRORS_DIR, exist_ok=True)
    os.makedirs(FLATTENED_DIR, exist_ok=True)

    log_path = os.path.join(BASE_DATA_DIR, "setup.log")
    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write("Directory check complete.\n")

    print(f"Directory check complete. Log written to: {log_path}")
