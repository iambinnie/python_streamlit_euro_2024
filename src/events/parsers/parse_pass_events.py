# === File: src/events/parsers/parse_pass_events.py ===

import pandas as pd
from typing import Dict
from src.events.event_models import PassEvent, BaseEvent


def parse_pass_events(df: pd.DataFrame) -> Dict[str, PassEvent]:
    """
    Convert a DataFrame of Pass events into a dictionary of PassEvent models keyed by event ID.
    Skips rows that raise validation errors or are missing required fields.
    """
    events = {}

    for _, row in df.iterrows():
        try:
            event = PassEvent(
                id=row["id"],
                index=row["index"],
                period=row["period"],
                minute=row["minute"],
                second=row["second"],
                timestamp=row["timestamp"],
                type=row["type"],
                player=row["player"],
                team=row["team"],
                match_id=row["match_id"],
                match_name=row["match_name"],
                x=row["x"],
                y=row["y"],
                end_x=row.get("end_x"),
                end_y=row.get("end_y"),
                outcome=BaseEvent.safe_str(row.get("pass_outcome")),
                length=row.get("pass_length"),
                angle=row.get("pass_angle"),
                recipient=BaseEvent.safe_str(row.get("pass_recipient")),
                height=BaseEvent.safe_str(row.get("pass_height")),
            )
            events[event.id] = event
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    return events
