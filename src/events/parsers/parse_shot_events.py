import pandas as pd
from typing import Dict
from src.events.event_models import ShotEvent, BaseEvent


def parse_shot_events(df: pd.DataFrame) -> Dict[str, ShotEvent]:
    """
    Convert a DataFrame of Shot events into a dictionary of ShotEvent models keyed by event ID.
    Skips rows with missing required fields or that raise validation errors.
    """
    events = {}

    for _, row in df.iterrows():
        try:
            event = ShotEvent(
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
                shot_outcome=BaseEvent.safe_str(row.get("shot_outcome")),
                shot_xg=row.get("shot_statsbomb_xg"),
                shot_end_x=row.get("shot_end_x"),
                shot_end_y=row.get("shot_end_y")
            )
            events[event.id] = event
        except Exception as e:
            print(f"Skipping row due to error: {e}")
            continue

    return events

