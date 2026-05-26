"""
Action Executor - Executes validated player actions.

This class takes validated actions (from ActionGenerator) and executes them,
modifying the game state and triggering effects through the EffectResolver.

Flow:
1. ActionGenerator tells us what actions are valid
2. Player chooses an action
3. ActionExecutor executes it (this file)
4. EffectResolver interprets card effects

IMPORTANT: JSON Data Format Requirements
========================================
All card and location effects MUST be in standard list format:

✅ CORRECT FORMAT:
    "agent_effects": [
        {"type": "resource", "resource": "persuasion", "amount": 2},
        {"type": "draw", "deck": "deck", "amount": 1}
    ]

❌ INCORRECT - Dict format not supported:
    "agent_effects": {"persuasion": 2, "draw": 1}

❌ INCORRECT - Nested "base" not supported:
    "agent_effects": {"base": {"persuasion": 2}}

Effect Types Reference:
- resource: {"type": "resource", "resource": "solari|spice|water|persuasion|swords|troops", "amount": N}
- draw: {"type": "draw", "deck": "deck|intrigue", "amount": N}
- influence: {"type": "influence", "target": "fremen|bene_gesserit|spacing_guild|emperor", "amount": N}
- trash: {"type": "trash", "deck": ["hand", "played"], "amount": N}
- steal: {"type": "steal", "deck": "intrigue", "amount": N}
- recall: {"type": "recall", "unit": "agent|spy", "amount": N}
- accept: {"type": "accept", "amount": N}
- play: {"type": "play", "unit": "spy", "amount": N}
- choice: {"type": "choice", "options": [...]}
- conditional: {"type": "conditional", "costs": [...], "rewards": [...]}

The JSON database MUST conform to this format. The code will NOT attempt
to normalize or convert different formats.
"""

from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
from ...models.game import Game
from ...models.player import Player
from ...models.card import ImperiumCard, IntrigueCard
from ...models.boardspace import BoardSpace
from ..effects.effect_resolver import EffectResolver
from ..core.game_state import GameState
from ..managers.contract_manager import ContractManager

if TYPE_CHECKING:
    from .phase_manager import PhaseManager
    from .deck_manager import DeckManager


# ==================== ACTION DATA CLASSES ====================

@dataclass
class PlaceAgentAction:
    """
    Action: Place an agent at a board location with a card.

    This is the core action of the agent turn phase.
    """
    player_id: str
    card: ImperiumCard
    location: BoardSpace
    placement_type: str  # Icon name or "spy_infiltrate"
    troops_to_deploy: int = 0  # For combat locations


@dataclass
class RevealAction:
    """
    Action: Reveal hand and resolve reveal effects.

    This ends the player's turn and triggers all reveal effects.
    """
    player_id: str


@dataclass
class AcquireCardAction:
    """
    Action: Acquire a card from the Imperium row or reserve.

    Happens during reveal turn after calculating persuasion.
    """
    player_id: str
    card: ImperiumCard
    source: str  # "row", "prepare", "spice"


@dataclass
class DeployTroopsAction:
    """
    Action: Deploy troops to conflict during combat phase.

    Happens at combat locations when agent is placed.
    """
    player_id: str
    troops_from_garrison: int
    deploy_sandworm: bool = False


@dataclass
class DeploySandwormAction:
    """
    Action: Deploy sandworm(s) to conflict (requires Maker Hooks).

    Sandworms:
    - Go directly to conflict (not through garrison)
    - Cannot be deployed if shield wall is active at critical location
    - Die at end of conflict
    - Some cards allow bypassing Maker Hooks requirement
    """
    player_id: str
    worm_count: int = 1  # Number of worms to deploy
    bypass_maker_hooks: bool = False  # Some cards allow bypassing this requirement


@dataclass
class PlayIntrigueAction:
    """
    Action: Play an intrigue card.

    Can happen during PLOT (player turns), COMBAT, or END_GAME phases.
    """
    player_id: str
    intrigue_card: IntrigueCard


@dataclass
class ResolveChoiceAction:
    """
    Action: Resolve a choice from an effect (choice or conditional).

    This happens when an effect requires player input (e.g., "choose spice or worms").
    """
    player_id: str
    choice_id: str  # Unique identifier for the choice
    selected_option_id: str  # ID of the option chosen by player


@dataclass
class GatherInformationAction:
    """Action: Recall spy from observation post to draw intrigue card."""
    player_id: str
    observation_post_id: str  # Post where spy is stationed


# ==================== ACTION EXECUTOR ====================

