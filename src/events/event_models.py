"""
Defines core event models for StatsBomb data, including PassEvent and ShotEvent.

- PassEvent: Includes logic for determining completion and arrow coloring.
- ShotEvent: Includes xG scaling, outcome-based coloring, and goal-view support.
"""

from typing import Optional
from pydantic import BaseModel
from enum import Enum


# ----------------------------------------------------------------------
# Pitch view modes
# ----------------------------------------------------------------------
class PitchViewMode(Enum):
    FULL = "full"
    HALF = "half"
    GOAL = "goal"

    def use_half_pitch(self) -> bool:
        """Return True if the half-pitch should be used."""
        return self in {PitchViewMode.HALF, PitchViewMode.GOAL}
        #return self in {PitchViewMode.HALF}


# ----------------------------------------------------------------------
# Base event model
# ----------------------------------------------------------------------
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
    pitch_view: PitchViewMode = PitchViewMode.FULL

    @staticmethod
    def safe_str(val) -> str:
        """Safe string conversion for None values."""
        return str(val) if val is not None else "-"

    def get_location(self, use_end: bool = False) -> Optional[tuple]:
        """Return (x, y) for plotting, switching to end coords if requested."""
        if use_end and self.end_x is not None and self.end_y is not None:
            return self.end_x, self.end_y
        if self.x is not None and self.y is not None:
            return self.x, self.y
        return None


# ----------------------------------------------------------------------
# PassEvent
# ----------------------------------------------------------------------
class PassEvent(BaseEvent):
    pass_outcome: Optional[str] = None
    pass_end_x: Optional[float] = None
    pass_end_y: Optional[float] = None

    def is_completed(self) -> bool:
        """Return True if the pass is completed (no outcome or specific outcome)."""
        return self.pass_outcome is None or self.pass_outcome.lower() == "complete"

    def get_color(self) -> str:
        """Return color based on pass completion."""
        return "green" if self.is_completed() else "red"


# ----------------------------------------------------------------------
# ShotEvent
# ----------------------------------------------------------------------

OUTCOME_COLOR_MAP = {
    "goal": "gold",
    "saved": "orange",
    "saved to post": "orange",
    "saved to woodwork": "orange",
    "off t": "red",          # "off target" variants
    "post": "blue",          # includes "hit the post"/"off the post"
    "bar": "blue",           # includes "crossbar"
    "blocked": "blue",
    "deflected": "blue",
    "other": "gray",         # catch-all for unusual categories
}

class ShotEvent(BaseEvent):
    shot_xg: float
    shot_outcome: Optional[str] = None
    shot_end_x: Optional[float] = None
    shot_end_y: Optional[float] = None
    shot_end_z: Optional[float] = None
    pitch_view: PitchViewMode = PitchViewMode.HALF

    def get_radius(self) -> float:
        """Scale dot size based on xG (0–1)."""
        return max(30, self.shot_xg * 300)

    def get_color(self) -> str:
        """Map shot outcome to standardized color groups."""
        if not self.shot_outcome:
            return "gray"
        key = self.shot_outcome.lower()
        for outcome_key, color in OUTCOME_COLOR_MAP.items():
            if outcome_key in key:
                return color
        return "gray"  # fallback for unknown outcomes

    def get_location(self, use_end: bool = False) -> Optional[tuple]:
        """Return start or end shot location (x, y)."""
        if use_end and self.shot_end_x is not None and self.shot_end_y is not None:
            return self.shot_end_x, self.shot_end_y
        return super().get_location(use_end=False)

    def get_goal_coordinates(self):
        """Returns normalized goal-view coordinates if available."""
        if self.shot_end_y is None:
            return None
        gx = (self.shot_end_y - 36) / 8 * 7.32
        gy = self.shot_end_z if self.shot_end_z is not None else 0
        return gx, gy
