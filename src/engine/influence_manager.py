"""
Influence Manager - Manages influence tracks, alliances, and influence-based VP.

Responsibilities:
- Add influence to faction tracks
- Award +1 VP when reaching 2 influence
- Manage alliances (4+ influence AND more than all other players)
- Track alliance status changes
"""

from typing import Dict, Any, List, Tuple
from ..models.game import Game
from .game_state import GameState


class InfluenceManager:
    """
    Manages influence tracks and alliances.

    VP Rules:
    - 2 influence on a track = +1 VP (one-time bonus)

    Alliance Rules:
    - 4+ influence AND more than all other players = Alliance
    - Only one player can have alliance per faction
    - Alliances provide ongoing bonuses (faction-specific)
    """

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    def add_influence(self, player_id: str, faction: str, amount: int) -> Dict[str, Any]:
        """
        Add influence to a faction track and award VP bonuses.

        Args:
            player_id: Player gaining influence
            faction: "fremen", "bene_gesserit", "spacing_guild", "emperor"
            amount: Amount of influence to add

        Returns:
            {
                "success": bool,
                "faction": str,
                "old_influence": int,
                "new_influence": int,
                "vp_gained": int,  # From reaching 2 threshold
                "alliance_gained": bool,
                "alliance_lost_by": List[str]  # Other players who lost alliance
            }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Validate faction
        valid_factions = ["fremen", "bene_gesserit", "spacing_guild", "emperor"]
        if faction not in valid_factions:
            return {
                "success": False,
                "error": f"Invalid faction: {faction}. Must be one of {valid_factions}"
            }

        track_attr = f"{faction}_influence"
        old_influence = getattr(player, track_attr, 0)
        new_influence = old_influence + amount

        setattr(player, track_attr, new_influence)

        # Check for 2-influence VP bonus
        vp_gained = 0
        if old_influence < 2 <= new_influence:
            player.victory_points += 1
            vp_gained = 1

        # Check for alliance (4+ influence AND more than others)
        alliance_gained = False
        alliance_lost_by = []

        if new_influence >= 4:
            alliance_gained, alliance_lost_by = self._check_alliance(player_id, faction)

        return {
            "success": True,
            "faction": faction,
            "old_influence": old_influence,
            "new_influence": new_influence,
            "vp_gained": vp_gained,
            "alliance_gained": alliance_gained,
            "alliance_lost_by": alliance_lost_by
        }

    def _check_alliance(self, player_id: str, faction: str) -> Tuple[bool, List[str]]:
        """
        Check if player has alliance (4+ influence AND more than all others).

        Returns:
            (alliance_gained: bool, players_who_lost: List[str])
        """
        player = self.state.get_player_by_id(player_id)
        track_attr = f"{faction}_influence"
        alliance_attr = f"{faction}_alliance"

        player_influence = getattr(player, track_attr, 0)

        # Check if player has more influence than all others
        has_alliance = player_influence >= 4
        for other in self.game.players:
            if other.player_id == player_id:
                continue
            other_influence = getattr(other, track_attr, 0)
            if other_influence >= player_influence:
                has_alliance = False
                break

        # Update alliance status
        old_alliance = getattr(player, alliance_attr, False)
        alliance_gained = has_alliance and not old_alliance

        setattr(player, alliance_attr, has_alliance)

        # Check if other players lost alliance
        players_who_lost = []
        if has_alliance:
            for other in self.game.players:
                if other.player_id == player_id:
                    continue
                other_alliance_attr = f"{faction}_alliance"
                if getattr(other, other_alliance_attr, False):
                    setattr(other, other_alliance_attr, False)
                    players_who_lost.append(other.player_id)

        return alliance_gained, players_who_lost

    def get_alliance_bonus(self, player_id: str, faction: str) -> Dict[str, Any]:
        """
        Get the ongoing bonus for having an alliance.

        Returns:
            {
                "has_alliance": bool,
                "bonus": Dict  # Faction-specific bonus
            }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"has_alliance": False, "bonus": {}}

        alliance_attr = f"{faction}_alliance"
        has_alliance = getattr(player, alliance_attr, False)

        # Faction-specific bonuses (can be loaded from JSON later)
        bonuses = {
            "fremen": {"troop_strength": 1},  # +1 troop strength in combat
            "bene_gesserit": {"draw_intrigue": 1},  # Draw +1 intrigue
            "spacing_guild": {"solari_per_turn": 1},  # +1 solari each turn
            "emperor": {"influence_cost": -1}  # -1 cost for influence effects
        }

        return {
            "has_alliance": has_alliance,
            "bonus": bonuses.get(faction, {}) if has_alliance else {}
        }

    def get_all_alliances(self, player_id: str) -> List[str]:
        """
        Get all factions where player has alliance.

        Returns:
            List of faction names
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        alliances = []
        for faction in ["fremen", "bene_gesserit", "spacing_guild", "emperor"]:
            alliance_attr = f"{faction}_alliance"
            if getattr(player, alliance_attr, False):
                alliances.append(faction)

        return alliances
