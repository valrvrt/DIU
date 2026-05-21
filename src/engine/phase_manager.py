"""
PhaseManager - Orchestrates game phases and turn order.

Responsibilities:
- Phase progression (SETUP → BEGIN_ROUND → PLAYER_TURNS → COMBAT → MAKERS → RECALL)
- Turn order within phases
- Phase transition validation
- Phase-specific action validation
- Cleanup/initialization when phases change
"""

from typing import Dict, Any, Optional, Tuple, TYPE_CHECKING
from ..models.game import Game, GamePhase
from ..models.player import Player
from .game_state import GameState

if TYPE_CHECKING:
    from .combat_manager import CombatManager
    from .deck_manager import DeckManager
    from .makers_manager import MakersManager


class PhaseManager:
    """
    Orchestrates game phases and turn order.

    The PhaseManager acts as the central coordinator for game flow:
    - Validates if actions can be taken in current phase
    - Manages turn order within phases
    - Triggers automatic phase transitions
    - Cleans up phase-specific state when leaving a phase
    - Initializes state when entering a new phase
    """

    def __init__(
        self,
        game: Game,
        combat_manager: Optional['CombatManager'] = None,
        deck_manager: Optional['DeckManager'] = None,
        makers_manager: Optional['MakersManager'] = None
    ):
        self.game = game
        self.state = GameState(game)

        # Track who has acted in current phase
        self.players_who_acted: set[str] = set()

        # Track reveal status (in addition to player.has_revealed_this_round)
        self.players_who_revealed: set[str] = set()

        # Combat manager for resolving conflicts
        self.combat_manager = combat_manager

        # Deck manager for draw/discard operations
        self.deck_manager = deck_manager

        # Makers manager for bonus spice accumulation
        if makers_manager:
            self.makers_manager = makers_manager
        else:
            # Create one if not provided
            from .makers_manager import MakersManager
            self.makers_manager = MakersManager(game)

    # ==================== PHASE VALIDATION ====================

    def can_player_take_action(
        self,
        player_id: str,
        action_type: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if player can take action in current phase.

        Args:
            player_id: Player attempting action
            action_type: Type of action (place_agent, reveal, acquire_card, etc.)

        Returns:
            (can_act: bool, reason: Optional[str])
        """
        current_phase = self.game.current_phase
        player = self.state.get_player_by_id(player_id)

        if not player:
            return (False, "Player not found")

        if current_phase == GamePhase.PLAYER_TURNS:
            if action_type == "place_agent":
                return self._validate_agent_placement(player_id)
            elif action_type == "reveal":
                return self._validate_reveal(player_id)
            elif action_type == "acquire_card":
                return self._validate_acquisition(player_id)

        elif current_phase == GamePhase.COMBAT:
            if action_type in ["deploy_troops", "play_intrigue_combat"]:
                return (True, None)
            return (False, "Action not allowed during COMBAT phase")

        elif current_phase == GamePhase.MAKERS:
            # Spice accumulation phase - automatic
            return (False, "MAKERS phase is automatic")

        elif current_phase == GamePhase.RECALL:
            # Agent recall - automatic
            return (False, "RECALL phase is automatic")

        return (False, f"Action not allowed in {current_phase.value} phase")

    def _validate_agent_placement(self, player_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if player can place agent.

        Can place agent if:
        - Player has agents available
        - Player hasn't revealed yet this round
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return (False, "Player not found")

        if player.has_revealed_this_round:
            return (False, "Cannot place agent after revealing")

        if player.agents_available <= 0:
            return (False, "No agents available")

        return (True, None)

    def _validate_reveal(self, player_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if player can reveal.

        Can reveal if:
        - Player hasn't revealed yet this round
        - (No minimum agents requirement - player can pass early)
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return (False, "Player not found")

        if player.has_revealed_this_round:
            return (False, "Already revealed this round")

        return (True, None)

    def _validate_acquisition(self, player_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if player can acquire cards.

        Can acquire if:
        - Player has revealed
        - Player has persuasion available
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return (False, "Player not found")

        if not player.has_revealed_this_round:
            return (False, "Must reveal before acquiring cards")

        # Persuasion is only temporary (no permanent persuasion field)
        temp_persuasion = getattr(player, 'temp_persuasion', 0)
        if temp_persuasion <= 0:
            return (False, "No persuasion available")

        return (True, None)

    # ==================== PHASE TRANSITIONS ====================

    def should_advance_phase(self) -> bool:
        """
        Check if current phase is complete and ready to transition.

        Returns:
            True if should advance, False otherwise
        """
        current_phase = self.game.current_phase

        if current_phase == GamePhase.SETUP:
            # Setup complete when board is ready
            return self._is_setup_complete()

        elif current_phase == GamePhase.BEGIN_ROUND:
            # Begin round is instantaneous - just setup phase actions
            return True

        elif current_phase == GamePhase.PLAYER_TURNS:
            # Player turns complete when all players have revealed
            return self._are_player_turns_complete()

        elif current_phase == GamePhase.COMBAT:
            # Combat complete when all conflicts resolved
            return self._is_combat_complete()

        elif current_phase == GamePhase.MAKERS:
            # Makers complete after spice distribution (automatic)
            return True

        elif current_phase == GamePhase.RECALL:
            # Recall complete after agents returned (automatic)
            return True

        elif current_phase == GamePhase.GAME_OVER:
            return False  # Can't advance from game over

        return False

    def advance_phase(self) -> Dict[str, Any]:
        """
        Advance to the next phase.

        Process:
        1. Cleanup current phase
        2. Determine next phase
        3. Update game state
        4. Initialize next phase

        Returns:
            Dict with transition details
        """
        old_phase = self.game.current_phase

        # Step 1: Cleanup current phase
        self._cleanup_phase(old_phase)

        # Step 2: Determine next phase
        next_phase = self._get_next_phase(old_phase)

        # Step 3: Update game state
        self.game.current_phase = next_phase

        # Step 4: Initialize next phase
        self._initialize_phase(next_phase)

        return {
            "old_phase": old_phase.value,
            "new_phase": next_phase.value,
            "round": self.game.current_round
        }

    def _get_next_phase(self, current: GamePhase) -> GamePhase:
        """Determine the next phase in sequence."""
        phase_order = [
            GamePhase.SETUP,
            GamePhase.BEGIN_ROUND,
            GamePhase.PLAYER_TURNS,
            GamePhase.COMBAT,
            GamePhase.MAKERS,
            GamePhase.RECALL
        ]

        # Check for game over condition
        if self._is_game_over():
            return GamePhase.GAME_OVER

        # Find current phase in order
        try:
            current_idx = phase_order.index(current)
        except ValueError:
            # If GAME_OVER or unknown, stay
            return current

        # If at RECALL, loop back to BEGIN_ROUND
        if current == GamePhase.RECALL:
            return GamePhase.BEGIN_ROUND

        # Otherwise advance to next in sequence
        next_idx = (current_idx + 1) % len(phase_order)
        return phase_order[next_idx]

    # ==================== PHASE LIFECYCLE HOOKS ====================

    def _cleanup_phase(self, phase: GamePhase):
        """Cleanup actions when leaving a phase."""
        if phase == GamePhase.PLAYER_TURNS:
            # Discard played cards and clear temporary resources
            if self.deck_manager:
                for player in self.game.players:
                    # Discard played cards to discard pile
                    self.deck_manager.discard_played_cards(player.player_id)

            # Clear temporary resources (persuasion, swords)
            for player in self.game.players:
                player.temp_persuasion = 0
                player.temp_swords = 0
                player.has_revealed_this_round = False

            # Clear tracking sets
            self.players_who_acted.clear()
            self.players_who_revealed.clear()

        elif phase == GamePhase.COMBAT:
            # Remove sandworms (they die after combat)
            for player in self.game.players:
                player.sandworms_in_conflict = 0

        elif phase == GamePhase.RECALL:
            # Discard remaining hand and reset agents
            if self.deck_manager:
                for player in self.game.players:
                    # Discard entire hand at end of round
                    self.deck_manager.discard_hand(player.player_id)

            # Reset agents for next round
            for player in self.game.players:
                player.agents_available = player.total_available_agents

            # CRITICAL: Clear all board spaces for next round
            if self.game.board and self.game.board.spaces:
                for space in self.game.board.spaces:
                    space.occupied_by = None

    def _initialize_phase(self, phase: GamePhase):
        """Setup actions when entering a phase."""
        if phase == GamePhase.BEGIN_ROUND:
            # Increment round counter
            self.game.current_round += 1

            # Flip new conflict card (if available)
            if self.game.board and self.game.board.conflict_deck:
                new_conflict = self.game.board.conflict_deck.pop(0)
                self.game.board.current_conflict = new_conflict

            # Draw starting hand (5 cards) for each player
            # BUT: Skip on round 1, players already have starting hand from setup
            if self.deck_manager and self.game.current_round > 1:
                for player in self.game.players:
                    self.deck_manager.draw_starting_hand(player.player_id)

        elif phase == GamePhase.PLAYER_TURNS:
            # Reset turn order to first player
            self.game.current_player_index = self.game.first_player_index

        elif phase == GamePhase.COMBAT:
            # Combat resolution happens in game loop after displaying state
            # Don't auto-resolve here - let the display show troops first
            pass

        elif phase == GamePhase.MAKERS:
            # Setup spice accumulation (to be implemented)
            self._setup_makers_phase()

    def _setup_combat_phase(self):
        """
        Prepare for combat phase.

        If combat_manager is available, it will automatically resolve the conflict.
        """
        # If we have a combat manager, resolve the conflict
        if self.combat_manager:
            result = self.combat_manager.resolve_conflict()
            # Combat is automatically resolved
            # The conflict is now marked as resolved (current_conflict = None)
        # If no combat manager, combat must be resolved manually

    def _setup_makers_phase(self):
        """
        Execute the MAKERS phase.

        Automatically adds bonus spice to unoccupied maker spaces.
        This phase is automatic and requires no player input.
        """
        if self.makers_manager:
            result = self.makers_manager.execute_makers_phase()
            # Bonus spice has been added to all unoccupied maker spaces
            # The result contains details about which spaces were updated

    # ==================== TURN ORDER MANAGEMENT ====================

    def get_current_player(self) -> Optional[Player]:
        """Get the player whose turn it is."""
        if self.game.current_phase == GamePhase.PLAYER_TURNS:
            return self.game.players[self.game.current_player_index]
        return None

    def advance_turn(self):
        """Move to next player's turn within current phase."""
        if self.game.current_phase == GamePhase.PLAYER_TURNS:
            self.game.current_player_index = (
                (self.game.current_player_index + 1) % len(self.game.players)
            )

    def mark_player_action_complete(self, player_id: str, action_type: str):
        """Mark that a player has completed an action in current phase."""
        if action_type == "place_agent":
            self.players_who_acted.add(player_id)
        elif action_type == "reveal":
            self.players_who_revealed.add(player_id)
            player = self.state.get_player_by_id(player_id)
            if player:
                player.has_revealed_this_round = True

    # ==================== PHASE COMPLETION CHECKS ====================

    def _is_setup_complete(self) -> bool:
        """Check if setup phase is complete."""
        # Setup complete when:
        # - All players have starting cards
        # - Board is initialized
        # Simplified for now
        return all(len(player.hand.cards) > 0 for player in self.game.players)

    def _are_player_turns_complete(self) -> bool:
        """Check if player turns phase is complete."""
        # All players must have revealed
        all_revealed = all(
            player.has_revealed_this_round
            for player in self.game.players
        )

        if not all_revealed:
            return False

        # All acquisitions must be done
        # Simplified: assume done after reveal for now
        # In full implementation, track if players still want to acquire
        return True

    def _is_combat_complete(self) -> bool:
        """Check if combat phase is complete."""
        # Current conflict must be resolved
        # Simplified: check if current conflict has been handled
        if not self.game.board:
            return True

        # If there is a conflict to resolve, not complete
        return self.game.board.current_conflict is None

    def _is_game_over(self) -> bool:
        """
        Check if game should end.

        Game ends at END OF RECALL phase if:
        1. Any player has 10+ VP
        2. Round 10 has been completed
        3. Conflict deck is empty
        """
        # Only check at end of RECALL phase
        if self.game.current_phase != GamePhase.RECALL:
            return False

        # Check VP threshold
        for player in self.game.players:
            if player.victory_points >= 10:
                return True

        # Check round limit (game ends after round 10)
        if self.game.current_round >= 10:
            return True

        # Check if conflict deck is empty
        if len(self.game.board.conflict_deck) == 0:
            return True

        return False

    def determine_winner(self) -> Dict[str, Any]:
        """
        Determine winner(s) at game end.

        Tiebreaker: Spice (desc)

        Returns:
            {
                "winner": Player,
                "is_tie": bool,
                "tied_players": List[Player],
                "final_scores": List[{player, vp, spice}]
            }
        """
        # Sort by VP (desc), then spice (desc)
        sorted_players = sorted(
            self.game.players,
            key=lambda p: (p.victory_points, p.spice),
            reverse=True
        )

        winner = sorted_players[0]
        is_tie = False
        tied_players = [winner]

        # Check for tie (same VP and spice)
        for player in sorted_players[1:]:
            if player.victory_points == winner.victory_points and player.spice == winner.spice:
                is_tie = True
                tied_players.append(player)
            else:
                break

        return {
            "winner": winner,
            "is_tie": is_tie,
            "tied_players": tied_players if is_tie else [winner],
            "final_scores": [
                {
                    "player": p,
                    "vp": p.victory_points,
                    "spice": p.spice
                }
                for p in sorted_players
            ]
        }

    def _determine_first_player(self) -> int:
        """
        Determine first player for the round.

        First player = player with objective id=2 ("Desert Mouse 1-6p")
        If no one has it, fallback to game.first_player_index
        """
        # Check if any player has objective id=2
        for i, player in enumerate(self.game.players):
            if hasattr(player, 'objectives'):
                for objective in player.objectives:
                    if hasattr(objective, 'id') and objective.id == 2:
                        return i

        # Fallback to game.first_player_index
        return self.game.first_player_index
        return self.game.first_player_index
