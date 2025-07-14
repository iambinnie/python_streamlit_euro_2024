from enum import Enum


class PitchViewMode(str, Enum):
    FULL = "full"
    HALF = "half"
    GOAL = "goal"
    KEEPER = "keeper"

    def use_half_pitch(self) -> bool:
        return self == PitchViewMode.HALF
