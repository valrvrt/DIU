"""
Action Executor - Executes validated player actions.

This class takes validated actions (from ActionGenerator) and executes them,
modifying the game state and triggering effects through the EffectResolver.

Flow:
1. ActionGenerator tells us what actions are valid
2. Player chooses an action
3. ActionExecutor executes it (this file)
4. EffectResolver interprets card effects
"""

from typing import Dict, Any, Optional, TYPE_CHECKING, List
from dataclasses import dataclass
from ..models.game import Game
from ..models.player import Player
from ..models.card import ImperiumCard, IntrigueCard
from ..models.boardspace import BoardSpace
from .effect_resolver import EffectResolver
from .game_state import GameState
from .contract_manager import ContractManager

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
        deck_manager: Optional['DeckManager'] = None
    ):
        self.game = game
        self.state = GameState(game)
        self.effect_resolver = EffectResolver(game)
        self.contract_manager = ContractManager(game)
        self.phase_manager = phase_manager  # Optional for backward compatibility
        self.deck_manager = deck_manager  # Optional deck manager

        # Track pending choices (for multi-step resolution)
        self.pending_choices: Dict[str, Dict[str, Any]] = {}

    def _normalize_effects(self, effects: Any) -> List[Dict[str, Any]]:
        """
        Normalize effects from various formats to standard effect list.

        Handles:
        1. List format: [{"type": "resource", "resource": "persuasion", "amount": 2}]
        2. Dict with "base": {"base": {"persuasion": 2}} or {"base": [...]}
        3. Simplified dict: {"persuasion": 2, "swords": 1}

        Returns:
            List of effect dicts in standard format
        """
        # Already a list
        if isinstance(effects, list):
            return effects

        # Dict format
        if isinstance(effects, dict):
            # Check for "base" key
            if "base" in effects:
                base_effects = effects["base"]
                # Recursively normalize the base
                return self._normalize_effects(base_effects)

            # Simplified format: {"persuasion": 2, "swords": 1, "draw": 1}
            # Convert to effect list
            # IMPORTANT: Some keys are effect types, not resources
            effect_type_keys = {"draw", "influence", "trash", "steal", "recall", "play", "accept"}

            normalized = []
            for key, amount in effects.items():
                if isinstance(amount, int):  # Safety check
                    if key in effect_type_keys:
                        # These are effect types, not resources
                        # For now, skip them - they need more complex handling
                        # TODO: Implement proper conversion for these
                        continue
                    else:
                        # Regular resources
                        normalized.append({
                            "type": "resource",
                            "resource": key,
                            "amount": amount
                        })
            return normalized

        # Unknown format, return empty list
        return []

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

        # Step 4: Occupy location or infiltrate
        if action.placement_type == "spy_infiltrate":
            # Infiltration doesn't change occupied_by
            # Both players get location bonus
            pass
        else:
            # Normal placement
            if action.location.occupied_by is not None:
                return {"success": False, "error": "Location already occupied"}
            action.location.occupied_by = action.player_id

        # Step 5: Pay location cost (using EffectResolver for validation and payment)
        cost_result = None
        if hasattr(action.location, 'cost_effects') and action.location.cost_effects:
            # Future: Load from JSON, costs are in array format
            cost_result = self._pay_costs(action.player_id, action.location.cost_effects)
            if not cost_result["success"]:
                return cost_result

        # Step 6: Move card from hand to played area
        # IMPORTANT: Card goes to played_cards_this_turn, NOT discarded immediately
        # It will be discarded at end of turn (RECALL phase)
        player.hand.cards.remove(action.card)
        player.played_cards_this_turn.append(action.card)

        # Step 7: Resolve card's AGENT effects (if the card has agent effects)
        # Most cards have agent effects that trigger when played
        card_agent_results = None
        if hasattr(action.card, 'agent_effects') and action.card.agent_effects:
            # Normalize agent_effects to standard format
            effects_to_resolve = self._normalize_effects(action.card.agent_effects)

            if effects_to_resolve and len(effects_to_resolve) > 0:
                card_agent_results = self.effect_resolver.resolve_effects(
                    action.player_id,
                    effects_to_resolve,
                    context={"phase": "agent", "card": action.card.name}
                )
                if not card_agent_results["success"]:
                    return card_agent_results

        # Step 8: Resolve location effects (using EffectResolver with JSON data)
        location_results = None
        if hasattr(action.location, 'reward') and action.location.reward:
            # Load effects from spaces.JSON format
            location_results = self.effect_resolver.resolve_effects(
                action.player_id,
                action.location.reward,
                context={"phase": "agent", "location": action.location.name}
            )
            if not location_results["success"]:
                return location_results

        # Step 9: Deploy troops if combat location
        # Player specifies troops_to_deploy (from their choice)
        # Maximum deployable: troops recruited this turn + 2 (if in garrison)
        troops_deployed_count = 0
        if action.location.is_combat_space and action.troops_to_deploy > 0:
            # Player can deploy troops they recruited this turn + up to 2 from garrison
            if player.troops_in_garrison >= action.troops_to_deploy:
                player.troops_in_garrison -= action.troops_to_deploy
                player.troops_in_conflict += action.troops_to_deploy
                troops_deployed_count = action.troops_to_deploy
            else:
                return {
                    "success": False,
                    "error": f"Not enough troops in garrison (have {player.troops_in_garrison}, need {action.troops_to_deploy})"
                }

        # Step 10: Check for contract completion (location-based)
        contract_results = self.contract_manager.check_location_contracts(
            action.player_id,
            action.location.id
        )

        # Step 11: Notify PhaseManager (if present)
        if self.phase_manager:
            self.phase_manager.mark_player_action_complete(
                action.player_id,
                "place_agent"
            )

        # Step 12: Return execution log
        return {
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

    def _pay_costs(
        self,
        player_id: str,
        costs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate and pay costs for an action.

        Uses EffectResolver's cost checking logic.
        Costs are validated BEFORE being paid.

        Args:
            player_id: Player paying costs
            costs: List of cost effects (same format as rewards)

        Returns:
            Dict with success status
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Check if player can afford all costs
        for cost in costs:
            cost_type = cost.get("type")
            if cost_type == "resource":
                resource = cost.get("resource")
                amount = cost.get("amount", 0)

                if resource == "solari" and player.solari < amount:
                    return {"success": False, "error": f"Not enough solari (need {amount}, have {player.solari})"}
                elif resource == "spice" and player.spice < amount:
                    return {"success": False, "error": f"Not enough spice (need {amount}, have {player.spice})"}
                elif resource == "water" and player.water < amount:
                    return {"success": False, "error": f"Not enough water (need {amount}, have {player.water})"}

        # Pay costs (reduce resources)
        for cost in costs:
            cost_type = cost.get("type")
            if cost_type == "resource":
                resource = cost.get("resource")
                amount = cost.get("amount", 0)

                if resource == "solari":
                    player.solari -= amount
                elif resource == "spice":
                    player.spice -= amount
                elif resource == "water":
                    player.water -= amount

        return {"success": True, "costs_paid": costs}

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
                # reveal_effects can be:
                # 1. List: [{"type": "resource", "resource": "persuasion", "amount": 2}]
                # 2. Dict with "base": {"base": {"persuasion": 2}} or {"base": [...]}
                # 3. Simplified dict: {"persuasion": 2, "swords": 1}
                effects_to_resolve = self._normalize_effects(card.reveal_effects)

                if effects_to_resolve and len(effects_to_resolve) > 0:
                    result = self.effect_resolver.resolve_effects(
                        action.player_id,
                        effects_to_resolve,
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

        return {
            "success": True,
            "action_type": "acquire_card",
            "player_id": action.player_id,
            "card": action.card.name,
            "cost": action.card.cost,
            "source": action.source,
            "remaining_persuasion": player.temp_persuasion,
            "acquire_effects": acquire_results,
            "choices_required": acquire_results.get("choices_required", []) if acquire_results else []
        }

    # ==================== INTRIGUE ACTIONS ====================

    def execute_play_intrigue(self, action: PlayIntrigueAction) -> Dict[str, Any]:
        """
        Execute playing an intrigue card.

        Process:
        1. Validate card is in player's hand
        2. Pay cost if any (using EffectResolver)
        3. Remove from player's intrigue cards
        4. Apply effects (using EffectResolver with JSON data)
        5. Move to discard (or trash if specified)

        Args:
            action: PlayIntrigueAction

        Returns:
            Dict with intrigue effects results
        """
        player = self.state.get_player_by_id(action.player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Step 1: Validate
        if action.intrigue_card not in player.intrigue_cards:
            return {"success": False, "error": "Intrigue card not in hand"}

        # Step 2: Pay cost (using _pay_costs helper)
        if hasattr(action.intrigue_card, 'cost') and action.intrigue_card.cost:
            cost_result = self._pay_costs(action.player_id, action.intrigue_card.cost)
            if not cost_result["success"]:
                return cost_result

        # Step 3: Remove from hand
        player.intrigue_cards.remove(action.intrigue_card)

        # Step 4: Apply effects using EffectResolver
        effects_results = None
        if hasattr(action.intrigue_card, 'effects') and action.intrigue_card.effects:
            effects_results = self.effect_resolver.resolve_effects(
                action.player_id,
                action.intrigue_card.effects,
                context={"phase": "intrigue", "card": action.intrigue_card.name}
            )
            if not effects_results["success"]:
                return effects_results

        # Step 5: Discard or trash
        # Most intrigue cards are one-time use
        # (In full implementation, track used intrigue cards in discard)

        return {
            "success": True,
            "action_type": "play_intrigue",
            "player_id": action.player_id,
            "card": action.intrigue_card.name,
            "effects": effects_results,
            "choices_required": effects_results.get("choices_required", []) if effects_results else []
        }

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
            cost_result = self._pay_costs(action.player_id, selected_option["costs"])
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
