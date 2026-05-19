from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum

from .player import Player
from .board import Board


class GamePhase(Enum):
    SETUP = "setup"
    BEGIN_ROUND = "begin_round"
    PLAYER_TURNS = "player_turns"
    COMBAT = "combat"
    MAKERS = "makers"
    RECALL = "recall"
    GAME_OVER = "game_over"


@dataclass
class Game:
    """Main game state - single source of truth"""
    
    # Players
    players: List[Player] = field(default_factory=list)
    current_player_index: int = 0
    first_player_index: int = 0
    
    # Board
    board: Board = None
    
    # Game state
    current_phase: GamePhase = GamePhase.SETUP
    current_round: int = 0
    
    # Config
    player_count: int = 2
    use_choam_module: bool = False
    seed: Optional[int] = None
    
    # Helper properties
    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]
    
    @property
    def first_player(self) -> Player:
        return self.players[self.first_player_index]
    
    # Core methods
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get player by ID"""
        for player in self.players:
            if player.player_id == player_id:
                return player
        return None

    def advance_to_next_player(self):
        """Move to next player in turn order"""
        self.current_player_index = (self.current_player_index + 1) % self.player_count
