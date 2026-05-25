from dataclasses import dataclass, field
from typing import Optional

@dataclass
class BoardSpace:
    id: str
    name: str
    
    # Agent placement
    agent_icon: str  # Which icon allows placement here
    occupied_by: Optional[str] = None  # player_id if occupied
    infiltrated_by: Optional[str] = None  # player_id if spy infiltrated
    
    # Faction (None if not faction-affiliated)
    faction: Optional[str] = None  # "fremen", "emperor", etc.
    
    # Cost to place agent here (array of effect objects matching JSON format)
    cost: list = field(default_factory=list)  # e.g., [{"type": "resource", "resource": "water", "amount": 1}]
    
    # Prerequisites (old format, kept for compatibility)
    required_influence: Optional[dict[str, int]] = None  # e.g., {"fremen": 2}

    # Prerequisites (new JSON format with check array)
    check: Optional[list] = None  # e.g., [{"type": "influence", "target": "fremen", "amount": 2}]

    # Effects when agent placed (old format - dict)
    effects: dict[str, int] = field(default_factory=dict)

    # Rewards when agent placed (new format - list of effect objects)
    reward: list = field(default_factory=list)  # e.g., [{"type": "resource", "resource": "water", "amount": 1}]
    
    # Combat-related
    is_combat_space: bool = False
    
    # Maker-related (Spice accumulation)
    is_maker_space: bool = False
    spice_bonus: int = 0  # Accumulates each round if not visited
    
    # Critical location (Arrakeen, Spice Refinery, Imperial Basin)
    is_critical_location: bool = False
    controlled_by: Optional[str] = None  # player_id
    control_bonus: dict[str, int] = field(default_factory=dict)  # Given when anyone visits
    
    # Observation post (for spy network)
    is_observation_post: bool = False
    connected_to: list[str] = field(default_factory=list)  # Location IDs connected via spy

@dataclass
class ObservationPost:
    """Separate class for observation posts might be cleaner"""
    id: str
    name: str
    occupied_by: Optional[str] = None  # player_id of spy owner
    connected_locations: list[str] = field(default_factory=list)  # Location IDs