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

from typing import Dict, List, Any, Optional, Callable
from ..models.game import Game
from ..engine.game_state import GameState


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
        Handle draw effects: {"type": "draw", "deck": "intrigue", "amount": 1}

        Supported decks:
        - intrigue: Draw from intrigue deck
        - contract: Draw from contract deck
        - deck: Draw from player's own deck
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
            # Draw from player's own deck
            # This should be handled by DeckManager if available
            if hasattr(self.game, 'deck_manager') and self.game.deck_manager:
                result = self.game.deck_manager.draw_cards(player_id, amount)
                if not result["success"]:
                    return result
                cards_drawn = result.get("cards_drawn", [])
            else:
                # Fallback: draw directly
                for _ in range(amount):
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

        Deploys units from reserve to board.
        """
        player = self.state.get_player_by_id(player_id)
        unit = effect.get("unit")
        amount = effect.get("amount", 0)

        if not unit:
            return {"success": False, "error": "Play effect missing 'unit' field"}

        if unit == "spy":
            # Deploy spy from available pool
            if player.spies_available < amount:
                return {
                    "success": False,
                    "error": f"Not enough spies available (need {amount}, have {player.spies_available})"
                }

            player.spies_available -= amount
            # Track deployed spies (add to placed list)
            # Location would come from context
            location = context.get("location", "unknown")
            player.spies_placed.append(location)

        else:
            return {
                "success": False,
                "error": f"Unknown unit type: {unit}"
            }

        return {
            "success": True,
            "applied": {
                "type": "play",
                "unit": unit,
                "amount": amount
            }
        }

    def _handle_accept(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle accept effects: {"type": "accept", "deck": "contract", "amount": 1}

        Allows player to accept contracts.
        """
        # Accept is essentially the same as draw for contracts
        return self._handle_draw(player_id, effect, context)

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

        Steals cards from opponents. Requires player choice of target.
        """
        deck_type = effect.get("deck")
        amount = effect.get("amount", 0)

        if not deck_type:
            return {"success": False, "error": "Steal effect missing 'deck' field"}

        # Build list of valid targets
        player = self.state.get_player_by_id(player_id)
        targets = []

        for opponent in self.game.players:
            if opponent.player_id == player_id:
                continue  # Can't steal from yourself

            if deck_type == "intrigue":
                if len(opponent.intrigue_cards) > 0:
                    targets.append({
                        "player_id": opponent.player_id,
                        "player_name": opponent.name,
                        "available_cards": len(opponent.intrigue_cards)
                    })

        if not targets:
            return {
                "success": False,
                "error": "No valid targets for steal effect"
            }

        # This effect requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "steal_card",
                "deck": deck_type,
                "amount": amount,
                "targets": targets
            }
        }

    def _handle_recall(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle recall effects: {"type": "recall", "unit": "agent", "amount": 1}

        Returns deployed units back to available pool.
        """
        player = self.state.get_player_by_id(player_id)
        unit = effect.get("unit")
        amount = effect.get("amount", 0)

        if not unit:
            return {"success": False, "error": "Recall effect missing 'unit' field"}

        if unit == "agent":
            # Return agents from board to available pool
            if len(player.agents_placed) < amount:
                return {
                    "success": False,
                    "error": f"Not enough agents to recall (need {amount}, have {len(player.agents_placed)})"
                }

            # Requires choice if player has multiple agents placed
            if len(player.agents_placed) > amount:
                return {
                    "success": True,
                    "choice_required": True,
                    "choice_data": {
                        "type": "recall_agent",
                        "amount": amount,
                        "placed_agents": player.agents_placed.copy()
                    }
                }

            # If exact match, recall all
            recalled = []
            for _ in range(amount):
                if player.agents_placed:
                    location = player.agents_placed.pop()
                    recalled.append(location)
                    player.agents_available += 1

            return {
                "success": True,
                "applied": {
                    "type": "recall",
                    "unit": unit,
                    "amount": len(recalled),
                    "from_locations": recalled
                }
            }

        else:
            return {
                "success": False,
                "error": f"Unknown unit type for recall: {unit}"
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

        else:
            return {
                "success": False,
                "error": f"Unknown choice type: {choice_type}"
            }

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
