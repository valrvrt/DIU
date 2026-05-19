from dataclasses import dataclass, field
from typing import Optional
from .boardspace import BoardSpace, ObservationPost
from .card import ConflictCard, ImperiumCard, IntrigueCard, ContractCard

@dataclass
class Board:
    
    # Board locations
    spaces: list[BoardSpace] = field(default_factory=list)
    observation_posts: list[ObservationPost] = field(default_factory=list)
    
    # Conflict system
    conflict_deck: list[ConflictCard] = field(default_factory=list)
    current_conflict: Optional[ConflictCard] = None
    resolved_conflicts: list[ConflictCard] = field(default_factory=list)
    
    # Imperium cards
    imperium_deck: list[ImperiumCard] = field(default_factory=list)
    imperium_row: list[ImperiumCard] = field(default_factory=list)  # 5 face-up cards
    imperium_discard: list[ImperiumCard] = field(default_factory=list)
    
    # Reserve piles
    reserve_prepare_the_way: list[ImperiumCard] = field(default_factory=list)
    reserve_spice_must_flow: list[ImperiumCard] = field(default_factory=list)
    
    # Intrigue cards
    intrigue_deck: list[IntrigueCard] = field(default_factory=list)
    intrigue_discard: list[IntrigueCard] = field(default_factory=list)
    
    # Contracts (CHOAM module)
    contract_deck: list[ContractCard] = field(default_factory=list)
    contract_row: list[ContractCard] = field(default_factory=list)  # 2 face-up
    
    # Shield
    shield_active: bool = True  # Can be destroyed
    
    def refill_imperium_row(self):
        """Refill Imperium row to 5 cards"""
        while len(self.imperium_row) < 5 and self.imperium_deck:
            self.imperium_row.append(self.imperium_deck.pop(0))
    
    def refill_contract_row(self):
        """Refill contract row to 2 cards"""
        while len(self.contract_row) < 2 and self.contract_deck:
            self.contract_row.append(self.contract_deck.pop(0))
        
    def get_spaces(self):
        return self.spaces

    def get_space_by_id(self, space_id):
        for space in self.spaces:
            if space.id == space_id:
                return space
        return None