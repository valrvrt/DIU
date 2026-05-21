"""
ActionGenerator - Determines what actions are available to a player.

This is where the core game logic lives:
- Which cards can be played?
- Which locations are valid for a card?
- Which intrigue cards can be played?
- How many troops can be deployed?
- What cards can be acquired?
"""

from typing import List, Dict, Tuple, Optional, TYPE_CHECKING
from ...models.game import Game
from ...models.player import Player
from ...models.card import ImperiumCard, IntrigueCard, IntriguePhase
from ...models.boardspace import BoardSpace
from ..core.game_state import GameState

if TYPE_CHECKING:
    from .phase_manager import PhaseManager


class ActionGenerator:
    """
    Generates all available actions for a player.

    This class determines what a player CAN do at any given moment,
    following the "available actions first" pattern.
    """

    def __init__(self, game: Game, phase_manager: Optional['PhaseManager'] = None, effect_resolver=None):
        self.game = game
        self.state = GameState(game)
        self.phase_manager = phase_manager
        self.effect_resolver = effect_resolver  # For evaluating checks  # Optional for backward compatibility

    # ==================== PLAYABLE CARDS ====================

    def get_playable_imperium_cards(self, player_id: str) -> List[ImperiumCard]:
        """
        Get all cards in hand that can be played right now.

        A card is playable if:
        1. Phase allows agent placement (if PhaseManager present)
        2. Player has agents available
        3. Card has at least ONE valid placement location

        Args:
            player_id: Player ID

        Returns:
            List of ImperiumCard objects that can be played
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        # Check phase before anything else (if PhaseManager exists)
        if self.phase_manager:
            can_act, reason = self.phase_manager.can_player_take_action(
                player_id,
                "place_agent"
            )
            if not can_act:
                return []  # No cards playable if phase doesn't allow

        # Can't play cards if no agents available
        if player.agents_available == 0:
            return []

        # Can't play cards if already revealed
        if player.has_revealed_this_round:
            return []

        playable = []

        for card in player.hand.cards:
            if self._has_any_valid_placement(player.player_id, card):
                playable.append(card)

        return playable

    def _has_any_valid_placement(self, player_id: str, card: ImperiumCard) -> bool:
        """
        Check if a card has at least ONE valid placement location.

        Returns True if any of:
        - Card has agent icon matching an available location
        - Card can be used with spy infiltration
        """
        # No icons = can only play with spy (special case)
        if len(self.get_valid_locations_for_card(player_id, card)) != 0:
            return True

        return False

    # ==================== VALID LOCATIONS FOR A CARD ====================

    def get_valid_locations_for_card(
        self,
        player_id: str,
        card: ImperiumCard
    ) -> List[Tuple[BoardSpace, str]]:
        """
        Get all valid locations where a specific card can be played.

        Args:
            player_id: Player ID
            card: The card to place

        Returns:
            List of (BoardSpace, placement_type) tuples where:
            - BoardSpace is the location
            - placement_type is either an agent icon ('fremen', 'emperor', etc.)
              or 'spy_infiltrate' if using spy network
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        valid_placements = []

        # Check normal placements (icon matching)
        for icon in card.agent_icons:
            locations = self.state.get_spaces_by_icon(icon)

            for location in locations:
                if self._can_place_at_location(player, card, location):
                    valid_placements.append((location, icon))

        # Check spy infiltration placements
        if self._has_spy_infiltration_option(player):
            spy_locations = self._get_spy_infiltratable_locations(player)

            for location in spy_locations:
                # For infiltration, we still need to afford the cost
                if self._can_afford_location(player, location):
                    valid_placements.append((location, "spy_infiltrate"))

        return valid_placements

    def _can_place_at_location(
        self,
        player: Player,
        card: ImperiumCard,
        location: BoardSpace
    ) -> bool:
        """
        Check if a specific card can be placed at a specific location.

        Checks:
        1. Location is not occupied
        2. Player can afford location cost
        3. Player meets influence requirements
        """
        # Location must be unoccupied (infiltration is separate)
        if location.occupied_by is not None:
            return False

        # Can afford cost?
        if not self._can_afford_location(player, location):
            return False

        # Meet influence requirement?
        if not self._meets_influence_requirement(player, location):
            return False

        return True

    # ==================== LOCATION VALIDATION HELPERS ====================

    def _can_afford_location(self, player: Player, location: BoardSpace) -> bool:
        """Check if player can pay the location's cost"""
        if not location.cost:
            return True

        # Handle both formats: dict (old) and list of effects (new)
        if isinstance(location.cost, dict):
            # Old format: {"water": 1, "solari": 2}
            for resource, amount in location.cost.items():
                if resource == "water" and player.water < amount:
                    return False
                elif resource == "solari" and player.solari < amount:
                    return False
                elif resource == "spice" and player.spice < amount:
                    return False
        elif isinstance(location.cost, list):
            # New format: [{"type": "resource", "resource": "water", "amount": 1}]
            for cost_effect in location.cost:
                if cost_effect.get("type") == "resource":
                    resource = cost_effect.get("resource")
                    amount = cost_effect.get("amount", 0)
                    if resource == "water" and player.water < amount:
                        return False
                    elif resource == "solari" and player.solari < amount:
                        return False
                    elif resource == "spice" and player.spice < amount:
                        return False

        return True

    def _meets_influence_requirement(self, player: Player, location: BoardSpace) -> bool:
        """Check if player meets the influence requirement for a location"""
        # Check new format (check array)
        if hasattr(location, 'check') and location.check and self.effect_resolver:
            check_result = self.effect_resolver.validate_location_access(player.player_id, location.check)
            if not check_result.get("success"):
                return False

        # Check old format (required_influence dict)
        if location.required_influence:
            for faction, required_amount in location.required_influence.items():
                current_influence = self.state.get_player_influence(player.player_id, faction)
                if current_influence < required_amount:
                    return False

        return True

    # ==================== SPY SYSTEM ====================

    def _has_spy_infiltration_option(self, player: Player) -> bool:
        """Check if player has any placed spies (enabling infiltration)"""
        return len(player.spies_placed) > 0

    def _get_spy_infiltratable_locations(self, player: Player) -> List[BoardSpace]:
        """
        Get locations that can be infiltrated via spy network.

        Returns locations that are:
        1. Connected to a spy post where player has a spy
        2. Currently occupied by another player (that's what infiltration is for!)
        """
        accessible = self.state.get_spy_accessible_locations(player.player_id)

        # Filter to only occupied locations (infiltration target)
        infiltratable = []
        for location in accessible:
            if location.occupied_by is not None:  # Must be occupied to infiltrate
                infiltratable.append(location)

        return infiltratable

    def can_gather_information_at_location(
        self,
        player_id: str,
        location_id: str
    ) -> bool:
        """
        Check if player can recall a spy from a post connected to this location
        to draw a card (Gather Information ability).

        Returns True if player has a spy at a post connected to this location.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return False

        # Find all posts connected to this location
        for post in self.game.board.observation_posts:
            if location_id in post.connected_locations:
                # Does player have a spy at this post?
                if post.id in player.spies_placed:
                    return True

        return False

    # ==================== INTRIGUE CARDS ====================

    def get_playable_intrigue_cards(
        self,
        player_id: str,
        current_phase: IntriguePhase
    ) -> List[IntrigueCard]:
        """
        Get intrigue cards that can be played right now.

        Args:
            player_id: Player ID
            current_phase: PLOT (during player turns), COMBAT, or END_GAME

        Returns:
            List of playable IntrigueCard objects
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        playable = []

        for intrigue_card in player.intrigue_cards:
            # Check if card can be played in this phase
            if current_phase in intrigue_card.phases:
                # Check if player meets conditions (if any)
                if self._meets_intrigue_conditions(player, intrigue_card):
                    # Check if player can afford cost (if any)
                    if self._can_afford_intrigue(player, intrigue_card):
                        playable.append(intrigue_card)

        return playable

    def _meets_intrigue_conditions(self, player: Player, intrigue: IntrigueCard) -> bool:
        """Check if player meets the conditions to play an intrigue card"""
        if not intrigue.conditional_gain:
            return True

        # Example conditions from test data:
        # {"min_alliances": 2} - Need at least 2 alliances
        if "min_alliances" in intrigue.conditional_gain:
            required = intrigue.conditional_gain["min_alliances"]
            alliances = 0
            if player.fremen_alliance:
                alliances += 1
            if player.emperor_alliance:
                alliances += 1
            if player.spacing_guild_alliance:
                alliances += 1
            if player.bene_gesserit_alliance:
                alliances += 1

            if alliances < required:
                return False

        # Add more condition checks as needed
        # {"min_troops_in_conflict": 3}
        if "min_troops_in_conflict" in intrigue.conditional_gain:
            required = intrigue.conditional_gain["min_troops_in_conflict"]
            if player.troops_conflict < required:
                return False

        return True

    def _can_afford_intrigue(self, player: Player, intrigue: IntrigueCard) -> bool:
        """Check if player can pay the cost of an intrigue card"""
        if not intrigue.cost:
            return True

        # Same as location cost check
        for resource, amount in intrigue.cost.items():
            if resource == "water" and player.water < amount:
                return False
            elif resource == "solari" and player.solari < amount:
                return False
            elif resource == "spice" and player.spice < amount:
                return False

        return True

    # ==================== TROOP DEPLOYMENT ====================

    def get_troop_deployment_options(self, player_id: str) -> Dict[str, int]:
        """
        Get troop deployment options for current turn.

        Called when player places agent at a combat location.

        Returns dict with:
        - max_from_garrison: How many from garrison (0-2)
        - total_available: Total troops that can be deployed
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"max_from_garrison": 0, "total_available": 0}

        # Can deploy up to 2 troops from garrison (rule)
        max_from_garrison = min(2, player.troops_in_garrison)

        return {
            "max_from_garrison": max_from_garrison,
            "total_available": player.troops_in_garrison
        }

    def can_deploy_sandworm(self, player_id: str) -> bool:
        """
        Check if player can deploy a sandworm.

        Requirements:
        1. Player has Maker Hooks token
        2. Current conflict is NOT at a shielded location
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return False

        # Must have Maker Hooks
        if not player.has_maker_hooks:
            return False

        # Check if current conflict location is shielded
        conflict = self.state.get_current_conflict()
        if conflict and conflict.location:
            # Location conflicts can be shielded
            if conflict.wall:  # 'wall' means shield protection
                return False

        return True

    # ==================== CARD ACQUISITION ====================

    def get_acquisition_options(self, player_id: str) -> Dict:
        """
        Get card acquisition options during reveal turn.

        Uses player's temp_persuasion (calculated during reveal) to determine
        what cards are affordable.

        Returns dict with:
        - total_persuasion: Total persuasion available
        - imperium_row: List of all cards in Imperium row
        - affordable_from_row: Cards from row player can afford
        - reserve_prepare: Prepare the Way cards available
        - reserve_spice: Spice Must Flow cards available
        - can_afford_prepare: Can afford Prepare the Way (cost 2)
        - can_afford_spice: Can afford Spice Must Flow (cost 8)
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {}

        # Use temp_persuasion (already calculated in reveal)
        persuasion = getattr(player, 'temp_persuasion', 0)

        # Get affordable cards from Imperium row
        affordable_from_row = []
        for card in self.game.board.imperium_row:
            if card.cost <= persuasion:
                affordable_from_row.append(card)

        # Check reserve piles
        prepare_cost = 2  # Standard cost for Prepare the Way
        spice_cost = 8    # Standard cost for Spice Must Flow

        return {
            "total_persuasion": persuasion,
            "imperium_row": self.game.board.imperium_row,
            "affordable_from_row": affordable_from_row,
            "reserve_prepare": self.game.board.reserve_prepare_the_way,
            "reserve_spice": self.game.board.reserve_spice_must_flow,
            "can_afford_prepare": persuasion >= prepare_cost and len(self.game.board.reserve_prepare_the_way) > 0,
            "can_afford_spice": persuasion >= spice_cost and len(self.game.board.reserve_spice_must_flow) > 0
        }

    def _calculate_persuasion(self, player: Player) -> int:
        """
        Calculate total persuasion for a player during their reveal turn.

        Persuasion comes from:
        1. Reveal effects of cards in hand (revealed this turn)
        2. Agent effects of cards played earlier (if they grant persuasion)

        Note: In the actual game, persuasion is calculated AFTER revealing,
        so we'd look at the revealed cards specifically.
        For now, this is a simplified version.
        """
        persuasion = 0

        # In real implementation, you'd track which cards were revealed
        # For now, we'll just count reveal_effects from hand
        for card in player.hand.cards:
            persuasion += card.reveal_effects.get("persuasion", 0)

        return persuasion

    # ==================== OBSERVATION POSTS ====================

    def get_available_observation_posts(self, player_id: str) -> List:
        """
        Get observation posts where player can place a spy.

        Returns list of posts that are:
        1. Not currently occupied by this player
        2. Not occupied by another player (only 1 spy per post)
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        # No spies available
        if player.spies_available == 0:
            return []

        available = []

        for post in self.game.board.observation_posts:
            # Check if post is already occupied
            occupied = False
            for p in self.game.players:
                if post.id in p.spies_placed:
                    occupied = True
                    break

            if not occupied:
                available.append(post)

        return available

    # ==================== SPECIAL ACTIONS ====================

    def can_take_reveal_turn(self, player_id: str) -> bool:
        """
        Check if player can take a reveal turn.

        Player can reveal if they haven't already revealed this round.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return False

        return not player.has_revealed_this_round

    def can_take_agent_turn(self, player_id: str) -> bool:
        """
        Check if player can take an agent turn.

        Requirements:
        1. Has agents available
        2. Hasn't revealed yet
        3. Has at least one playable card
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return False

        # Already revealed = no more agent turns
        if player.has_revealed_this_round:
            return False

        # No agents = can't place
        if player.agents_available == 0:
            return False

        # Must have at least one playable card
        playable = self.get_playable_imperium_cards(player_id)
        return len(playable) > 0

    def get_gather_information_options(self, player_id: str) -> List[str]:
        """
        Get observation posts where player can recall spy.

        Returns:
            List of observation post IDs where player has spies
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        return list(player.spies_placed)
