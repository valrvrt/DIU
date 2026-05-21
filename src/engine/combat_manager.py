"""
Combat Manager - Manages combat resolution.

Responsibilities:
- Calculate combat strength for each player
- Determine rankings with tie-breaking rules
- Distribute rewards based on rankings (using EffectResolver)
- Cleanup after combat (troops to reserve, winner gets conflict card)
"""

from typing import Dict, Any, List, Tuple, TYPE_CHECKING
from ..models.game import Game
from ..models.player import Player
from ..models.card import ConflictCard
from .game_state import GameState

if TYPE_CHECKING:
    from .effect_resolver import EffectResolver


class CombatManager:
    """
    Manages combat resolution in the COMBAT phase.

    Combat Flow:
    1. [TODO] Intrigue round (players play combat intrigues)
    2. Calculate combat strength for each player
    3. Determine rankings (with tie-breaking)
    4. Distribute rewards
    5. Cleanup (troops to reserve, winner gets conflict card)
    """

    def __init__(self, game: Game, effect_resolver: 'EffectResolver' = None, victory_point_manager=None):
        self.game = game
        self.state = GameState(game)

        # Use provided EffectResolver or create one
        if effect_resolver:
            self.effect_resolver = effect_resolver
        else:
            from .effect_resolver import EffectResolver
            self.effect_resolver = EffectResolver(game)

        # Optional VictoryPointManager for tag pair VP updates
        self.victory_point_manager = victory_point_manager

    # ==================== COMBAT RESOLUTION ====================

    def resolve_conflict(self) -> Dict[str, Any]:
        """
        Resolve the current conflict.

        Process:
        1. Calculate combat strength for all players
        2. Determine rankings (handle ties)
        3. Distribute rewards based on rankings
        4. Award conflict card to winner(s)
        5. Cleanup (troops to reserve)
        6. Mark conflict as resolved

        Returns:
            Dict with combat results
        """
        if not self.game.board or not self.game.board.current_conflict:
            return {
                "success": False,
                "error": "No conflict to resolve"
            }

        conflict = self.game.board.current_conflict

        # Step 1: Calculate combat strength for all players
        player_strengths = self._calculate_all_combat_strengths()

        # Step 2: Determine rankings (handle ties)
        rankings = self._determine_rankings(player_strengths)
        
        # Step 3: Cleanup troops in case a winner re win his troop thanks to conflict reward (prevents winning troop and no troop in reserve availible)
        self._cleanup_troops()

        # Step 4: Distribute rewards
        reward_results = self._distribute_rewards(conflict, rankings)

        # Step 5: Award conflict card to winner(s)
        # IMPORTANT: If tied for 1st place, NO ONE gets the conflict card
        # Only a single 1st place winner gets the card
        winners = []
        if 1 in rankings:
            # Only award card if there's a single winner (not tied)
            if len(rankings[1]) == 1:
                winners = rankings[1]
                for player_id in winners:
                    player = self.state.get_player_by_id(player_id)
                    if player:
                        player.conflict_cards_won.append(conflict)

                        # Update tag pair VP if VictoryPointManager is available
                        if self.victory_point_manager:
                            self.victory_point_manager.update_player_vp_from_tags(player_id)
            # If tied for 1st (rankings[1] has multiple players), no one gets the card


        # Step 6: Mark conflict as resolved
        self.game.board.resolved_conflicts.append(conflict)
        self.game.board.current_conflict = None

        return {
            "success": True,
            "conflict": conflict.name,
            "player_strengths": player_strengths,
            "rankings": rankings,
            "rewards": reward_results,
            "winners": [self.state.get_player_by_id(pid).name for pid in winners]
        }

    # ==================== STRENGTH CALCULATION ====================

    def _calculate_all_combat_strengths(self) -> Dict[str, Dict[str, Any]]:
        """
        Calculate combat strength for all players.

        Returns:
            Dict mapping player_id to strength details:
            {
                "player1": {
                    "troops": 3,
                    "sandworms": 1,
                    "swords": 2,
                    "total_strength": 11,  # (3*2) + (1*3) + 2
                    "participating": True   # Has troops or sandworms
                }
            }
        """
        results = {}

        for player in self.game.players:
            troops = player.troops_in_conflict
            sandworms = player.sandworms_in_conflict
            swords = getattr(player, 'temp_swords', 0)

            # Calculate strength: troops*2 + sandworms*3 + swords
            total_strength = (troops * 2) + (sandworms * 3) + swords

            # Use is_participating_in_combat method for consistency
            participating = self.is_participating_in_combat(player.player_id)

            results[player.player_id] = {
                "troops": troops,
                "sandworms": sandworms,
                "swords": swords,
                "total_strength": total_strength,
                "participating": participating
            }

        return results

    def calculate_combat_strength(self, player_id: str) -> int:
        """
        Calculate combat strength for a specific player.

        Formula: (troops × 2) + (sandworms × 3) + temp_swords

        Args:
            player_id: Player to calculate strength for

        Returns:
            Total combat strength
        """
        # Use the main calculation method
        all_strengths = self._calculate_all_combat_strengths()
        return all_strengths.get(player_id, {}).get("total_strength", 0)

    def is_participating_in_combat(self, player_id: str) -> bool:
        """
        Check if player is participating in combat.

        Player participates only if they have troops or sandworms.
        Having only swords is NOT sufficient.

        Args:
            player_id: Player to check

        Returns:
            True if player has troops or sandworms in conflict
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return False

        return (player.troops_in_conflict > 0 or
                player.sandworms_in_conflict > 0)

    # ==================== RANKING DETERMINATION ====================

    def _determine_rankings(
        self,
        player_strengths: Dict[str, Dict[str, Any]]
    ) -> Dict[int, List[str]]:
        """
        Determine player rankings with tie-breaking rules.

        Tie Rules:
        - 2 first place → both get 2nd place reward, 3rd gets 3rd place reward
        - 2 second place → both get 3rd place reward, 3rd gets nothing
        - 2 third place → both get nothing
        - At 3 players: 3rd place reward never distributed

        Args:
            player_strengths: Dict of player strengths from _calculate_all_combat_strengths

        Returns:
            Dict mapping effective rank to list of player_ids:
            {
                1: ["player1"],           # Winner(s)
                2: ["player2", "player3"], # Second place (or tied first)
                3: ["player4"]             # Third place
            }
        """
        # Filter only participating players
        participants = [
            (player_id, data["total_strength"])
            for player_id, data in player_strengths.items()
            if data["participating"]
        ]

        if not participants:
            return {}  # No one participated

        # Sort by strength (descending)
        participants.sort(key=lambda x: x[1], reverse=True)

        # Group by strength (handle ties)
        strength_groups = []
        current_strength = None
        current_group = []

        for player_id, strength in participants:
            if strength != current_strength:
                if current_group:
                    strength_groups.append(current_group)
                current_group = [player_id]
                current_strength = strength
            else:
                current_group.append(player_id)

        if current_group:
            strength_groups.append(current_group)

        # Assign effective ranks based on tie rules
        rankings = {}

        if len(strength_groups) == 0:
            return {}

        # First group (highest strength)
        if len(strength_groups[0]) == 1:
            # Single winner
            rankings[1] = strength_groups[0]
        elif len(strength_groups[0]) == 2:
            # 2-way tie for first → both get 2nd place reward
            rankings[2] = strength_groups[0]
        else:
            # 3+ way tie for first → all get 3rd place reward
            rankings[3] = strength_groups[0]

        # Second group (if exists)
        if len(strength_groups) > 1:
            if 1 in rankings:
                # First place was not tied, second group gets 2nd place
                if len(strength_groups[1]) == 1:
                    rankings[2] = strength_groups[1]
                else:
                    # Multiple tied for second → get 3rd place reward
                    rankings[3] = strength_groups[1]
            elif 2 in rankings:
                # First place was 2-way tied (they got 2nd place reward)
                # Second group gets 3rd place reward
                if len(strength_groups[1]) == 1:
                    rankings[3] = strength_groups[1]
                # If multiple tied for second after tied first, they get nothing
                # (don't add to rankings)
            else:
                # First place was 3+ way tied (they got 3rd place reward already)
                # Second group gets nothing
                pass

        # Third group (if exists)
        if len(strength_groups) > 2:
            # Only if we have a clear 1st and 2nd
            if 1 in rankings and 2 in rankings:
                # Only assign 3rd place if not tied
                if len(strength_groups[2]) == 1:
                    rankings[3] = strength_groups[2]
                # If multiple tied for 3rd → they get nothing (don't add to rankings)

        return rankings

    # ==================== REWARD DISTRIBUTION ====================

    def _distribute_rewards(
        self,
        conflict: ConflictCard,
        rankings: Dict[int, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        Distribute conflict rewards based on rankings using EffectResolver.

        Rewards come from conflicts.JSON in the format:
        {
            "rewards": {
                "1": [...effects...],  # 1st place
                "2": [...effects...],  # 2nd place
                "3": [...effects...]   # 3rd place
            }
        }

        Args:
            conflict: Current conflict card with rewards
            rankings: Dict mapping rank to list of player_ids

        Returns:
            List of reward distributions
        """
        results = []

        for rank, player_ids in rankings.items():
            # Get rewards for this rank from JSON format
            # conflict.rewards is a dict like {"1": [...], "2": [...], "3": [...]}
            rank_key = str(rank)
            if hasattr(conflict, 'rewards') and rank_key in conflict.rewards:
                reward_effects = conflict.rewards[rank_key]

                # Distribute to all players at this rank
                for player_id in player_ids:
                    player = self.state.get_player_by_id(player_id)
                    if player:
                        # Use EffectResolver to apply rewards
                        result = self.effect_resolver.resolve_effects(
                            player_id,
                            reward_effects,
                            context={"phase": "combat", "conflict": conflict.name, "rank": rank}
                        )

                        results.append({
                            "player": player.name,
                            "rank": rank,
                            "rewards": result.get("effects_applied", []),
                            "success": result["success"],
                            "choices_required": result.get("choices_required", [])
                        })

        return results


    # ==================== CLEANUP ====================

    def _cleanup_troops(self):
        """
        Return all troops from conflict to reserve.

        Called after combat is resolved.
        """
        for player in self.game.players:
            # Move troops from conflict back to reserve
            player.troops_in_reserve += player.troops_in_conflict
            player.troops_in_conflict = 0

    # ==================== QUERIES ====================

    def get_current_combat_state(self) -> Dict[str, Any]:
        """
        Get current state of combat.

        Returns:
            Dict with current conflict and player strengths
        """
        if not self.game.board or not self.game.board.current_conflict:
            return {
                "has_conflict": False
            }

        conflict = self.game.board.current_conflict
        player_strengths = self._calculate_all_combat_strengths()

        return {
            "has_conflict": True,
            "conflict": conflict.name,
            "player_strengths": player_strengths,
            "participating_players": [
                self.state.get_player_by_id(pid).name
                for pid, data in player_strengths.items()
                if data["participating"]
            ]
        }
