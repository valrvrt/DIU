""" Tout ce qui concerne le joueur"""
from dataclasses import dataclass, field
from typing import List

from .deck import Deck
from .card import ContractCard, LeaderCard, ConflictCard


@dataclass
class Player:
    # Required fields (no defaults) MUST come first
    player_id: str
    name: str
    leader: LeaderCard
    color: str
    deck: Deck
    hand: Deck
    discard_pile: Deck

    # Optional fields (with defaults)
    intrigue_cards: List = field(default_factory=list)
    contracts_active: list[ContractCard] = field(default_factory=list)
    contracts_completed: list[ContractCard] = field(default_factory=list)
    conflict_cards_won: list[ConflictCard] = field(default_factory=list)

    # Resources
    solari: int = 0
    spice: int = 0
    water: int = 1
    victory_points: int = 0
    has_maker_hooks: bool = False

    # Troops
    troops_in_garrison: int = 3
    troops_in_conflict: int = 0
    troops_in_reserve: int = 9
    sandworms_in_conflict: int = 0

    # Agents
    total_available_agents: int = 2
    agents_available: int = 2
    agents_placed: list[str] = field(default_factory=list)

    # Spies
    total_available_spies: int = 3
    spies_available: int = 3
    spies_placed: list[str] = field(default_factory=list)

    # Influence tracks
    fremen_influence: int = 0
    bene_gesserit_influence: int = 0
    spacing_guild_influence: int = 0
    emperor_influence: int = 0

    # Alliance tokens
    fremen_alliance: bool = False
    bene_gesserit_alliance: bool = False
    spacing_guild_alliance: bool = False
    emperor_alliance: bool = False

    # Control markers
    controlled_locations: list[str] = field(default_factory=list)

    # Turn state
    has_revealed_this_round: bool = False
    played_cards_this_turn: List = field(default_factory=list)  # Cards played during current turn
    acquired_cards_this_turn: List = field(default_factory=list)  # Cards acquired during reveal turn
    discarded_cards_this_turn: List = field(default_factory=list)  # Cards discarded this turn
    recalled_spy_this_turn: bool = False  # Whether a spy was recalled this turn
    placed_on_maker_this_turn: bool = False  # Whether agent was placed on Maker space

    # Player type
    is_human: bool = False  # True for the human player, False for bots

    # Council
    has_high_council_sit = False

    # Turn-scoped restrictions (e.g. Shaddam "no_troop_deployment_this_turn")
    turn_restrictions: List = field(default_factory=list)

    # Victory Points tracking
    tag_pair_vp: int = 0  # VP from conflict/objective tag pairs (tracked separately)
    objectives: List = field(default_factory=list)  # Objective cards distributed at setup
    # VP attributed by source for the breakdown display, e.g.
    # {"Influence": 2, "Alliances": 1, "Conflicts": 3, "Contracts": 1, "Cards": 2}
    vp_sources: dict = field(default_factory=dict)

    # Combat strength calculation
    @property
    def combat_strength(self) -> int:
        """Calculate current combat strength"""
        if self.troops_in_conflict == 0:
            return 0  # Must have at least 1 troop

        strength = self.troops_in_conflict * 2  # 2 per troop
        strength += self.sandworms_in_conflict * 3  # 3 per sandworm
        # Swords are added during reveal turn, not stored here
        return strength