class ActionExecutor:
    """
    Executes player actions and modifies game state.

    Works in conjunction with:
    - ActionGenerator (determines what's valid)
    - EffectResolver (executes card effects)
    - GameState (queries current state)
    - ContractManager (manages contracts)
    - PhaseManager (validates phase-appropriate actions)
    """

    def __init__(
        self,
        game: Game,
        phase_manager: Optional['PhaseManager'] = None,
        deck_manager: Optional['DeckManager'] = None,
        effect_resolver: Optional['EffectResolver'] = None
    ):
        self.game = game
        self.state = GameState(game)
        # Use provided effect_resolver if available, otherwise create new one
        self.effect_resolver = effect_resolver if effect_resolver else EffectResolver(game)
        self.contract_manager = ContractManager(game)
        self.phase_manager = phase_manager  # Optional for backward compatibility
        self.deck_manager = deck_manager  # Optional deck manager

        # Track pending choices (for multi-step resolution)
        self.pending_choices: Dict[str, Dict[str, Any]] = {}

    # ==================== AGENT TURN ACTIONS ====================

    def execute_place_agent(self, action: PlaceAgentAction) -> Dict[str, Any]:
        """
        Execute a "place agent" action.

        This is the most complex action - it involves:
        1. Validate phase (if PhaseManager present)
        2. Validate action is still legal (defensive check)
        3. Remove agent from player's pool
        4. Occupy the board location (or infiltrate if spy)
        5. Pay location cost (using EffectResolver)
        6. Move card from hand to played area (NOT discarded yet)
        7. Resolve card's AGENT effects (if card has them)
        8. Resolve location effects (using EffectResolver)
        9. Deploy troops if combat location (troops_to_deploy from player's choice)
        10. Check for contract completion (location-based)
        11. Notify PhaseManager (if present)
        12. Return execution log

        Args:
            action: PlaceAgentAction with all details

        Returns:
            Dict with execution results and any pending player choices
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate phase (if PhaseManager exists)
        if self.phase_manager:
            can_act, reason = self.phase_manager.can_player_take_action(
                action.player_id,
                "place_agent"
            )
            if not can_act:
                return {
                    "success": False,
                    "error": f"Cannot place agent: {reason}"
                }

        # Step 2: Defensive validation
        if player.agents_available <= 0:
            return {"success": False, "error": "No agents available"}

        if action.card not in player.hand.cards:
            return {"success": False, "error": "Card not in hand"}

        # Step 3: Remove agent from pool
        player.agents_available -= 1
        player.agents_placed.append(action.location.id)

        # Step 4: Check location requirements (influence, council seat, etc.)
        if hasattr(action.location, 'check') and action.location.check:
            check_result = self.effect_resolver.validate_location_access(action.player_id, action.location.check)
            if not check_result["success"]:
                # Restore agent since we're failing
                player.agents_available += 1
                player.agents_placed.remove(action.location.id)
                return {
                    "success": False,
                    "error": f"Cannot access {action.location.name}: {check_result.get('error', 'Requirements not met')}"
                }

        # Step 5: Occupy location or infiltrate
        if action.placement_type == "spy_infiltrate":
            # Spy infiltration: occupy WITH the existing agent
            # Both players get location effects
            if action.location.occupied_by is None:
                # Can't infiltrate an unoccupied location (should use normal placement)
                player.agents_available += 1
                player.agents_placed.remove(action.location.id)
                return {"success": False, "error": "Cannot infiltrate unoccupied location"}

            # Mark location as infiltrated
            action.location.infiltrated_by = action.player_id

            # Use spy instead of agent
            if player.spies_available <= 0:
                player.agents_available += 1
                player.agents_placed.remove(action.location.id)
                return {"success": False, "error": "No spies available"}

            player.spies_available -= 1
            player.spies_placed.append(action.location.id)
        else:
            # Normal placement
            if action.location.occupied_by is not None:
                return {"success": False, "error": "Location already occupied"}
            action.location.occupied_by = action.player_id

        # Step 6: Pay location cost
        cost_result = None
        if action.location.cost:
            # Validate player can afford cost
            validation = self._validate_cost(player, action.location.cost)
            if not validation["success"]:
                # Restore agent since we're failing
                player.agents_available += 1
                player.agents_placed.remove(action.location.id)
                return {
                    "success": False,
                    "error": f"Cannot afford {action.location.name}: {validation['error']}"
                }

            # Deduct cost
            cost_result = self._pay_cost(player, action.location.cost)
            if not cost_result["success"]:
                # Restore agent since we're failing
                player.agents_available += 1
                player.agents_placed.remove(action.location.id)
                return cost_result

        # Step 7: Move card from hand to played area
        # IMPORTANT: Card goes to played_cards_this_turn, NOT discarded immediately
        # It will be discarded at end of turn (RECALL phase)
        player.hand.cards.remove(action.card)
        player.played_cards_this_turn.append(action.card)

        # Step 8-9: Collect ALL effects from card and location
        # In real DUNE Imperium, after placing agent, player resolves ALL effects
        # (card agent effects + location effects) in their chosen order
        all_effects = []
        effect_sources = []  # Track which effect came from where (for logging)

        # Collect card agent effects
        if hasattr(action.card, 'agent_effects') and action.card.agent_effects:
            if not isinstance(action.card.agent_effects, list):
                return {
                    "success": False,
                    "error": f"Card {action.card.name} has invalid agent_effects format (expected list)"
                }
            for effect in action.card.agent_effects:
                all_effects.append(effect)
                effect_sources.append(f"card:{action.card.name}")

        # Collect location effects (for normal placement)
        location_results_for_original = None
        if action.placement_type != "spy_infiltrate":
            # Check for new format (reward list)
            if hasattr(action.location, 'reward') and action.location.reward:
                for effect in action.location.reward:
                    all_effects.append(effect)
                    effect_sources.append(f"location:{action.location.name}")
            # Check for old format (effects list)
            elif hasattr(action.location, 'effects') and action.location.effects:
                if not isinstance(action.location.effects, list):
                    return {
                        "success": False,
                        "error": f"Location {action.location.name} has invalid effects format (expected list)"
                    }
                for effect in action.location.effects:
                    all_effects.append(effect)
                    effect_sources.append(f"location:{action.location.name}")
        else:
            # Spy infiltration: Both players get location effects separately
            # Get location effects (prioritize new format)
            location_effects = []
            if hasattr(action.location, 'reward') and action.location.reward:
                location_effects = action.location.reward
            elif hasattr(action.location, 'effects') and action.location.effects:
                if not isinstance(action.location.effects, list):
                    return {
                        "success": False,
                        "error": f"Location {action.location.name} has invalid effects format (expected list)"
                    }
                location_effects = action.location.effects

            if location_effects:
                # Original occupant gets effects (with their preferred order)
                original_occupant_id = action.location.occupied_by
                original_ordered_effects = self._order_effects_for_resolution(
                    original_occupant_id,
                    location_effects,
                    context={"phase": "agent", "location": action.location.name, "infiltrated": True}
                )
                location_results_for_original = self.effect_resolver.resolve_effects(
                    original_occupant_id,
                    original_ordered_effects,
                    context={"phase": "agent", "location": action.location.name, "infiltrated": True}
                )
                # Note: Don't fail if original occupant's effects fail

                # Infiltrating spy gets location effects added to their pool
                for effect in location_effects:
                    all_effects.append(effect)
                    effect_sources.append(f"location:{action.location.name}")

        # Step 10: Allow player to choose resolution order for ALL effects
        # This matches real DUNE Imperium where player chooses effect order
        ordered_effects = self._order_effects_for_resolution(
            action.player_id,
            all_effects,
            context={
                "phase": "agent",
                "card": action.card.name,
                "location": action.location.name,
                "sources": effect_sources
            }
        )

        # Step 11: Resolve all effects with conditional reward trigger monitoring
        combined_results = self.effect_resolver.resolve_effects(
            action.player_id,
            ordered_effects,
            context={
                "phase": "agent",
                "card": action.card.name,
                "location": action.location.name,
                "monitor_triggers": True  # Enable trigger monitoring
            }
        )

        if not combined_results["success"]:
            return combined_results

        # Split results for backward compatibility with return format
        card_agent_results = {
            "success": True,
            "effects_applied": [e for e in combined_results.get("effects_applied", [])
                               if any(src.startswith("card:") for src in effect_sources)],
            "choices_required": combined_results.get("choices_required", [])
        }
        location_results = {
            "success": True,
            "effects_applied": [e for e in combined_results.get("effects_applied", [])
                               if any(src.startswith("location:") for src in effect_sources)],
            "choices_required": []
        }

        # Step 12: Deploy troops if combat location (optional - can be 0)
        # NOTE: UI typically passes 0 here and calls deploy_troops_to_conflict() separately
        # after showing rewards, to ensure correct order (rewards first, then deployment prompt)
        troops_deployed_count = 0
        if action.location.is_combat_space and action.troops_to_deploy > 0:
            if player.troops_in_garrison >= action.troops_to_deploy:
                player.troops_in_garrison -= action.troops_to_deploy
                player.troops_in_conflict += action.troops_to_deploy
                troops_deployed_count = action.troops_to_deploy
            else:
                return {
                    "success": False,
                    "error": f"Not enough troops in garrison (have {player.troops_in_garrison}, need {action.troops_to_deploy})"
                }

        # Step 13: Check for contract completion (location-based)
        contract_results = self.contract_manager.check_location_contracts(
            action.player_id,
            action.location.id
        )

        # Step 14: Notify PhaseManager (if present)
        if self.phase_manager:
            self.phase_manager.mark_player_action_complete(
                action.player_id,
                "place_agent"
            )

        # Step 15: Return execution log
        result = {
            "success": True,
            "action_type": "place_agent",
            "player_id": action.player_id,
            "card": action.card.name,
            "location": action.location.name,
            "placement_type": action.placement_type,
            "troops_deployed": troops_deployed_count,
            "card_agent_effects": card_agent_results,
            "location_effects": location_results,
            "contracts_completed": contract_results.get("completed_contracts", []),
            "agents_remaining": player.agents_available,
            "choices_required": (card_agent_results.get("choices_required", []) if card_agent_results else []) +
                               (location_results.get("choices_required", []) if location_results else [])
        }

        # Include spy infiltration details if applicable
        if action.placement_type == "spy_infiltrate":
            result["spy_infiltration"] = True
            result["original_occupant_effects"] = location_results_for_original

        return result

    def deploy_troops_to_conflict(self, player_id: str, num_troops: int) -> Dict[str, Any]:
        """
        Deploy troops from garrison to conflict.
        Called AFTER location rewards are given.

        Args:
            player_id: Player deploying troops
            num_troops: Number of troops to deploy

        Returns:
            Result dict with success/error
        """
        player = self.state.get_player_by_id(player_id)

        if num_troops <= 0:
            return {"success": True, "troops_deployed": 0}

        if player.troops_in_garrison >= num_troops:
            player.troops_in_garrison -= num_troops
            player.troops_in_conflict += num_troops
            return {
                "success": True,
                "troops_deployed": num_troops,
                "garrison_remaining": player.troops_in_garrison,
                "conflict_total": player.troops_in_conflict
            }
        else:
            return {
                "success": False,
                "error": f"Not enough troops in garrison (have {player.troops_in_garrison}, need {num_troops})"
            }

    # ==================== REVEAL TURN ACTIONS ====================

    def execute_reveal(self, action: RevealAction) -> Dict[str, Any]:
        """
        Execute a "reveal" action.

        Process:
        1. Validate phase (if PhaseManager present)
        2. Validate player hasn't already revealed
        3. Mark player as having revealed
        4. Resolve reveal effects ONLY for cards still in hand (not played cards)
        5. Move hand cards to played_cards_this_turn
        6. Calculate total persuasion and swords from effects
        7. Notify PhaseManager (if present)
        8. Return results with acquisition options

        IMPORTANT: Only cards still in hand get reveal effects!
        Cards already played (in played_cards_this_turn) had their agent effects
        triggered during placement and do NOT get reveal effects.

        Args:
            action: RevealAction

        Returns:
            Dict with persuasion total and reveal effects results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate phase (if PhaseManager exists)
        if self.phase_manager:
            can_act, reason = self.phase_manager.can_player_take_action(
                action.player_id,
                "reveal"
            )
            if not can_act:
                return {
                    "success": False,
                    "error": f"Cannot reveal: {reason}"
                }

        # Step 2: Validate
        if player.has_revealed_this_round:
            return {"success": False, "error": "Already revealed this round"}

        # Step 3: Mark as revealed
        player.has_revealed_this_round = True

        # Step 4: Resolve reveal effects ONLY for unplayed cards (still in hand)
        # IMPORTANT: Cards already played do NOT get reveal effects
        reveal_results = []
        all_effects_applied = []
        all_choices_required = []

        # Only cards still in hand get reveal effects
        unplayed_cards = list(player.hand.cards)  # Copy to avoid modification during iteration

        for card in unplayed_cards:
            if hasattr(card, 'reveal_effects') and card.reveal_effects:
                # Expected format: List[Dict] e.g. [{"type": "resource", "resource": "persuasion", "amount": 2}]
                if not isinstance(card.reveal_effects, list):
                    return {
                        "success": False,
                        "error": f"Card {card.name} has invalid reveal_effects format (expected list)"
                    }

                result = self.effect_resolver.resolve_effects(
                    action.player_id,
                    card.reveal_effects,
                    context={"phase": "reveal", "card": card.name}
                )

                if not result["success"]:
                    return result

                reveal_results.append({
                    "card": card.name,
                    "result": result
                })

                # Track all effects applied
                all_effects_applied.extend(result.get("effects_applied", []))
                all_choices_required.extend(result.get("choices_required", []))

        # Step 5: Move hand cards to played_cards_this_turn
        # All remaining hand cards are now revealed (they join the played cards)
        for card in unplayed_cards:
            player.hand.cards.remove(card)
            player.played_cards_this_turn.append(card)

        # Step 6: Calculate totals from effects
        # Extract persuasion and swords from ALL applied effects
        total_persuasion = 0
        temp_swords = 0

        for effect_data in all_effects_applied:
            # Effects can have different structures, check both formats
            if isinstance(effect_data, dict):
                # Check for resource effects
                if effect_data.get("type") == "resource":
                    resource = effect_data.get("resource")
                    amount = effect_data.get("amount", 0)
                    if resource == "persuasion":
                        total_persuasion += amount
                    elif resource == "sword":
                        temp_swords += amount

        # Store temporary values for acquisition phase
        player.temp_persuasion = total_persuasion
        player.temp_swords = temp_swords

        # Step 7: Notify PhaseManager (if present)
        if self.phase_manager:
            self.phase_manager.mark_player_action_complete(
                action.player_id,
                "reveal"
            )

        # Step 8: Return results
        return {
            "success": True,
            "action_type": "reveal",
            "player_id": action.player_id,
            "reveal_results": reveal_results,
            "total_persuasion": total_persuasion,
            "temp_swords": temp_swords,
            "cards_revealed": len(unplayed_cards),
            "total_cards_played": len(player.played_cards_this_turn),
            "choices_required": all_choices_required
        }

    # ==================== ACQUISITION ACTIONS ====================

    def execute_acquire_card(self, action: AcquireCardAction) -> Dict[str, Any]:
        """
        Execute card acquisition during reveal turn.

        Process:
        1. Validate phase (if PhaseManager present)
        2. Validate player has enough persuasion
        3. Use DeckManager to acquire card (if available) OR manual acquisition
        4. Add acquired card to discard (NOT played_cards_this_turn)
        5. Trigger on-acquire effects if any

        Args:
            action: AcquireCardAction

        Returns:
            Dict with acquisition results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate phase (if PhaseManager exists)
        if self.phase_manager:
            can_act, reason = self.phase_manager.can_player_take_action(
                action.player_id,
                "acquire_card"
            )
            if not can_act:
                return {
                    "success": False,
                    "error": f"Cannot acquire card: {reason}"
                }

        # Step 2: Validate player has revealed and has persuasion
        if not player.has_revealed_this_round:
            return {"success": False, "error": "Must reveal before acquiring cards"}

        temp_persuasion = getattr(player, 'temp_persuasion', 0)
        if temp_persuasion < action.card.cost:
            return {
                "success": False,
                "error": f"Not enough persuasion (need {action.card.cost}, have {temp_persuasion})"
            }

        # Step 3: Acquire card using DeckManager (preferred) or manual
        if self.deck_manager:
            if action.source == "row":
                result = self.deck_manager.acquire_card_from_imperium(
                    action.player_id,
                    action.card,
                    action.card.cost
                )
            elif action.source == "prepare":
                result = self.deck_manager.acquire_reserve_card(
                    action.player_id,
                    "prepare_the_way",
                    2  # Standard cost
                )
            elif action.source == "spice":
                result = self.deck_manager.acquire_reserve_card(
                    action.player_id,
                    "spice_must_flow",
                    9  # Standard cost
                )
            else:
                return {"success": False, "error": f"Unknown source: {action.source}"}

            if not result["success"]:
                return result

        else:
            # Manual acquisition (fallback if no DeckManager)
            if action.source == "row":
                if action.card not in self.game.board.imperium_row:
                    return {"success": False, "error": "Card not in row"}
                self.game.board.imperium_row.remove(action.card)
                self.game.board.refill_imperium_row()

            elif action.source == "prepare":
                if not self.game.board.reserve_prepare_the_way:
                    return {"success": False, "error": "No Prepare cards available"}
                action.card = self.game.board.reserve_prepare_the_way[0]

            elif action.source == "spice":
                if not self.game.board.reserve_spice_must_flow:
                    return {"success": False, "error": "No Spice cards available"}
                action.card = self.game.board.reserve_spice_must_flow[0]

            # Add to discard pile
            player.discard_pile.add_card(action.card)
            player.temp_persuasion -= action.card.cost

        # Note: Acquired cards go directly to discard pile (via DeckManager)
        # They do NOT need to be added to played_cards_this_turn
        # (played_cards_this_turn is only for cards played from hand during agent turns)

        # Step 4.5: Track acquired card for this turn (for card effects that check acquisitions)
        if not hasattr(player, 'acquired_cards_this_turn'):
            player.acquired_cards_this_turn = []
        player.acquired_cards_this_turn.append(action.card)

        # Step 5: Trigger on-acquire effects using EffectResolver
        acquire_results = None
        if hasattr(action.card, 'on_acquire_effects') and action.card.on_acquire_effects:
            acquire_results = self.effect_resolver.resolve_effects(
                action.player_id,
                action.card.on_acquire_effects,
                context={"phase": "acquire", "card": action.card.name}
            )
            if not acquire_results["success"]:
                return acquire_results

        # Step 6: Check acquire-card contracts
        contract_results = self.contract_manager.check_acquire_card_contracts(
            action.player_id,
            action.card.name
        )

        return {
            "success": True,
            "action_type": "acquire_card",
            "player_id": action.player_id,
            "card": action.card.name,
            "cost": action.card.cost,
            "source": action.source,
            "remaining_persuasion": player.temp_persuasion,
            "acquire_effects": acquire_results,
            "choices_required": acquire_results.get("choices_required", []) if acquire_results else [],
            "contract_completions": contract_results
        }

    # ==================== INTRIGUE ACTIONS ====================

    def execute_play_intrigue(self, action: PlayIntrigueAction) -> Dict[str, Any]:
        """
        Execute playing an intrigue card with phase-based effect filtering.

        Process:
        1. Validate card is in player's hand
        2. Validate current phase allows this intrigue card
        3. Filter effects to only those valid for current phase
        4. Apply effects (using EffectResolver with JSON data)
        5. Remove from player's intrigue cards
        6. Move to discard

        Args:
            action: PlayIntrigueAction

        Returns:
            Dict with intrigue effects results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate card is in hand
        if action.intrigue_card not in player.intrigue_cards:
            return {"success": False, "error": "Intrigue card not in hand"}

        # Step 2: Get current phase and map to intrigue phase
        current_game_phase = self.game.current_phase
        phase_map = {
            "player_turns": "plot",  # Agent placement and reveal
            "combat": "combat",
            "game_over": "endgame"
        }
        current_intrigue_phase = phase_map.get(
            current_game_phase.value if hasattr(current_game_phase, 'value') else str(current_game_phase),
            "plot"
        )

        # Step 3: Filter effects by phase
        card_effects = action.intrigue_card.effects if hasattr(action.intrigue_card, 'effects') else []
        playable_effects = self._filter_effects_by_phase(card_effects, current_intrigue_phase)

        if not playable_effects:
            return {
                "success": False,
                "error": f"No effects on '{action.intrigue_card.name}' can be played during {current_intrigue_phase} phase"
            }

        # Step 4: Remove from hand (before resolving in case effects fail)
        player.intrigue_cards.remove(action.intrigue_card)

        # Step 5: Apply playable effects
        effects_results = self.effect_resolver.resolve_effects(
            action.player_id,
            playable_effects,
            context={
                "phase": current_intrigue_phase,
                "card": action.intrigue_card.name,
                "intrigue": True
            }
        )

        if not effects_results["success"]:
            # Put card back if effects failed
            player.intrigue_cards.append(action.intrigue_card)
            return effects_results

        # Step 6: Card is discarded (one-time use)
        # TODO: Track in intrigue discard pile

        return {
            "success": True,
            "action_type": "play_intrigue",
            "player_id": action.player_id,
            "card": action.intrigue_card.name,
            "phase": current_intrigue_phase,
            "effects": effects_results,
            "choices_required": effects_results.get("choices_required", [])
        }

    def _filter_effects_by_phase(self, effects: list, current_phase: str) -> list:
        """
        Filter intrigue effects to only those valid for current phase.

        Args:
            effects: List of effect objects
            current_phase: Current intrigue phase ("plot", "combat", or "endgame")

        Returns:
            List of effects playable in this phase
        """
        playable = []

        for effect in effects:
            # Choice effects: filter options by phase
            if effect.get("type") == "choice":
                options = effect.get("options", [])
                valid_options = [opt for opt in options if opt.get("phase") == current_phase]

                if valid_options:
                    playable.append({
                        "type": "choice",
                        "options": valid_options
                    })
            else:
                # Non-choice effects: check phase match
                effect_phase = effect.get("phase")
                if effect_phase == current_phase or not effect_phase:
                    playable.append(effect)

        return playable

    # ==================== TROOP DEPLOYMENT ====================

    def execute_deploy_troops(self, action: DeployTroopsAction) -> Dict[str, Any]:
        """
        Execute troop deployment to conflict.

        Usually happens as part of placing agent at combat location,
        but can also happen during combat phase.

        Args:
            action: DeployTroopsAction

        Returns:
            Dict with deployment results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Validate troop availability
        if player.troops_in_garrison < action.troops_from_garrison:
            return {"success": False, "error": "Not enough troops in garrison"}

        # Move troops
        player.troops_in_garrison -= action.troops_from_garrison
        player.troops_in_conflict += action.troops_from_garrison

        return {
            "success": True,
            "action_type": "deploy_troops",
            "player_id": action.player_id,
            "troops_deployed": action.troops_from_garrison,
            "total_combat_strength": player.combat_strength
        }

    def execute_deploy_sandworm(self, action: DeploySandwormAction) -> Dict[str, Any]:
        """
        Execute sandworm deployment to conflict.

        Sandworms:
        - Usually require Maker Hooks token (unless bypassed by card)
        - Cannot be deployed if shield is active at a critical location
        - Go directly to conflict (bypass garrison)
        - Worth 3 combat strength each
        - Die at end of conflict
        - Number deployed is specified in action (from card effect or JSON data)

        Args:
            action: DeploySandwormAction with worm_count and bypass_maker_hooks

        Returns:
            Dict with deployment results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Check Maker Hooks (unless bypassed by specific card)
        if not action.bypass_maker_hooks and not player.has_maker_hooks:
            return {"success": False, "error": "Player does not have Maker Hooks"}

        # Check shield wall status
        conflict = self.game.board.current_conflict
        if conflict:
            # If conflict is at a critical location and shield is active, sandworms blocked
            if conflict.location and self.game.board.shield_active:
                # Check if it's a critical location (locations have control mechanics)
                location = self.state.get_space_by_id(conflict.location)
                if location and location.is_critical_location:
                    return {
                        "success": False,
                        "error": "Shield wall blocks sandworms at critical locations"
                    }

        # Deploy sandworm(s) - number specified in action
        player.sandworms_in_conflict += action.worm_count

        return {
            "success": True,
            "action_type": "deploy_sandworm",
            "player_id": action.player_id,
            "worms_deployed": action.worm_count,
            "sandworms_in_conflict": player.sandworms_in_conflict,
            "total_combat_strength": player.combat_strength
        }

    # ==================== CHOICE RESOLUTION ====================

    def execute_resolve_choice(self, action: ResolveChoiceAction) -> Dict[str, Any]:
        """
        Resolve a player choice from an effect (choice or conditional).

        This is called after an effect returns a "choice_required" result.
        The player makes their choice, and this method applies the effects
        of the chosen option.

        Process:
        1. Validate choice exists in pending_choices
        2. Get the selected option from the choice data
        3. Pay costs if the option has costs
        4. Apply rewards from the option
        5. Remove from pending_choices
        6. Return results

        Args:
            action: ResolveChoiceAction with choice_id and selected_option_id

        Returns:
            Dict with resolution results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate choice exists
        if action.choice_id not in self.pending_choices:
            return {"success": False, "error": f"Choice {action.choice_id} not found"}

        choice_data = self.pending_choices[action.choice_id]

        # Find the selected option
        selected_option = None
        for option in choice_data.get("options", []):
            if option["id"] == action.selected_option_id:
                selected_option = option
                break

        if not selected_option:
            return {
                "success": False,
                "error": f"Option {action.selected_option_id} not found in choice {action.choice_id}"
            }

        # Check if option is available
        if not selected_option.get("available", True):
            return {
                "success": False,
                "error": f"Option {action.selected_option_id} is not available"
            }

        # Step 2: Pay costs if option has costs
        if "costs" in selected_option and selected_option["costs"]:
            cost_result = self.effect_resolver.apply_costs(action.player_id, selected_option["costs"])
            if not cost_result["success"]:
                return cost_result

        # Step 3: Apply rewards from the option
        rewards_result = None
        if "rewards" in selected_option and selected_option["rewards"]:
            rewards_result = self.effect_resolver.resolve_effects(
                action.player_id,
                selected_option["rewards"],
                context={"phase": choice_data.get("phase", "choice"), "choice_id": action.choice_id}
            )
            if not rewards_result["success"]:
                return rewards_result

        # Step 4: Remove from pending choices
        del self.pending_choices[action.choice_id]

        return {
            "success": True,
            "action_type": "resolve_choice",
            "player_id": action.player_id,
            "choice_id": action.choice_id,
            "selected_option": action.selected_option_id,
            "rewards_applied": rewards_result,
            "new_choices_required": rewards_result.get("choices_required", []) if rewards_result else []
        }

    def execute_gather_information(self, action: GatherInformationAction) -> Dict[str, Any]:
        """
        Execute spy recall to draw intrigue.

        Process:
        1. Validate spy is at the observation post
        2. Remove spy from post (return to available)
        3. Draw 1 intrigue card
        4. Return result

        Returns:
            {
                "success": bool,
                "spy_recalled": bool,
                "intrigue_drawn": Card or None,
                "error": str (if failed)
            }
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Validate spy is at this post
        if action.observation_post_id not in player.spies_placed:
            return {
                "success": False,
                "error": f"No spy at observation post {action.observation_post_id}"
            }

        # Remove spy from post
        player.spies_placed.remove(action.observation_post_id)
        player.spies_available += 1

        # Draw intrigue card
        intrigue_drawn = None
        if self.deck_manager and self.game.board.intrigue_deck:
            intrigue_drawn = self.game.board.intrigue_deck.pop(0)
            player.intrigue_cards.append(intrigue_drawn)

        return {
            "success": True,
            "action_type": "gather_information",
            "spy_recalled": True,
            "observation_post": action.observation_post_id,
            "intrigue_drawn": intrigue_drawn,
            "player_id": action.player_id
        }

    # ==================== EFFECT ORDERING ====================

    def _order_effects_for_resolution(self, player_id: str, effects: list, context: dict) -> list:
        """
        Allow player/bot to choose the order in which effects are resolved.

        This gives players agency over effect resolution order, which can be
        strategically important (e.g., gain resources before drawing cards
        to have more options for what to trash).

        Args:
            player_id: Player who will receive the effects
            effects: List of effect objects to order
            context: Context dict (phase, card/location name, etc.)

        Returns:
            Ordered list of effects (same effects, possibly different order)
        """
        # If only 0-1 effects, no ordering needed
        if len(effects) <= 1:
            return effects

        # Check if this is a human player
        player = self.game.get_player(player_id)
        is_human = player.is_human if player else False

        # Use effect ordering manager
        try:
            from .effect_ordering import get_effect_ordering_manager
            manager = get_effect_ordering_manager()
            return manager.order_effects_interactive(
                player_id, effects, context, is_human
            )
        except ImportError:
            # Fallback to heuristic if module not available
            return self._apply_effect_ordering_heuristic(effects)

    def _apply_effect_ordering_heuristic(self, effects: list) -> list:
        """
        Apply a simple heuristic to order effects optimally.

        Heuristic priority:
        1. Resource gains (enable future actions)
        2. Draw cards (more options)
        3. Influence (long-term benefit)
        4. Other effects

        Args:
            effects: List of effect objects

        Returns:
            Ordered list of effects
        """
        def effect_priority(effect):
            """Return priority score (lower = resolve first)"""
            effect_type = effect.get("type", "")

            # Resource gains first (most immediately useful)
            if effect_type == "resource":
                resource = effect.get("resource", "")
                if resource in ["solari", "spice", "water"]:
                    return 1  # Currency resources first
                elif resource == "troop":
                    return 2  # Troops second
                else:
                    return 3  # Other resources

            # Draw cards second (more options)
            elif effect_type == "draw":
                return 4

            # Influence third (long-term benefit)
            elif effect_type == "influence":
                return 5

            # Play/trash/steal effects
            elif effect_type in ["play", "trash", "steal", "recall"]:
                return 6

            # Everything else last
            else:
                return 10

        # Sort by priority (stable sort preserves original order for ties)
        return sorted(effects, key=effect_priority)

    # ==================== COST VALIDATION & PAYMENT ====================

    def _validate_cost(self, player, cost_effects: list) -> dict:
        """
        Validate that player can afford the cost.

        Args:
            player: Player object
            cost_effects: List of cost effect objects from JSON
                e.g., [{"type": "resource", "resource": "water", "amount": 1}]

        Returns:
            {"success": bool, "error": str (if failed)}
        """
        for cost_effect in cost_effects:
            if cost_effect.get("type") == "resource":
                resource = cost_effect.get("resource")
                amount = cost_effect.get("amount", 0)

                # Check if player has enough of this resource
                if resource == "solari":
                    if player.solari < amount:
                        return {"success": False, "error": f"Need {amount} solari, have {player.solari}"}
                elif resource == "spice":
                    if player.spice < amount:
                        return {"success": False, "error": f"Need {amount} spice, have {player.spice}"}
                elif resource == "water":
                    if player.water < amount:
                        return {"success": False, "error": f"Need {amount} water, have {player.water}"}
                elif resource == "troop":
                    total_troops = player.troops_garrison + player.troops_combat + player.troops_in_reserve
                    if total_troops < amount:
                        return {"success": False, "error": f"Need {amount} troops, have {total_troops}"}

        return {"success": True}

    def _pay_cost(self, player, cost_effects: list) -> dict:
        """
        Deduct the cost from player's resources.

        Args:
            player: Player object
            cost_effects: List of cost effect objects from JSON

        Returns:
            {"success": bool, "costs_paid": dict, "error": str (if failed)}
        """
        costs_paid = {}

        for cost_effect in cost_effects:
            if cost_effect.get("type") == "resource":
                resource = cost_effect.get("resource")
                amount = cost_effect.get("amount", 0)

                # Deduct resource
                if resource == "solari":
                    player.solari -= amount
                    costs_paid["solari"] = costs_paid.get("solari", 0) + amount
                elif resource == "spice":
                    player.spice -= amount
                    costs_paid["spice"] = costs_paid.get("spice", 0) + amount
                elif resource == "water":
                    player.water -= amount
                    costs_paid["water"] = costs_paid.get("water", 0) + amount
                elif resource == "troop":
                    # Deduct troops (from garrison first, then combat, then reserve)
                    remaining = amount
                    if player.troops_garrison > 0:
                        deducted = min(player.troops_garrison, remaining)
                        player.troops_garrison -= deducted
                        remaining -= deducted
                    if remaining > 0 and player.troops_combat > 0:
                        deducted = min(player.troops_combat, remaining)
                        player.troops_combat -= deducted
                        remaining -= deducted
                    if remaining > 0 and player.troops_in_reserve > 0:
                        deducted = min(player.troops_in_reserve, remaining)
                        player.troops_in_reserve -= deducted
                        remaining -= deducted
                    costs_paid["troop"] = costs_paid.get("troop", 0) + amount

        return {"success": True, "costs_paid": costs_paid}
