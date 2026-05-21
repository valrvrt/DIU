"""
Universal Effect Resolver for DUNE Imperium Uprising.

Resolves all card effects from JSON format into game state changes.
Uses Strategy pattern with handler registry for extensibility.

Matches the standardized JSON formalism from:
- conflicts.JSON
- contracts.JSON
- leaders.JSON
- spaces.JSON
- observation_posts.json
- objectives.JSON
"""

import random
from typing import Dict, List, Any, Optional, Callable
from ...models.game import Game
from ..core.game_state import GameState


class EffectResolver:
    """
    Universal effect resolver that interprets JSON effect definitions
    and applies them to game state.

    Supports:
    - Simple effects (resource, draw, influence, etc.)
    - Complex effects (choice, conditional)
    - Cost/reward patterns
    - Condition checking

    All handlers follow the standardized JSON formalism where effects have:
    - type: Effect type identifier
    - Parameters specific to that type (resource, target, amount, etc.)
    """

    def __init__(self, game: Game, influence_manager=None):
        self.game = game
        self.state = GameState(game)
        self.influence_manager = influence_manager  # Optional InfluenceManager for VP bonuses

        # Registry of effect type handlers
        self.handlers: Dict[str, Callable] = {
            # Simple resource/card effects
            "resource": self._handle_resource,
            "draw": self._handle_draw,
            "play": self._handle_play,
            "accept": self._handle_accept,
            "trash": self._handle_trash,
            "steal": self._handle_steal,
            "recall": self._handle_recall,

            # Faction effects
            "influence": self._handle_influence,

            # Board control
            "control": self._handle_control,

            # State modifications
            "council_seat": self._handle_council_seat,
            "maker_hooks": self._handle_maker_hooks,
            "shieldwall_deactivate": self._handle_shieldwall_deactivate,
            "signet": self._handle_signet,

            # Complex effects
            "choice": self._handle_choice,
            "conditional": self._handle_conditional,

            # Shorthand effect types (delegate to resource handler)
            "persuasion": self._handle_persuasion_shorthand,
            "sword": self._handle_sword_shorthand,
            "solari": self._handle_solari_shorthand,
            "spice": self._handle_spice_shorthand,
            "water": self._handle_water_shorthand,
            "troop": self._handle_troop_shorthand,
        }

    # ==================== MAIN RESOLUTION ENTRY POINT ====================

    def resolve_effects(
        self,
        player_id: str,
        effects: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for resolving a list of effects.

        Args:
            player_id: ID of player receiving effects
            effects: List of effect definitions from JSON
            context: Optional context (phase, source, etc.)

        Returns:
            Dict with:
                - success: bool
                - effects_applied: List of applied effects
                - choices_required: List of choices that need user input
                - error: Optional error message

        Example:
            effects = [
                {"type": "resource", "resource": "solari", "amount": 2},
                {"type": "influence", "target": "fremen", "amount": 1, "times": 1}
            ]
            result = resolver.resolve_effects("player1", effects)
        """
        if context is None:
            context = {}

        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": f"Player {player_id} not found"
            }

        applied_effects = []
        choices_required = []

        for effect in effects:
            # Skip if effect is not a dict (malformed data)
            if not isinstance(effect, dict):
                continue

            effect_type = effect.get("type")

            if not effect_type:
                return {
                    "success": False,
                    "error": f"Effect missing 'type' field: {effect}"
                }

            # Get handler for this effect type
            handler = self.handlers.get(effect_type)

            if not handler:
                return {
                    "success": False,
                    "error": f"Unknown effect type: {effect_type}"
                }

            # Execute handler
            try:
                result = handler(player_id, effect, context)

                if not result["success"]:
                    return result

                # Track what was applied
                if result.get("applied"):
                    applied_effects.append(result["applied"])

                # Track choices that need resolution
                if result.get("choice_required"):
                    choices_required.append(result["choice_data"])

            except Exception as e:
                return {
                    "success": False,
                    "error": f"Error executing {effect_type}: {str(e)}"
                }

        return {
            "success": True,
            "effects_applied": applied_effects,
            "choices_required": choices_required
        }

    # ==================== SIMPLE EFFECT HANDLERS ====================

    def _handle_resource(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle resource effects: {"type": "resource", "resource": "solari", "amount": 2}

        Supported resources:
        - solari, spice, water, troop, sword, persuasion, victory_point
        - agent, spy, worm, intrigue

        Optional parameters:
        - times: Multiplier for amount (default 1)
        - bonus_spice: Flag for spice from maker spaces
        """
        player = self.state.get_player_by_id(player_id)
        resource = effect.get("resource")
        amount = effect.get("amount", 0)
        times = effect.get("times", 1)
        bonus_spice = effect.get("bonus_spice", False)

        if not resource:
            return {"success": False, "error": "Resource effect missing 'resource' field"}

        # Calculate total amount (amount * times)
        total_amount = amount * times

        # Apply resource based on type
        if resource == "solari":
            player.solari += total_amount
        elif resource == "spice":
            player.spice += total_amount
        elif resource == "water":
            player.water += total_amount
        elif resource == "troop" or resource == "troops":  # Handle both singular and plural
            # Add troops to garrison
            player.troops_in_garrison += total_amount
        elif resource == "sword" or resource == "swords":  # Handle both singular and plural
            # Temporary combat resource
            if not hasattr(player, "temp_swords"):
                player.temp_swords = 0
            player.temp_swords += total_amount
        elif resource == "persuasion":
            # Temporary acquire resource
            if not hasattr(player, "temp_persuasion"):
                player.temp_persuasion = 0
            player.temp_persuasion += total_amount
        elif resource == "victory_point":
            player.victory_points += total_amount
        elif resource == "agent":
            # Permanent agent increase
            player.total_available_agents += total_amount
            player.agents_available += total_amount
        elif resource == "spy":
            # Add spy to available pool
            player.spies_available += total_amount
        elif resource == "worm":
            # Add sandworms (used in combat)
            if not hasattr(player, "sandworms_available"):
                player.sandworms_available = 0
            player.sandworms_available += total_amount
        elif resource == "intrigue":
            # Draw intrigue cards (delegate to draw handler)
            return self._handle_draw(
                player_id,
                {"type": "draw", "deck": "intrigue", "amount": total_amount},
                context
            )
        else:
            return {
                "success": False,
                "error": f"Unknown resource type: {resource}"
            }

        return {
            "success": True,
            "applied": {
                "type": "resource",
                "resource": resource,
                "amount": total_amount,
                "bonus_spice": bonus_spice
            }
        }

    def _handle_draw(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle draw effects: {"type": "draw", "deck": "intrigue"|"deck", "amount": 1}

        Auto-shuffles discard/played when deck empty.

        Supported decks:
        - intrigue: Draw from intrigue deck (shuffles played intrigue when empty)
        - contract: Draw from contract deck
        - deck: Draw from player's own deck (shuffles discard when empty)
        """
        player = self.state.get_player_by_id(player_id)
        deck_type = effect.get("deck")
        amount = effect.get("amount", 0)

        if not deck_type:
            return {"success": False, "error": "Draw effect missing 'deck' field"}

        cards_drawn = []

        if deck_type == "intrigue":
            # Draw from board's intrigue deck
            for _ in range(amount):
                # If intrigue deck empty, shuffle played intrigue back
                if not self.game.board.intrigue_deck and hasattr(self.game.board, 'played_intrigue_deck'):
                    self.game.board.intrigue_deck = self.game.board.played_intrigue_deck
                    random.shuffle(self.game.board.intrigue_deck)
                    self.game.board.played_intrigue_deck = []

                if self.game.board.intrigue_deck:
                    card = self.game.board.intrigue_deck.pop(0)
                    player.intrigue_cards.append(card)
                    cards_drawn.append(card)

        elif deck_type == "contract":
            # Draw from board's contract deck
            for _ in range(amount):
                if self.game.board.contract_deck:
                    contract = self.game.board.contract_deck.pop(0)
                    # Add to active contracts
                    player.contracts_active.append(contract)
                    cards_drawn.append(contract)

        elif deck_type == "deck":
            # Draw from player's own deck (use DeckManager for auto-shuffle)
            if hasattr(self.game, 'deck_manager') and self.game.deck_manager:
                result = self.game.deck_manager.draw_cards(player_id, amount)
                if not result["success"]:
                    return result
                cards_drawn = result.get("cards_drawn", [])
            else:
                # Fallback: manual draw with shuffle
                from ...models.deck import Deck
                for _ in range(amount):
                    if player.deck.is_empty and not player.discard_pile.is_empty:
                        # Shuffle discard into deck
                        player.deck = player.discard_pile
                        player.deck.shuffle()
                        player.discard_pile = Deck()

                    if not player.deck.is_empty:
                        card = player.deck.draw()
                        player.hand.add_card(card)
                        cards_drawn.append(card)

        else:
            return {
                "success": False,
                "error": f"Unknown deck type: {deck_type}"
            }

        return {
            "success": True,
            "applied": {
                "type": "draw",
                "deck": deck_type,
                "amount": len(cards_drawn),
                "cards": cards_drawn
            }
        }

    def _handle_play(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle play effects: {"type": "play", "unit": "spy", "amount": 1}

        Plays a spy to an observation post.
        Requires player choice of which post.
        """
        unit_type = effect.get("unit")
        amount = effect.get("amount", 0)

        if unit_type != "spy":
            return {"success": False, "error": "Play effect only supports 'spy' unit"}

        player = self.state.get_player_by_id(player_id)

        if player.spies_available < amount:
            return {
                "success": False,
                "error": f"Not enough spies available (have {player.spies_available}, need {amount})"
            }

        # Get available observation posts (not already occupied by this player)
        available_posts = []
        for post in self.game.board.observation_posts:
            if post.id not in player.spies_placed:
                available_posts.append({
                    "post_id": post.id,
                    "post_name": post.name,
                    "connected_locations": post.connected_locations
                })

        if not available_posts:
            return {
                "success": False,
                "error": "No available observation posts"
            }

        # Requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "play_spy",
                "amount": amount,
                "available_posts": available_posts
            }
        }

    def _handle_accept(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle accept effects: {"type": "accept", "amount": 1}

        Accepts a contract from the contract row.
        Requires player choice of which contract (row refills automatically).
        """
        amount = effect.get("amount", 1)

        # Get available contracts from row
        if not hasattr(self.game.board, 'contract_row') or not self.game.board.contract_row:
            return {
                "success": False,
                "error": "No contracts available in contract row"
            }

        available_contracts = self.game.board.contract_row[:2]  # Only first 2 are visible

        if not available_contracts:
            return {
                "success": False,
                "error": "Contract row is empty"
            }

        # Requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "accept_contract",
                "amount": amount,
                "available_contracts": available_contracts
            }
        }

    def _handle_trash(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle trash effects: {"type": "trash", "deck": ["hand", "played"], "amount": 1}

        Requires player choice of which card to trash.
        Returns choice_required flag.
        """
        player = self.state.get_player_by_id(player_id)
        deck_sources = effect.get("deck")
        amount = effect.get("amount", 0)

        # If amount is 0 or negative, nothing to trash
        if amount <= 0:
            return {
                "success": True,
                "applied": {"type": "trash", "amount": 0, "cards_trashed": []}
            }

        if not deck_sources:
            return {"success": False, "error": "Trash effect missing 'deck' field"}

        # Normalize to list
        if isinstance(deck_sources, str):
            deck_sources = [deck_sources]

        # Build list of available cards to trash
        available_cards = []

        for source in deck_sources:
            if source == "hand":
                available_cards.extend([
                    {"card": card, "source": "hand"}
                    for card in player.hand.cards
                ])
            elif source == "played":
                available_cards.extend([
                    {"card": card, "source": "played"}
                    for card in player.played_cards_this_turn
                ])
            elif source == "owned_intrigue":
                available_cards.extend([
                    {"card": card, "source": "intrigue"}
                    for card in player.intrigue_cards
                ])
            elif source == "discard":
                available_cards.extend([
                    {"card": card, "source": "discard"}
                    for card in player.discard_pile.cards
                ])

        if len(available_cards) < amount:
            return {
                "success": False,
                "error": f"Not enough cards to trash (need {amount}, have {len(available_cards)})"
            }

        # This effect requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "trash_card",
                "amount": amount,
                "available_cards": available_cards
            }
        }

    def _handle_steal(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle steal effects: {"type": "steal", "deck": "intrigue", "amount": 1}

        Steals intrigue from opponent with 4+ intrigues.
        Requires player choice of which opponent.
        """
        deck_type = effect.get("deck")
        amount = effect.get("amount", 0)

        if deck_type != "intrigue":
            return {"success": False, "error": "Steal only supports 'intrigue' deck"}

        # Find opponents with 4+ intrigue cards
        valid_targets = []
        for other_player in self.game.players:
            if other_player.player_id == player_id:
                continue
            if len(other_player.intrigue_cards) >= 4:
                valid_targets.append({
                    "player_id": other_player.player_id,
                    "player_name": other_player.name,
                    "intrigue_count": len(other_player.intrigue_cards)
                })

        if not valid_targets:
            # No valid targets - effect fails silently
            return {
                "success": True,
                "applied": {
                    "type": "steal",
                    "amount": 0,
                    "reason": "No opponents with 4+ intrigue cards"
                }
            }

        # Requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "steal_intrigue",
                "amount": amount,
                "valid_targets": valid_targets
            }
        }

    def _handle_recall(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle recall effects: {"type": "recall", "unit": "agent"|"spy", "amount": 1}

        Recalls agent/spy from board to available pool.
        Requires player choice of which unit to recall (excluding triggering unit).
        """
        unit_type = effect.get("unit")  # "agent" or "spy"
        amount = effect.get("amount", 0)

        if unit_type not in ["agent", "spy"]:
            return {"success": False, "error": "Recall unit must be 'agent' or 'spy'"}

        player = self.state.get_player_by_id(player_id)

        if unit_type == "agent":
            # Get locations where player has agents (exclude current context location)
            placed_locations = player.agents_placed.copy()

            # Exclude the triggering location if in context
            if context and "location_id" in context:
                if context["location_id"] in placed_locations:
                    placed_locations.remove(context["location_id"])

            if not placed_locations:
                return {
                    "success": True,
                    "applied": {
                        "type": "recall",
                        "unit": "agent",
                        "amount": 0,
                        "reason": "No agents to recall"
                    }
                }

            # Requires player choice of which location
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "recall_agent",
                    "amount": amount,
                    "placed_locations": placed_locations
                }
            }

        elif unit_type == "spy":
            # Get observation posts where player has spies
            placed_posts = player.spies_placed.copy()

            # Exclude the triggering post if in context
            if context and "observation_post_id" in context:
                if context["observation_post_id"] in placed_posts:
                    placed_posts.remove(context["observation_post_id"])

            if not placed_posts:
                return {
                    "success": True,
                    "applied": {
                        "type": "recall",
                        "unit": "spy",
                        "amount": 0,
                        "reason": "No spies to recall"
                    }
                }

            # Requires player choice of which post
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "recall_spy",
                    "amount": amount,
                    "placed_posts": placed_posts
                }
            }

    def _handle_influence(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle influence effects: {"type": "influence", "target": "fremen", "amount": 1, "times": 1}

        Increases influence with factions.
        "target": "any" requires player choice.
        """
        player = self.state.get_player_by_id(player_id)
        target = effect.get("target")
        amount = effect.get("amount", 0)
        times = effect.get("times", 1)

        if not target:
            return {"success": False, "error": "Influence effect missing 'target' field"}

        total_influence = amount * times

        if target == "any":
            # Player must choose faction
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "choose_influence_faction",
                    "amount": total_influence,
                    "factions": ["fremen", "bene_gesserit", "spacing_guild", "emperor"]
                }
            }

        # Apply to specific faction
        # Use InfluenceManager if available (handles VP bonuses and alliances)
        if self.influence_manager:
            result = self.influence_manager.add_influence(player_id, target, total_influence)
            if not result.get("success"):
                return result

            return {
                "success": True,
                "applied": {
                    "type": "influence",
                    "target": target,
                    "amount": total_influence,
                    "vp_gained": result.get("vp_gained", 0),
                    "alliance_gained": result.get("alliance_gained", False)
                }
            }
        else:
            # Fallback: direct influence addition (backward compatibility)
            if target == "fremen":
                player.fremen_influence += total_influence
            elif target == "bene_gesserit":
                player.bene_gesserit_influence += total_influence
            elif target == "spacing_guild":
                player.spacing_guild_influence += total_influence
            elif target == "emperor":
                player.emperor_influence += total_influence
            else:
                return {
                    "success": False,
                    "error": f"Unknown faction target: {target}"
                }

            return {
                "success": True,
                "applied": {
                    "type": "influence",
                    "target": target,
                    "amount": total_influence
                }
            }

    def _handle_control(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle control effects: {"type": "control", "location": "spice_refinery"}

        Claims control of board locations.
        """
        player = self.state.get_player_by_id(player_id)
        location = effect.get("location")

        if not location:
            return {"success": False, "error": "Control effect missing 'location' field"}

        # Add to controlled locations if not already present
        if location not in player.controlled_locations:
            player.controlled_locations.append(location)

        return {
            "success": True,
            "applied": {
                "type": "control",
                "location": location
            }
        }

    def _handle_council_seat(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle council seat effects: {"type": "council_seat", "value": true}
        """
        player = self.state.get_player_by_id(player_id)
        value = effect.get("value", False)

        player.has_high_council_sit = value

        return {
            "success": True,
            "applied": {
                "type": "council_seat",
                "value": value
            }
        }

    def _handle_maker_hooks(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle maker hooks effects: {"type": "maker_hooks", "value": true}
        """
        player = self.state.get_player_by_id(player_id)
        value = effect.get("value", False)

        player.has_maker_hooks = value

        return {
            "success": True,
            "applied": {
                "type": "maker_hooks",
                "value": value
            }
        }

    def _handle_signet(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle signet effects: {"type": "signet"}
        Signet abilities are triggered during reveal phase based on leader.
        This is a placeholder - actual signet logic handled in reveal phase.
        """
        return {
            "success": True,
            "effect_type": "signet",
            "applied": []
        }

    def _handle_shieldwall_deactivate(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle shieldwall deactivate effects: {"type": "shieldwall_deactivate", "value": true}
        """
        # This affects game state, not player state
        # Store in context or game flags
        if not hasattr(self.game, 'shieldwall_active'):
            self.game.shieldwall_active = True

        value = effect.get("value", False)
        if value:
            self.game.shieldwall_active = False

        return {
            "success": True,
            "applied": {
                "type": "shieldwall_deactivate",
                "value": value
            }
        }

    # ==================== COMPLEX EFFECT HANDLERS ====================

    def _handle_choice(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle choice effects: Player must select one option.

        Example:
        {
            "type": "choice",
            "required": true,
            "options": [
                {
                    "id": "option1",
                    "reward": [{"type": "resource", "resource": "solari", "amount": 2}]
                },
                {
                    "id": "option2",
                    "cost": [{"type": "resource", "resource": "spice", "amount": 1}],
                    "reward": [{"type": "resource", "resource": "solari", "amount": 4}]
                }
            ]
        }
        """
        options = effect.get("options", [])
        required = effect.get("required", False)

        if not options:
            return {"success": False, "error": "Choice effect missing 'options' field"}

        # Evaluate each option for availability
        available_options = []

        for option in options:
            option_id = option.get("id", "unknown")
            checks = option.get("check", [])
            costs = option.get("cost", [])
            rewards = option.get("reward", [])

            # Check if option is available (check conditions)
            is_available = True
            unavailable_reason = None

            if checks:
                check_result = self._evaluate_checks(player_id, checks)
                if not check_result["success"]:
                    is_available = False
                    unavailable_reason = check_result.get("error", "Requirements not met")

            # Check if player can afford costs
            if costs and is_available:
                cost_check = self._check_costs(player_id, costs)
                if not cost_check["success"]:
                    is_available = False
                    unavailable_reason = cost_check.get("error", "Cannot afford cost")

            available_options.append({
                "id": option_id,
                "available": is_available,
                "unavailable_reason": unavailable_reason,
                "costs": costs,
                "rewards": rewards
            })

        # Return choice requirement
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "choice",
                "required": required,
                "options": available_options
            }
        }

    def _handle_conditional(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle conditional effects: Optional cost for reward.

        Example:
        {
            "type": "conditional",
            "cost": [{"type": "resource", "resource": "spice", "amount": 3}],
            "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
        }
        """
        costs = effect.get("cost", [])
        rewards = effect.get("reward", [])

        # Check if player can afford
        cost_check = self._check_costs(player_id, costs)

        if not cost_check["success"]:
            # Can't afford, skip silently (conditional is optional)
            return {
                "success": True,
                "applied": {
                    "type": "conditional",
                    "declined": True,
                    "reason": "Cannot afford cost"
                }
            }

        # Present choice to player
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "conditional",
                "costs": costs,
                "rewards": rewards
            }
        }

    # ==================== HELPER METHODS ====================

    def _evaluate_checks(
        self,
        player_id: str,
        checks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluate a list of check conditions.

        Returns success=True only if ALL checks pass.
        """
        player = self.state.get_player_by_id(player_id)

        for check in checks:
            check_type = check.get("type")

            if check_type == "influence":
                target = check.get("target")
                amount = check.get("amount", 0)

                current_influence = 0
                if target == "fremen":
                    current_influence = player.fremen_influence
                elif target == "bene_gesserit":
                    current_influence = player.bene_gesserit_influence
                elif target == "spacing_guild":
                    current_influence = player.spacing_guild_influence
                elif target == "emperor":
                    current_influence = player.emperor_influence

                if current_influence < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} {target} influence (have {current_influence})"
                    }

            elif check_type == "council_seat":
                value = check.get("value", False)
                if player.has_high_council_sit != value:
                    return {
                        "success": False,
                        "error": "Requires council seat"
                    }

            elif check_type == "always":
                # Always passes
                continue

            else:
                # Unknown check type - skip for now
                continue

        return {"success": True}

    def _check_costs(
        self,
        player_id: str,
        costs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check if player can afford all costs.

        Does NOT deduct costs - just validates availability.
        """
        player = self.state.get_player_by_id(player_id)

        for cost in costs:
            cost_type = cost.get("type")

            if cost_type == "resource":
                resource = cost.get("resource")
                amount = cost.get("amount", 0)

                current_amount = 0
                if resource == "solari":
                    current_amount = player.solari
                elif resource == "spice":
                    current_amount = player.spice
                elif resource == "water":
                    current_amount = player.water

                if current_amount < amount:
                    return {
                        "success": False,
                        "error": f"Not enough {resource} (need {amount}, have {current_amount})"
                    }

        return {"success": True}

    def apply_costs(
        self,
        player_id: str,
        costs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Actually deduct costs from player resources.

        Should be called after _check_costs validation.
        """
        player = self.state.get_player_by_id(player_id)

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

        return {"success": True}

    def execute_choice(
        self,
        player_id: str,
        choice_data: Dict[str, Any],
        selected_option_id: str
    ) -> Dict[str, Any]:
        """
        Execute a player's choice selection.

        Args:
            player_id: Player making choice
            choice_data: Original choice data from resolve_effects
            selected_option_id: ID of selected option

        Returns:
            Result of executing chosen option
        """
        choice_type = choice_data.get("type")

        if choice_type == "choice":
            # Find selected option
            options = choice_data.get("options", [])
            selected = None

            for option in options:
                if option["id"] == selected_option_id:
                    selected = option
                    break

            if not selected:
                return {
                    "success": False,
                    "error": f"Invalid option ID: {selected_option_id}"
                }

            if not selected["available"]:
                return {
                    "success": False,
                    "error": f"Option not available: {selected.get('unavailable_reason')}"
                }

            # Apply costs
            if selected.get("costs"):
                cost_result = self.apply_costs(player_id, selected["costs"])
                if not cost_result["success"]:
                    return cost_result

            # Apply rewards
            if selected.get("rewards"):
                return self.resolve_effects(player_id, selected["rewards"])

            return {"success": True}

        elif choice_type == "conditional":
            # Player chose to pay cost for reward
            if selected_option_id == "accept":
                # Apply costs
                costs = choice_data.get("costs", [])
                if costs:
                    cost_result = self.apply_costs(player_id, costs)
                    if not cost_result["success"]:
                        return cost_result

                # Apply rewards
                rewards = choice_data.get("rewards", [])
                if rewards:
                    return self.resolve_effects(player_id, rewards)

            # Player declined
            return {
                "success": True,
                "applied": {"type": "conditional", "declined": True}
            }

        elif choice_type == "trash_card":
            # Execute card trashing
            available_cards = choice_data.get("available_cards", [])
            player = self.state.get_player_by_id(player_id)

            # Find the selected card
            selected_card_info = None
            for card_info in available_cards:
                if card_info["card"].id == selected_option_id:
                    selected_card_info = card_info
                    break

            if not selected_card_info:
                return {"success": False, "error": "Invalid card selection"}

            card = selected_card_info["card"]
            source = selected_card_info["source"]

            # Remove from source
            if source == "hand":
                player.hand.remove_card(card)
            elif source == "played":
                player.played_cards_this_turn.remove(card)
            elif source == "intrigue":
                player.intrigue_cards.remove(card)
            elif source == "discard":
                player.discard_pile.remove_card(card)

            # Add to trash
            if hasattr(self.game, 'trash_pile'):
                self.game.trash_pile.append(card)

            return {
                "success": True,
                "applied": {
                    "type": "trash",
                    "card_trashed": card.name,
                    "from_source": source
                }
            }

        elif choice_type == "steal_intrigue":
            # Execute intrigue steal
            target_player_id = selected_option_id  # player_id of target
            amount = choice_data.get("amount", 1)

            target_player = self.state.get_player_by_id(target_player_id)
            player = self.state.get_player_by_id(player_id)

            if not target_player or not player:
                return {"success": False, "error": "Invalid player"}

            if len(target_player.intrigue_cards) < 4:
                return {"success": False, "error": "Target doesn't have 4+ intrigue"}

            # Steal random intrigue
            stolen_card = random.choice(target_player.intrigue_cards)
            target_player.intrigue_cards.remove(stolen_card)
            player.intrigue_cards.append(stolen_card)

            return {
                "success": True,
                "applied": {
                    "type": "steal",
                    "card_stolen": stolen_card,
                    "from_player": target_player.name
                }
            }

        elif choice_type == "recall_agent":
            # Execute agent recall
            location_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            if location_id not in player.agents_placed:
                return {"success": False, "error": "No agent at that location"}

            player.agents_placed.remove(location_id)
            player.agents_available += 1

            # Clear occupation from board space
            for space in self.game.board.spaces:
                if space.id == location_id and space.occupied_by == player_id:
                    space.occupied_by = None

            return {
                "success": True,
                "applied": {
                    "type": "recall",
                    "unit": "agent",
                    "location": location_id
                }
            }

        elif choice_type == "recall_spy":
            # Execute spy recall
            post_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            if post_id not in player.spies_placed:
                return {"success": False, "error": "No spy at that post"}

            player.spies_placed.remove(post_id)
            player.spies_available += 1

            return {
                "success": True,
                "applied": {
                    "type": "recall",
                    "unit": "spy",
                    "post": post_id
                }
            }

        elif choice_type == "accept_contract":
            # Execute contract acceptance
            contract = None
            available_contracts = choice_data.get("available_contracts", [])

            # Find the selected contract
            for c in available_contracts:
                if c.id == selected_option_id:
                    contract = c
                    break

            if not contract:
                return {"success": False, "error": "Contract not found"}

            player = self.state.get_player_by_id(player_id)

            if contract not in self.game.board.contract_row:
                return {"success": False, "error": "Contract not in row"}

            # Add to player's contracts
            player.contracts_active.append(contract)

            # Remove from row
            self.game.board.contract_row.remove(contract)

            # Refill row
            if hasattr(self.game.board, 'contract_deck') and self.game.board.contract_deck:
                new_contract = self.game.board.contract_deck.pop(0)
                self.game.board.contract_row.append(new_contract)

            return {
                "success": True,
                "applied": {
                    "type": "accept",
                    "contract": contract.name
                }
            }

        elif choice_type == "play_spy":
            # Execute spy placement
            post_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            if player.spies_available < 1:
                return {"success": False, "error": "No spies available"}

            if post_id in player.spies_placed:
                return {"success": False, "error": "Already have spy at that post"}

            player.spies_available -= 1
            player.spies_placed.append(post_id)

            return {
                "success": True,
                "applied": {
                    "type": "play",
                    "unit": "spy",
                    "post": post_id
                }
            }

        else:
            return {
                "success": False,
                "error": f"Unknown choice type: {choice_type}"
            }

    # ==================== PUBLIC VALIDATION METHODS ====================

    def validate_location_access(self, player_id: str, location_checks: List) -> Dict[str, Any]:
        """
        Public wrapper for location requirement validation.

        Evaluates whether a player meets the requirements to access a location.

        Args:
            player_id: Player to check
            location_checks: List of check conditions from location JSON

        Returns:
            Dict with success=True if all checks pass, or error details
        """
        return self._evaluate_checks(player_id, location_checks)

    def validate_choice_costs(self, player_id: str, costs: List) -> bool:
        """
        Public wrapper for checking if player can afford choice costs.

        Args:
            player_id: Player to check
            costs: List of cost requirements

        Returns:
            True if player can afford all costs, False otherwise
        """
        result = self._check_costs(player_id, costs)
        return result["success"]

    # ==================== SHORTHAND EFFECT HANDLERS ====================

    def _handle_persuasion_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "persuasion", "amount": 2}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "persuasion", "amount": effect.get("amount", 0)},
            context
        )

    def _handle_sword_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "sword", "amount": 1}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "sword", "amount": effect.get("amount", 0)},
            context
        )

    def _handle_solari_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "solari", "amount": 2}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "solari", "amount": effect.get("amount", 0)},
            context
        )

    def _handle_spice_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "spice", "amount": 2}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "spice", "amount": effect.get("amount", 0)},
            context
        )

    def _handle_water_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "water", "amount": 1}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "water", "amount": effect.get("amount", 0)},
            context
        )

    def _handle_troop_shorthand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle shorthand: {"type": "troop", "amount": 2}"""
        return self._handle_resource(
            player_id,
            {"type": "resource", "resource": "troop", "amount": effect.get("amount", 0)},
            context
        )
