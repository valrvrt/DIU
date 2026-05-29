"""
Victory Point Manager - Calculate and update victory points from various sources.

Responsibilities:
- Calculate VP from conflict/objective tag pairs
- Update player VP when winning conflicts
- Provide VP breakdown for display
"""

from typing import Dict, Any
from ...models.game import Game
from ..core.game_state import GameState


class VictoryPointManager:
    """Calculate and update victory points from various sources."""

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    def calculate_conflict_tag_pairs_vp(self, player_id: str) -> int:
        """
        Calculate VP from matching conflict/objective tags.

        Rules:
        - Each PAIR of same-tag cards = 1 VP
        - Sources: conflict_cards_won + objectives
        - Tags: "crysknife", "desert-mouse", "ornithopter"

        Examples:
        - 2 crysknife = 1 pair = 1 VP
        - 4 crysknife = 2 pairs = 2 VP
        - 1 crysknife + 1 desert-mouse = 0 pairs = 0 VP
        - 3 crysknife + 1 objective(crysknife) = 4 total = 2 pairs = 2 VP

        Returns:
            Total VP from tag pairs
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return 0

        # Count tags
        tag_counts = {}

        # Count from won conflicts
        if hasattr(player, 'conflict_cards_won'):
            for conflict in player.conflict_cards_won:
                tag = getattr(conflict, 'tag', None)
                if tag and tag != "":
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Count from objectives
        if hasattr(player, 'objectives'):
            for objective in player.objectives:
                tag = getattr(objective, 'tag', None)
                if tag and tag != "":
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Calculate pairs (floor division by 2)
        total_vp = sum(count // 2 for count in tag_counts.values())

        return total_vp

    def update_player_vp_from_tags(self, player_id: str) -> Dict[str, Any]:
        """
        Recalculate and update player VP from tag pairs.

        Called when:
        - Player wins a conflict
        - Player gains an objective (setup only)

        Returns:
            {
                "success": bool,
                "tag_vp": int,
                "vp_gained": int  # Difference from previous
            }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Calculate VP from tags
        tag_vp = self.calculate_conflict_tag_pairs_vp(player_id)

        # Store or update tag VP (track separately to avoid double-counting)
        old_tag_vp = getattr(player, 'tag_pair_vp', 0)
        vp_diff = tag_vp - old_tag_vp

        player.victory_points += vp_diff
        player.vp_sources["Matching conflict cards"] = (
            player.vp_sources.get("Matching conflict cards", 0) + vp_diff
        )
        player.tag_pair_vp = tag_vp  # Track for future updates

        return {
            "success": True,
            "tag_vp": tag_vp,
            "vp_gained": vp_diff
        }

    def get_vp_breakdown(self, player_id: str) -> Dict[str, int]:
        """
        Get breakdown of VP sources for display.

        Returns:
            {
                "total": int,
                "influence": int,  # From 2-influence bonuses
                "tag_pairs": int,  # From conflict/objective pairs
                "other": int       # From cards, contracts, etc.
            }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"total": 0, "influence": 0, "tag_pairs": 0, "other": 0}

        tag_vp = getattr(player, 'tag_pair_vp', 0)

        # Calculate influence VP (count tracks with 2+)
        influence_vp = 0
        for faction in ["fremen", "bene_gesserit", "spacing_guild", "emperor"]:
            track_attr = f"{faction}_influence"
            if getattr(player, track_attr, 0) >= 2:
                influence_vp += 1

        other_vp = player.victory_points - tag_vp - influence_vp

        return {
            "total": player.victory_points,
            "influence": influence_vp,
            "tag_pairs": tag_vp,
            "other": max(0, other_vp)
        }
