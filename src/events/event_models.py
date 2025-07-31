"""
Defines core event models for StatsBomb data, including PassEvent and ShotEvent.

- PassEvent: Includes logic for determining completion and arrow coloring.
- ShotEvent: Includes xG scaling, outcome-based coloring, and goal-view support.
"""

from typing import Optional, ClassVar, Dict, List
import pandas as pd
from pydantic import BaseModel

from src.config.colour_mappings import SHOT_OUTCOME_COLOR_MAP, PASS_OUTCOME_COLOR_MAP
from src.events.pitch_config import PitchViewMode
import matplotlib.patches as mpatches


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

    def get_location(self, use_end: bool = False) -> Optional[tuple]:
        """Return (x, y) start location only; end coords handled in subclasses."""
        if self.x is not None and self.y is not None:
            return self.x, self.y
        return None

    def get_outcome_color(self, event_string: Optional[str], mapping: dict) -> str:
        """
        Generic method to return color based on outcome using a mapping dictionary.
        """
        if not event_string:
            return "gray"
        key = event_string.lower()
        for outcome_key, color in mapping.items():
            if outcome_key in key:
                return color
        return "gray"


# ----------------------------------------------------------------------
# PassEvent
# ----------------------------------------------------------------------
class PassEvent(BaseEvent):
    pass_outcome: Optional[str] = None
    pass_length: Optional[float] = None
    pass_angle: Optional[float] = None
    pass_recipient: Optional[str] = None
    pass_height: Optional[str] = None
    pass_end_x: Optional[float] = None
    pass_end_y: Optional[float] = None
    pitch_view: PitchViewMode = PitchViewMode.FULL


    def is_completed(self) -> bool:
        """Return True if the pass is completed (no outcome or specific outcome)."""
        return self.pass_outcome is None

    def get_color(self) -> str:
        """Return color based on pass outcome using external mapping."""
        if self.pass_outcome is None:
            return PASS_OUTCOME_COLOR_MAP.get("complete", "gray")

        key = self.pass_outcome.lower()
        for outcome_key, color in PASS_OUTCOME_COLOR_MAP.items():
            if outcome_key in key:
                return color

        return PASS_OUTCOME_COLOR_MAP.get("other", "gray")

    def to_arrow_coords(self) -> Optional[tuple[float, float, float, float]]:
        if None in (self.x, self.y, self.pass_end_x, self.pass_end_y):
            return None
        return (self.x, self.y, self.pass_end_x, self.pass_end_y)

    @classmethod
    def get_legend_patches(cls):
        return [
            mpatches.Patch(color=color, label=key.title())
            for key, color in PASS_OUTCOME_COLOR_MAP.items()
        ]

# ----------------------------------------------------------------------
# ShotEvent
# ----------------------------------------------------------------------
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
        """Color based on shot outcome."""
        return self.get_outcome_color(self.shot_outcome, SHOT_OUTCOME_COLOR_MAP)

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


    @classmethod
    def get_legend_patches(cls):
        return [
            mpatches.Patch(color=color, label=key.title())
            for key, color in SHOT_OUTCOME_COLOR_MAP.items()
        ]

