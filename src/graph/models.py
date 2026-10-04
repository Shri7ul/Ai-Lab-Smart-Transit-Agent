from dataclasses import dataclass, field
from typing import List

@dataclass
class Leg:
    frm: str
    to: str
    mode: str
    time: float
    cost: float
    distance: float

@dataclass
class Route:
    path: List[str]
    legs: List[Leg] = field(default_factory=list)

    @property
    def total_time(self) -> float:
        return sum(leg.time for leg in self.legs)

    @property
    def total_cost(self) -> float:
        return sum(leg.cost for leg in self.legs)

    @property
    def total_distance(self) -> float:
        return sum(leg.distance for leg in self.legs)

    @property
    def num_transfers(self) -> int:
        modes = [leg.mode for leg in self.legs]
        return sum(1 for a, b in zip(modes, modes[1:]) if a != b)

    @property
    def walking_distance(self) -> float:
        return sum(leg.distance for leg in self.legs if leg.mode == "walk")

    @property
    def mode_sequence(self) -> List[str]:
        seq = []
        for leg in self.legs:
            if not seq or seq[-1] != leg.mode:
                seq.append(leg.mode)
        return seq
