from typing import Dict
from src.events.event_models import ShotEvent

def parse_shot_events(df) -> Dict[str, ShotEvent]:
    events = {}
    for _, row in df.iterrows():
        event = ShotEvent(
            id=row.get("id"),
            index=row.get("index"),
            match_id=row.get("match_id"),
            match_name=row.get("match_name"),
            period=row.get("period"),
            timestamp=row.get("timestamp"),
            type=row.get("type"),
            minute=row.get("minute"),
            second=row.get("second"),
            player=row.get("player"),
            team=row.get("team"),
            x=row.get("x"),
            y=row.get("y"),
            shot_end_x=row.get("shot_end_x"),
            shot_end_y=row.get("shot_end_y"),
            shot_end_z=row.get("shot_end_z"),  # ✅ NEW!
            shot_xg=row.get("shot_statsbomb_xg"),
            shot_outcome=row.get("shot_outcome"),
        )
        events[event.id] = event
    return events
