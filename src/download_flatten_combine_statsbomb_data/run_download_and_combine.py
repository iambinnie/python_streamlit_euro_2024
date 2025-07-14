# === File: run_download_and_combine.py ===

"""
Orchestrates the full StatsBomb data ETL pipeline:
- Create required directories
- Download raw data (if not already downloaded)
- Remove any non-raw data (cleans out bad intermediate states)
- Flatten all raw JSON event files into a combined CSV

Each step can be toggled independently via function parameters.
"""

from src.download_flatten_combine_statsbomb_data import (
    create_directories_if_not_exists,
    download_statsbomb_data_if_not_exists,
    remove_any_non_raw_statsbomb_data_if_exists,
    flatten_statsbomb_events,
    combine_flattened_event_csvs
)


def run(
    create_dirs: bool = True,
    download_data: bool = True,
    clear_non_raw: bool = True,
    flatten_data: bool = True,
    combine_data: bool = True
):
    print("Running StatsBomb ETL pipeline...\n")

    if create_dirs:
        print("Step 1: Creating directories...")
        create_directories_if_not_exists.run()

    if download_data:
        print("Step 2: Downloading raw data (if not already present)...")
        download_statsbomb_data_if_not_exists.run()

    if clear_non_raw:
        print("Step 3: Removing non-raw/intermediate files...")
        remove_any_non_raw_statsbomb_data_if_exists.run()

    if flatten_data:
        print("Step 4: Flattening event data to CSV...")
        flatten_statsbomb_events.run()

    if combine_data:
        print("Step 5: Combining all data into single CSV")
        combine_flattened_event_csvs.run()

    print("\nPipeline complete.")


# Optional: run all steps by default when this script is run directly
if __name__ == "__main__":
    run()
