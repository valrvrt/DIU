"""
MAKERS Manager - Manages the MAKERS phase.

Responsibilities:
- Add bonus spice to maker spaces (if no agent present)
- Track bonus spice accumulation on the board
"""

from typing import Dict, Any, List
from ..models.game import Game
from ..models.boardspace import BoardSpace
from .game_state import GameState


class MakersManager:
    """
    Manages the MAKERS phase.

    MAKERS Phase Flow:
    1. For each boardspace with maker=true:
       - If no agent is present (occupied_by is None):
         - Add 1 bonus spice to that space
    2. Bonus spice accumulates until a player claims the space
    3. When a player places an agent on a maker space:
       - They collect all bonus spice from that space
       - Bonus spice on that space resets to 0
    """

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    def execute_makers_phase(self) -> Dict[str, Any]:
        """
        Execute the MAKERS phase.

        Process:
        1. Find all maker spaces (spaces with maker=true in JSON)
        2. For each maker space:
           - If unoccupied (no agent), add 1 bonus spice
           - If occupied, skip (player gets spice when they placed agent)
        3. Return summary of bonus spice added

        Returns:
            Dict with:
                - success: bool
                - spaces_updated: List of spaces that received bonus spice
                - total_bonus_added: Total bonus spice added this round
        """
        if not self.game.board:
            return {
                "success": False,
                "error": "No board found"
            }

        spaces_updated = []
        total_bonus_added = 0

        # Get all board spaces
        all_spaces = self._get_all_maker_spaces()

        for space in all_spaces:
            # Check if space is unoccupied
            if space.occupied_by is None:
                # Add 1 bonus spice
                if not hasattr(space, 'bonus_spice'):
                    space.bonus_spice = 0

                space.bonus_spice += 1
                total_bonus_added += 1

                spaces_updated.append({
                    "space": space.name,
                    "bonus_spice": space.bonus_spice
                })

        return {
            "success": True,
            "spaces_updated": spaces_updated,
            "total_bonus_added": total_bonus_added
        }

    def _get_all_maker_spaces(self) -> List[BoardSpace]:
        """
        Get all boardspaces that are maker spaces.

        A maker space is identified by having the 'maker' attribute set to True.

        Returns:
            List of BoardSpace objects with maker=True
        """
        maker_spaces = []

        # In a full implementation, this would query the board for all spaces
        # For now, we'll check spaces that are tracked in the game board
        if hasattr(self.game.board, 'spaces'):
            for space in self.game.board.spaces:
                if hasattr(space, 'maker') and space.maker:
                    maker_spaces.append(space)

        return maker_spaces

    def claim_bonus_spice(self, space: BoardSpace, player_id: str) -> int:
        """
        Claim accumulated bonus spice from a maker space.

        Called when a player places an agent on a maker space.
        Returns the amount of bonus spice collected and resets it to 0.

        Args:
            space: The maker space being claimed
            player_id: ID of the player claiming the space

        Returns:
            Amount of bonus spice collected
        """
        if not hasattr(space, 'bonus_spice'):
            return 0

        bonus_collected = space.bonus_spice
        space.bonus_spice = 0  # Reset after collection

        return bonus_collected

    def get_maker_spaces_status(self) -> List[Dict[str, Any]]:
        """
        Get current status of all maker spaces.

        Useful for displaying to players.

        Returns:
            List of dicts with space info:
            [
                {
                    "name": "Deep Desert",
                    "occupied": False,
                    "bonus_spice": 3
                },
                ...
            ]
        """
        maker_spaces = self._get_all_maker_spaces()
        status = []

        for space in maker_spaces:
            bonus_spice = getattr(space, 'bonus_spice', 0)
            status.append({
                "name": space.name,
                "occupied": space.occupied_by is not None,
                "occupied_by": space.occupied_by if space.occupied_by else None,
                "bonus_spice": bonus_spice
            })

        return status
