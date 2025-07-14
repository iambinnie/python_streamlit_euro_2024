from pydantic import BaseModel
from typing import Optional
import pandas as pd
from src.events.pitch_config import PitchViewMode


class BaseEvent(BaseModel):
    id: str
    index: int
    period: int
    minute: int
    second: int
    timestamp: str
    type: str
    player: str
    team: str
    match_id: int
    match_name: str
    x: Optional[float]
    y: Optional[float]

    @staticmethod
    def safe_str(val):
        """Convert NaN or float('nan') to None; otherwise return as-is."""
        try:
            if val is None:
                return None
            if isinstance(val, float) and pd.isna(val):
                return None
            return val
        except Exception:
            return None


class PassEvent(BaseEvent):
    end_x: Optional[float]
    end_y: Optional[float]
    outcome: Optional[str] = None           # from "pass_outcome"
    length: Optional[float] = None          # from "pass_length"
    angle: Optional[float] = None           # from "pass_angle"
    recipient: Optional[str] = None         # from "pass_recipient"
    height: Optional[str] = None            # from "pass_height"

    pitch_view: PitchViewMode = PitchViewMode.FULL

    def is_completed(self) -> bool:
        return self.outcome is None

    def to_arrow_coords(self) -> Optional[tuple[float, float, float, float]]:
        if None in (self.x, self.y, self.end_x, self.end_y):
            return None
        return (self.x, self.y, self.end_x, self.end_y)


class ShotEvent(BaseEvent):
    shot_outcome: Optional[str] = None           # e.g., "Goal", "Off T", "Saved", "Blocked"
    shot_xg: Optional[float] = None              # Expected goals value
    shot_end_x: Optional[float] = None
    shot_end_y: Optional[float] = None

    pitch_view: PitchViewMode = PitchViewMode.HALF

    def get_color(self) -> str:
        """Map outcome to display color."""
        if not self.shot_outcome:
            return "white"
        outcome = self.shot_outcome.lower()
        if "goal" in outcome or "on t" in outcome:
            return "green"
        elif "off" in outcome:
            return "red"
        elif "block" in outcome:
            return "blue"
        elif "save" in outcome:
            return "orange"
        return "gray"

    def get_radius(self) -> float:
        """Scale xG to dot size."""
        if self.shot_xg is None:
            return 200
        return max(100, self.shot_xg * 1000)

    def get_location(self, use_end=False) -> Optional[tuple[float, float]]:
        if use_end:
            if self.shot_end_x is not None and self.shot_end_y is not None and not any(
                    pd.isna([self.shot_end_x, self.shot_end_y])):
                return self.shot_end_x, self.shot_end_y
        if self.x is not None and self.y is not None and not any(pd.isna([self.x, self.y])):
            return self.x, self.y
        return None

