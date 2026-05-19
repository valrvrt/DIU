
from dataclasses import dataclass, field
from typing import Literal, Optional
from enum import Enum

class CardType(Enum):
    IMPERIUM = "Imperium"
    INTRIGUE = "Intrigue"
    CONTRACT = "Contract"
    CONFLICT = "Conflict"
    LEADER = "Leader"

class IntriguePhase(Enum):
    PLOT = "Plot"
    COMBAT = "Combat"
    END_GAME = "End Game"

@dataclass
class Card:
    name: str
    type: str
    card_type: CardType
    in_hand: bool = False
    in_play: bool = False
    in_trash: bool = False


@dataclass
class ImperiumCard(Card):
    id: str = ""
    cost: int = 0
    factions: list[str] = field(default_factory=list)
    starting_hand: bool = False
    on_acquire_effects: dict[str, int] = field(default_factory=dict)
    agent_icons: list[str] = field(default_factory=list)
    agent_effects: dict[str, int] = field(default_factory=dict)
    reveal_effects: dict[str, int] = field(default_factory=dict)


@dataclass
class IntrigueCard(Card):
    id: str = ""
    phases: list[IntriguePhase] = field(default_factory=list)
    cost: dict[str, int] = field(default_factory=dict)
    played_gain: dict[str, int] = field(default_factory=dict)
    conditional_gain: dict[str, int] = field(default_factory=dict)


@dataclass
class ContractCard(Card):
    id: str = ""
    completion_type: Literal["location", "harvest", "immediate", "acquire_card"] = "immediate"
    completion_target: Optional[str] = None
    required_spice: int = 0
    rewards: dict[str, int] = field(default_factory=dict)


@dataclass
class ConflictCard(Card):
    id: str = ""
    level: int = 1  # Conflict level (1, 2, or 3)
    tag: str = ""  # Tag for objective matching ("crysknife", "desert-mouse", "ornithopter")
    rewards: list[dict[str, int]] = field(default_factory=list)
    location: Optional[str] = None
    battle_icon: Optional[str] = None
    wall: bool = False


@dataclass
class LeaderCard(Card):
    id: str = ""
    ring: dict[str, int] = field(default_factory=dict)
    passive_condition: dict[str, int] = field(default_factory=dict)
    passive_gain: dict[str, int] = field(default_factory=dict)


@dataclass
class ObjectiveCard:
    """Objective card (secret goal distributed at setup)."""
    id: int
    name: str
    tag: str  # "desert-mouse", "ornithopter", "crysknife"
    n_players: list[int] = field(default_factory=list)  # Valid for which player counts