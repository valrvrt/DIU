"""
Victory Point Manager - Calculates and updates victory points from various sources.

Responsibilities:
- Calculate VP from conflict/objective tag pairs
- Update player VP when winning conflicts
- Provide VP breakdown for display
"""

from typing import Dict, Any
from ..models.game import Game
from .game_state import GameState


class VictoryPointManager:
    """
    Manages victory point calculations from tag pairs.

    Tag Pair Rules:
    - Each PAIR of same-tag cards = 1 VP
    - Sources: conflict_cards_won + objectives
    - Tags: "crysknife", "desert-mouse", "ornithopter"

    Examples:
    - 2 crysknife = 1 pair = 1 VP
    - 4 crysknife = 2 pairs = 2 VP
    - 1 crysknife + 1 desert-mouse = 0 pairs = 0 VP
    - 3 crysknife + 1 objective(crysknife) = 4 total = 2 pairs = 2 VP
    """

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    def calculate_conflict_tag_pairs_vp(self, player_id: str) -> int:
        """
        Calculate VP from matching conflict/objective tags.

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
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Count from objectives
        if hasattr(player, 'objectives'):
            for objective in player.objectives:
                tag = getattr(objective, 'tag', None)
                if tag:
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
                "old_vp": int,
                "new_vp": int,
                "tag_vp": int,
                "vp_gained": int
            }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"error": "Player not found"}

        # Calculate VP from tags
        tag_vp = self.calculate_conflict_tag_pairs_vp(player_id)

        # Store or update tag VP (need to track separately to avoid double-counting)
        old_tag_vp = getattr(player, 'tag_pair_vp', 0)
        vp_diff = tag_vp - old_tag_vp

        old_total_vp = player.victory_points
        player.victory_points += vp_diff
        player.tag_pair_vp = tag_vp  # Track for future updates

        return {
            "old_vp": old_total_vp,
            "new_vp": player.victory_points,
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

    def get_tag_count_breakdown(self, player_id: str) -> Dict[str, int]:
        """
        Get detailed breakdown of tag counts.

        Returns:
            Dict of tag -> count
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {}

        tag_counts = {}

        # Count from won conflicts
        if hasattr(player, 'conflict_cards_won'):
            for conflict in player.conflict_cards_won:
                tag = getattr(conflict, 'tag', None)
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Count from objectives
        if hasattr(player, 'objectives'):
            for objective in player.objectives:
                tag = getattr(objective, 'tag', None)
                if tag:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        return tag_counts
