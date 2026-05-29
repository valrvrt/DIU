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

        # Conditional reward tracking (for trigger-based intrigue cards)
        # Format: {player_id: [{condition, reward, card_name}, ...]}
        self.active_conditional_rewards: Dict[str, List[Dict[str, Any]]] = {}

        # Registry of effect type handlers
        self.handlers: Dict[str, Callable] = {
            # Simple resource/card effects
            "resource": self._handle_resource,
            "draw": self._handle_draw,
            "play": self._handle_play,
            "accept": self._handle_accept,
            "acquire": self._handle_acquire,
            "trash": self._handle_trash,
            "discard": self._handle_discard,
            "steal": self._handle_steal,
            "recall": self._handle_recall,
            "retreat": self._handle_retreat,
            "opponent_discard": self._handle_opponent_discard,

            # Faction effects
            "influence": self._handle_influence,

            # Board control
            "control": self._handle_control,

            # State modifications
            "council_seat": self._handle_council_seat,
            "maker_hooks": self._handle_maker_hooks,
            "agent_on_maker": self._handle_agent_on_maker,
            "shieldwall_deactivate": self._handle_shieldwall_deactivate,
            "shield_active": self._handle_shield_active,
            "manipulate": self._handle_manipulate,
            "signet": self._handle_signet,

            # Complex effects
            "choice": self._handle_choice,
            "conditional": self._handle_conditional,

            # Intrigue-specific effect types
            "action": self._handle_action,
            "conditional_reward": self._handle_conditional_reward,
            "endgame_condition": self._handle_endgame_condition,

            # Shorthand effect types (delegate to resource handler)
            "persuasion": self._handle_persuasion_shorthand,
            "sword": self._handle_sword_shorthand,
            "solari": self._handle_solari_shorthand,
            "spice": self._handle_spice_shorthand,
            "water": self._handle_water_shorthand,
            "troop": self._handle_troop_shorthand,

            # Generic "per X" multiplier effect
            "multiple": self._handle_multiple,

            # Card 30 specific effect
            "deck_manipulation": self._handle_deck_manipulation,

            # Card 34 - Overthrow
            "influence_double": self._handle_influence_double,

            # Card 36 - Price is No Object
            "acquire_with_solari": self._handle_acquire_with_solari,

            # Card 37 - Priority Contracts
            # NOTE: "choice" handler already registered above at line 76 (general choice handler)
            # NOTE: "trash" and "play" handlers already registered above (no duplicates needed)

            # Card 41 - Sardaukar Coordination
            "bypass_troops_deployment_rule": self._handle_bypass_troops_deployment_rule,

            # Card 43 - Shishakli
            "trash_to_acquire": self._handle_trash_to_acquire,

            # Card 45 - Smuggler's Haven
            "trade": self._handle_trade,

            # Card 47, 48 - Acquire card effects
            "acquire_card": self._handle_acquire_card,

            # Card 54 - Treacherous Maneuver
            "trash_hand_card": self._handle_trash_hand_card,

            # Card 57 - Undercover Asset
            "ignore_influence_requirements": self._handle_ignore_influence_requirements,

            # Card 58 - Unswerving Loyalty
            "deploy_or_retreat_troop": self._handle_deploy_or_retreat_troop,

            # Card 59 - Weirding Woman
            "return_to_hand": self._handle_return_to_hand,

            # Additional effect types
            "cost": self._handle_cost,
            "exchange": self._handle_exchange,
            "bypass_influence_requirment_rule": self._handle_bypass_influence_requirement_rule,

            # Leader-specific effects
            "play_spy": self._handle_play_spy,
            "ply": self._handle_ply,
            "transform_leader": self._handle_transform_leader,
            "retrigger_board_space": self._handle_retrigger_board_space,
            "contract_choice_expansion": self._handle_contract_choice_expansion,

            # Staban Tuek: conditional bonuses based on where agent was placed
            "conditional_multi": self._handle_conditional_multi,

            # Shaddam Corrino IV: restrict player actions this turn
            "restrict": self._handle_restrict,
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
        monitor_triggers = context.get("monitor_triggers", False)

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

            # Check if effect has requirements (check field)
            # If check fails, skip this effect (don't apply it)
            if "check" in effect:
                check_result = self._evaluate_checks(player_id, effect["check"])
                if not check_result.get("success"):
                    # Check failed - skip this effect silently
                    continue

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

                # Check for conditional reward triggers AFTER each effect
                if monitor_triggers:
                    trigger_results = self._check_and_trigger_conditional_rewards(
                        player_id,
                        effect,
                        context
                    )
                    if trigger_results:
                        applied_effects.extend(trigger_results.get("effects_applied", []))

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
            # Track lifetime spice harvested (for harvest contracts)
            if not hasattr(player, 'total_spice_harvested'):
                player.total_spice_harvested = 0
            player.total_spice_harvested += total_amount
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
        elif resource == "worm" or resource == "sandworm":
            # Sandworms go directly into the current Conflict, where they add
            # combat strength (+3 each) and double that player's combat rewards.
            # There is no "deploy worm" step — gaining a worm places it in the
            # conflict immediately (matching the physical game's sandworm tokens).
            if not hasattr(player, "sandworms_in_conflict"):
                player.sandworms_in_conflict = 0
            player.sandworms_in_conflict += total_amount
            # Keep the available pool defined for any legacy callers.
            if not hasattr(player, "sandworms_available"):
                player.sandworms_available = 0
            # Muad'Dib passive: gaining a sandworm triggers an intrigue draw
            self._trigger_muaddib_sandworm_passive(player_id, total_amount)
        elif resource == "intrigue":
            # Draw intrigue cards (delegate to draw handler)
            return self._handle_draw(
                player_id,
                {"type": "draw", "deck": "intrigue", "amount": total_amount},
                context
            )
        elif resource == "mentat":
            # Add mentat(s) to player
            if not hasattr(player, "mentats"):
                player.mentats = 0
            player.mentats += total_amount
        elif resource == "memory" or resource == "memories":
            # Add memory/memories (Lady Jessica mechanic)
            if not hasattr(player, "memories"):
                player.memories = 0
            player.memories += total_amount
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

        elif deck_type == "deck" or deck_type == "hand":
            # Draw from player's own deck (use DeckManager for auto-shuffle)
            # Note: "hand" is treated as "deck" since you draw INTO hand FROM deck
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
        Handle play effects: {"type": "play", "unit": "spy"|"sandworm", "amount": 1}

        For spies: Plays a spy to an observation post (requires player choice).
        For sandworms: Plays sandworms to conflict.

        Special parameters:
        - target: "any_observation_post" (default for spies)
        - allow_shared_post_if: Condition that allows placing spy on post with other players' spies
        """
        unit_type = effect.get("unit")
        amount = effect.get("amount", 0)

        if unit_type == "sandworm":
            # Place sandworm(s) directly into the current Conflict. Worms come
            # from the player's supply (not the resource pool), so this always
            # succeeds — they add +3 combat strength each and double rewards.
            player = self.state.get_player_by_id(player_id)

            if not hasattr(player, 'sandworms_in_conflict'):
                player.sandworms_in_conflict = 0
            player.sandworms_in_conflict += amount
            # Gaining a sandworm triggers Muad'Dib's passive intrigue draw.
            self._trigger_muaddib_sandworm_passive(player_id, amount)

            return {
                "success": True,
                "applied": {
                    "type": "play",
                    "unit": "sandworm",
                    "amount": amount
                }
            }

        elif unit_type == "spy":
            player = self.state.get_player_by_id(player_id)

            # Initialize spies_placed if needed
            if not hasattr(player, 'spies_placed'):
                player.spies_placed = []

            if player.spies_available < amount:
                return {
                    "success": True,
                    "applied": {"type": "play", "unit": "spy", "skipped": True,
                                "reason": f"Not enough spies (have {player.spies_available}, need {amount})"}
                }

            # Check if observation posts exist
            if not hasattr(self.game.board, 'observation_posts') or not self.game.board.observation_posts:
                return {
                    "success": False,
                    "error": "No observation posts available on board"
                }

            # Check if special condition allows sharing observation posts
            allow_shared = False
            allow_shared_condition = effect.get("allow_shared_post_if")

            if allow_shared_condition:
                condition_type = allow_shared_condition.get("type")

                if condition_type == "current_location_spied_by_self":
                    # Check if current location (from context) is being spied by this player
                    current_location = context.get("location")

                    if current_location:
                        # Find observation post that controls current location
                        for post in self.game.board.observation_posts:
                            if current_location in post.connected_locations:
                                # Check if this player has a spy on this post
                                if str(post.id) in player.spies_placed:
                                    allow_shared = True
                                break

            # Get available observation posts
            available_posts = []
            for post in self.game.board.observation_posts:
                # Check if this player already has a spy here
                if str(post.id) in player.spies_placed:
                    continue

                # Check if post is occupied by another player
                post_occupied_by_other = False
                for other_player in self.game.players:
                    if other_player.player_id != player_id:
                        if not hasattr(other_player, 'spies_placed'):
                            other_player.spies_placed = []
                        if str(post.id) in other_player.spies_placed:
                            post_occupied_by_other = True
                            break

                # Include post if:
                # 1. Not occupied by another player, OR
                # 2. Occupied by another player but allow_shared is True
                if not post_occupied_by_other or allow_shared:
                    available_posts.append({
                        "post_id": post.id,
                        "post_name": post.name,
                        "connected_locations": post.connected_locations,
                        "shared": post_occupied_by_other  # Flag to indicate this is a shared placement
                    })

            if not available_posts:
                # No posts available — skip silently so other effects still apply
                return {
                    "success": True,
                    "applied": {"type": "play", "unit": "spy", "skipped": True, "reason": "No available observation posts"}
                }

            # Human players must pick; bots auto-select first available post
            if player.is_human:
                return {
                    "success": True,
                    "choice_required": True,
                    "choice_data": {
                        "type": "spy_post",
                        "available_posts": available_posts,
                        "amount": amount
                    }
                }

            selected_post = available_posts[0]
            post_id = selected_post["post_id"]
            post_name = selected_post["post_name"]

            # Place spy on selected observation post
            player.spies_placed.append(str(post_id))
            player.spies_available -= amount

            return {
                "success": True,
                "applied": {
                    "type": "play",
                    "unit": "spy",
                    "amount": amount,
                    "post_id": post_id,
                    "post_name": post_name
                }
            }

        else:
            return {"success": False, "error": f"Play effect only supports 'spy' or 'sandworm' unit, got '{unit_type}'"}

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
        player = self.state.get_player_by_id(player_id)

        # Cannot accept if already at cap (2 active contracts)
        if player and len(getattr(player, "contracts_active", [])) >= 2:
            return {"success": True, "applied": {"type": "accept", "skipped": True}}

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
                "available_contracts": available_contracts,
                "can_skip": True,
            }
        }

    def _handle_trash(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle trash effects: {"type": "trash", "deck": ["hand", "played"]|"self", "amount": 1}

        Supports:
        - deck: "self" - Trash the card being played (from context)
        - deck: ["hand", "played"] - Trash cards from specified decks (requires choice)
        - target: "self" - Legacy format, same as deck: "self"
        """
        player = self.state.get_player_by_id(player_id)
        deck_sources = effect.get("deck")
        target = effect.get("target")
        amount = effect.get("amount", 0)

        # Handle "deck: self" or "target: self" - trash the card being played
        if deck_sources == "self" or target == "self":
            card_name = context.get("card") if context else None

            if not card_name:
                return {
                    "success": False,
                    "error": "No card context for trashing self"
                }

            # For agent effects, the card being played isn't in any deck yet
            # Just mark it as trashed and it won't be added to play area
            if not hasattr(player, 'trashed_cards'):
                player.trashed_cards = []
            player.trashed_cards.append(card_name)

            return {
                "success": True,
                "applied": {
                    "type": "trash",
                    "card": card_name,
                    "source": "self"
                }
            }

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

    def _handle_discard(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle discard effects: {"type": "discard", "deck": "hand"|"played", "amount": 2}

        Discards cards (moves to played area without triggering effects).
        Different from trash (which removes from game).
        Requires player choice of which cards to discard.
        """
        player = self.state.get_player_by_id(player_id)
        deck_source = effect.get("deck", "hand")
        amount = effect.get("amount", 0)

        # If amount is 0 or negative, nothing to discard
        if amount <= 0:
            return {
                "success": True,
                "applied": {"type": "discard", "amount": 0, "cards_discarded": []}
            }

        # Build list of available cards to discard
        available_cards = []

        if deck_source == "hand":
            available_cards = [
                {"card": card, "source": "hand"}
                for card in player.hand.cards
            ]
        elif deck_source == "played":
            available_cards = [
                {"card": card, "source": "played"}
                for card in player.played_cards_this_turn
            ]

        if len(available_cards) < amount:
            return {
                "success": False,
                "error": f"Not enough cards to discard (need {amount}, have {len(available_cards)})"
            }

        # This effect requires player choice
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "discard_card",
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

    def _handle_opponent_discard(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle opponent discard effects: {"type": "opponent_discard", "target": "all"|"choose", "amount": 1}

        Forces opponents to discard cards from their hand.
        - target "all": All opponents discard
        - target "choose": Player chooses which opponent(s) discard
        """
        target = effect.get("target", "all")
        amount = effect.get("amount", 1)

        if amount <= 0:
            return {
                "success": True,
                "applied": {"type": "opponent_discard", "amount": 0}
            }

        opponents_affected = []

        if target == "all":
            # All opponents must discard
            for other_player in self.game.players:
                if other_player.player_id == player_id:
                    continue

                # Each opponent discards from their hand
                cards_to_discard = min(amount, len(other_player.hand.cards))
                if cards_to_discard > 0:
                    opponents_affected.append({
                        "player_id": other_player.player_id,
                        "player_name": getattr(other_player, 'name', f'Player {other_player.player_id}'),
                        "cards_to_discard": cards_to_discard
                    })

            # This requires each opponent to choose which cards to discard
            # For now, return success with info about who must discard
            # Full implementation would need UI/bot logic for each opponent to choose
            return {
                "success": True,
                "applied": {
                    "type": "opponent_discard",
                    "target": "all",
                    "amount": amount,
                    "opponents_affected": opponents_affected
                },
                "note": "Each opponent must choose which cards to discard"
            }

        elif target == "choose":
            # Player chooses which opponent(s) must discard
            valid_targets = []
            for other_player in self.game.players:
                if other_player.player_id == player_id:
                    continue
                if len(other_player.hand.cards) > 0:
                    valid_targets.append({
                        "player_id": other_player.player_id,
                        "player_name": getattr(other_player, 'name', f'Player {other_player.player_id}'),
                        "hand_size": len(other_player.hand.cards)
                    })

            if not valid_targets:
                return {
                    "success": True,
                    "applied": {
                        "type": "opponent_discard",
                        "amount": 0,
                        "reason": "No opponents with cards in hand"
                    }
                }

            # Requires player choice
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "choose_opponent_discard",
                    "amount": amount,
                    "valid_targets": valid_targets
                }
            }

        return {"success": False, "error": f"Unknown target type: {target}"}

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

    def _handle_retreat(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle retreat effects: {"type": "retreat", "unit": "troop"|"sandworm", "amount": 2}

        Retreats units from conflict back to their origin:
        - Troops: Move from conflict to garrison
        - Sandworms: Remove from conflict (they die)
        """
        unit_type = effect.get("unit")
        amount = effect.get("amount", 0)

        if unit_type not in ["troop", "sandworm"]:
            return {"success": False, "error": "Retreat unit must be 'troop' or 'sandworm'"}

        player = self.state.get_player_by_id(player_id)

        if unit_type == "troop":
            # Move troops from conflict to garrison
            troops_to_retreat = min(amount, player.troops_in_conflict)
            player.troops_in_conflict -= troops_to_retreat
            player.troops_in_garrison += troops_to_retreat

            return {
                "success": True,
                "applied": {
                    "type": "retreat",
                    "unit": "troop",
                    "amount": troops_to_retreat
                }
            }

        elif unit_type == "sandworm":
            # Remove sandworms from conflict (they die/return to desert)
            worms_to_remove = min(amount, player.sandworms_in_conflict)
            player.sandworms_in_conflict -= worms_to_remove

            return {
                "success": True,
                "applied": {
                    "type": "retreat",
                    "unit": "sandworm",
                    "amount": worms_to_remove,
                    "note": "Sandworms returned to desert"
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
        "target": "agent" means the faction of the current location (from context).
        """
        player = self.state.get_player_by_id(player_id)
        target = effect.get("target")
        amount = effect.get("amount", 0)
        times = effect.get("times", 1)

        if not target:
            return {"success": False, "error": "Influence effect missing 'target' field"}

        total_influence = amount * times

        # Handle "agent" target - dynamic based on current location
        if target == "agent":
            location = context.get("location") or context.get("board_space")
            if not location:
                return {"success": False, "error": "Cannot determine current location for 'agent' target"}

            # Get faction from board space
            if hasattr(self.game, 'board') and hasattr(self.game.board, 'spaces'):
                board_space = None
                for space in self.game.board.spaces:
                    if space.id == location or space.name == location:
                        board_space = space
                        break

                if not board_space:
                    return {"success": False, "error": f"Board space '{location}' not found"}

                # Get faction from board space
                if hasattr(board_space, 'faction'):
                    target = board_space.faction.lower() if isinstance(board_space.faction, str) else board_space.faction
                else:
                    return {"success": False, "error": f"Board space '{location}' has no faction"}
            else:
                return {"success": False, "error": "Game board not available"}

        # Handle faction choice (target is "any" or a list of factions)
        if target == "any" or isinstance(target, list):
            # Player must choose faction from available options
            factions = target if isinstance(target, list) else ["fremen", "bene_gesserit", "spacing_guild", "emperor"]

            # Human players must pick; bots auto-select first faction
            if player.is_human:
                return {
                    "success": True,
                    "choice_required": True,
                    "choice_data": {
                        "type": "influence_faction",
                        "factions": factions,
                        "amount": total_influence,
                        "original_effect": effect
                    }
                }

            selected_faction = factions[0]
            target = selected_faction
            # Continue to apply influence below

        # Apply to specific faction
        # Use InfluenceManager if available (handles VP bonuses and alliances)
        if self.influence_manager:
            result = self.influence_manager.add_influence(player_id, target, total_influence)
            if not result.get("success"):
                return result

            # Check influence_reached passives for the player whose influence changed
            passive_choices = self._check_influence_reached_passives(player_id, target)

            ret = {
                "success": True,
                "applied": {
                    "type": "influence",
                    "target": target,
                    "amount": total_influence,
                    "vp_gained": result.get("vp_gained", 0),
                    "alliance_gained": result.get("alliance_gained", False)
                }
            }
            if passive_choices:
                ret["choice_required"] = True
                ret["choice_data"] = passive_choices[0]
            return ret
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

            # Check influence_reached passives (fallback path)
            passive_choices = self._check_influence_reached_passives(player_id, target)
            ret = {
                "success": True,
                "applied": {
                    "type": "influence",
                    "target": target,
                    "amount": total_influence
                }
            }
            if passive_choices:
                ret["choice_required"] = True
                ret["choice_data"] = passive_choices[0]
            return ret

    def _handle_acquire(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle acquire effects: {"type": "acquire", "card": "spice_must_flow", "amount": 1}

        Acquires a card from the market or reserve.
        Special card values:
        - "spice_must_flow": Acquire from Spice Must Flow reserve
        - "prepare_the_way": Acquire from Prepare the Way reserve
        - "reserve": Player chooses from available reserve cards
        - Specific card name: Acquire from market
        """
        player = self.state.get_player_by_id(player_id)
        card_type = effect.get("card", "")
        amount = effect.get("amount", 1)

        if card_type == "reserve":
            # Player chooses from available reserve cards
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "choose_reserve_card",
                    "amount": amount
                }
            }
        elif card_type in ["spice_must_flow", "prepare_the_way"]:
            # Acquire specific reserve card
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "acquire_reserve_card",
                    "card": card_type,
                    "amount": amount
                }
            }
        else:
            # Acquire from market (requires card selection)
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "acquire_card",
                    "card": card_type if card_type else None,
                    "amount": amount
                }
            }

    def _handle_persuasion_per_contract(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle persuasion_per_contract effects: {"type": "persuasion_per_contract", "amount": 1}

        Grants persuasion for each completed contract.
        """
        player = self.state.get_player_by_id(player_id)
        amount_per_contract = effect.get("amount", 1)

        # Count completed contracts
        contracts_completed = len(player.contracts_completed) if hasattr(player, 'contracts_completed') else 0
        total_persuasion = amount_per_contract * contracts_completed

        # Add to temporary persuasion (for reveal turn)
        if hasattr(player, 'temp_persuasion'):
            player.temp_persuasion += total_persuasion
        else:
            player.temp_persuasion = total_persuasion

        return {
            "success": True,
            "applied": {
                "type": "persuasion_per_contract",
                "contracts_completed": contracts_completed,
                "persuasion_gained": total_persuasion
            }
        }

    def _handle_control(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle control effects: {"type": "control", "location": "spice_refinery"|"current"}

        Claims control of board locations.
        Special value "current" means the location where the agent was just placed.
        """
        player = self.state.get_player_by_id(player_id)
        location = effect.get("location")

        if not location:
            return {"success": False, "error": "Control effect missing 'location' field"}

        # Handle "current" location (get from context)
        if location == "current":
            location = context.get("location") or context.get("board_space")
            if not location:
                return {"success": False, "error": "Cannot determine current location from context"}

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

    def _handle_agent_on_maker(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle agent_on_maker effects: {"type": "agent_on_maker", "amount": 1}

        This effect doesn't do anything by itself - it's a marker that indicates
        this card requires placing an agent on a Maker space.

        The actual game logic for Maker spaces is:
        - Player must place agent on a location with is_maker_space=True
        - This is validated during action generation/execution
        - When agent is placed on Maker space, player.placed_on_maker_this_turn is set

        This effect just returns success and marks the requirement was seen.
        """
        player = self.state.get_player_by_id(player_id)
        amount = effect.get("amount", 1)

        # Mark that player needs to/has placed on maker space
        # This flag would be set by action_executor when placing agent on maker space
        if not hasattr(player, 'placed_on_maker_this_turn'):
            player.placed_on_maker_this_turn = False

        return {
            "success": True,
            "applied": {
                "type": "agent_on_maker",
                "amount": amount
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

        Signet Ring triggers the player's leader signet ability.
        - Agent phase: Does nothing (just places agent)
        - Reveal phase: Resolves leader's signet_ability effects

        Args:
            player_id: Player using signet
            effect: Signet effect dict
            context: Must include 'phase' to determine behavior

        Returns:
            Result dict with effects from leader ability
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        phase = context.get("phase", "agent")

        # During agent phase, signet does nothing (agent placement handles it)
        if phase == "agent":
            return {
                "success": True,
                "effect_type": "signet",
                "effects_applied": ["Signet agent placed"]
            }

        # During reveal phase, trigger leader's signet ability
        if phase == "reveal":
            # Get player's leader
            if not hasattr(player, 'leader') or not player.leader:
                return {
                    "success": False,
                    "error": "Player has no leader"
                }

            leader = player.leader

            # Method 1: Leader has custom signet_ring() method (preferred)
            if hasattr(leader, 'signet_ring') and callable(leader.signet_ring):
                signet_result = leader.signet_ring(self.state, player_id, context)

                if not signet_result.get('success'):
                    return signet_result

                signet_effects = signet_result.get('effects', [])
                message = signet_result.get('message', '')

                if not signet_effects:
                    return {
                        "success": True,
                        "effect_type": "signet",
                        "effects_applied": [message or "No signet effects"]
                    }

                # Resolve the effects returned by signet_ring()
                result = self.resolve_effects(
                    player_id,
                    signet_effects,
                    {**context, "source": "signet_ability", "leader": getattr(leader, 'name', 'Unknown')}
                )

                if result.get("success"):
                    # Prepend the signet message to effects_applied
                    effects_applied = [message] + result.get("effects_applied", [])

                    # If there are choices, we need to return them in the singular form expected by resolve_effects
                    choices = result.get("choices_required", [])

                    # If there's exactly one choice, return it as choice_required (singular)
                    # This matches what other handlers like _handle_choice do
                    if len(choices) == 1:
                        return {
                            "success": True,
                            "applied": f"Signet ability: {message}",
                            "choice_required": True,
                            "choice_data": choices[0]
                        }
                    elif len(choices) > 1:
                        # Multiple choices - this shouldn't happen for signet but handle it
                        # Return the first one and hope for the best
                        # TODO: Better handling of multiple choices
                        return {
                            "success": True,
                            "applied": f"Signet ability: {message}",
                            "choice_required": True,
                            "choice_data": choices[0]
                        }
                    else:
                        # No choices required
                        return {
                            "success": True,
                            "effect_type": "signet",
                            "effects_applied": effects_applied
                        }
                else:
                    return result

            # Method 2: Get current signet effects (handles both old and new format, plus progression)
            signet_effects = []
            if hasattr(leader, 'get_current_signet_effects'):
                signet_effects = leader.get_current_signet_effects()
            elif hasattr(leader, 'signet_ability') and leader.signet_ability:
                # Fallback to old format
                signet_ability = leader.signet_ability
                if isinstance(signet_ability, dict) and 'effects' in signet_ability:
                    signet_effects = signet_ability['effects']
                elif hasattr(signet_ability, 'effects'):
                    signet_effects = signet_ability.effects

            if not signet_effects:
                return {
                    "success": True,
                    "effect_type": "signet",
                    "effects_applied": [f"No signet effects at level {getattr(leader, 'training_track_position', 0)}"]
                }

            # Resolve leader's signet effects
            result = self.resolve_effects(
                player_id,
                signet_effects,
                {**context, "source": "signet_ability", "leader": getattr(leader, 'name', 'Unknown')}
            )

            if result.get("success"):
                leader_name = getattr(leader, 'name', 'Unknown Leader')
                message = f"Signet ability ({leader_name})"
                effects_applied = [message] + result.get("effects_applied", [])

                # If there are choices, return them in the singular form
                choices = result.get("choices_required", [])

                if len(choices) == 1:
                    return {
                        "success": True,
                        "applied": message,
                        "choice_required": True,
                        "choice_data": choices[0]
                    }
                elif len(choices) > 1:
                    return {
                        "success": True,
                        "applied": message,
                        "choice_required": True,
                        "choice_data": choices[0]
                    }
                else:
                    return {
                        "success": True,
                        "effect_type": "signet",
                        "effects_applied": effects_applied
                    }
            else:
                return result

        # Unknown phase
        return {
            "success": False,
            "error": f"Signet effect in unknown phase: {phase}"
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

    def _handle_shield_active(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle shield_active effects: {"type": "shield_active", "value": false}

        Controls the Great Shield Wall status (same as shieldwall_deactivate but with clearer naming).
        value=false means deactivate the shield, value=true means activate it.
        """
        if not hasattr(self.game, 'shieldwall_active'):
            self.game.shieldwall_active = True

        value = effect.get("value", True)
        self.game.shieldwall_active = value

        return {
            "success": True,
            "applied": {
                "type": "shield_active",
                "value": value,
                "shield_status": "active" if value else "inactive"
            }
        }

    def _handle_manipulate(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle manipulate effects: {"type": "manipulate", "phase": "plot"}

        Manipulate allows the player to look at the top card of the intrigue deck
        and either keep it on top or put it on the bottom.

        For bots/testing: Auto-keeps on top
        TODO: For human players, show card and allow choice
        """
        player = self.state.get_player_by_id(player_id)

        if not hasattr(self.game.board, 'intrigue_deck') or not self.game.board.intrigue_deck:
            return {
                "success": False,
                "error": "Intrigue deck is empty"
            }

        # Look at top card
        top_card = self.game.board.intrigue_deck[0]

        # For bots/testing: keep on top
        # For humans: would show card and ask "Keep on top or move to bottom?"
        action = "kept_on_top"

        # Uncomment for human choice:
        # return {
        #     "success": True,
        #     "choice_required": True,
        #     "choice_data": {
        #         "type": "manipulate",
        #         "card": top_card,
        #         "options": ["keep_top", "move_bottom"]
        #     }
        # }

        return {
            "success": True,
            "applied": {
                "type": "manipulate",
                "action": action,
                "card_name": top_card.get("name", "Unknown") if isinstance(top_card, dict) else str(top_card)
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

        # Only "endgame" phase options need special gating.
        # During normal play (any non-endgame context), endgame options are
        # hidden.  During the endgame scoring pass (context phase = "endgame"),
        # only endgame options are shown.
        # Options with no "phase" field are always available in normal contexts.
        is_endgame_ctx = (context or {}).get("phase") == "endgame"

        # Evaluate each option for availability
        available_options = []

        for option in options:
            option_id = option.get("id", "unknown")
            option_phase = option.get("phase")  # None means "available always"
            checks = option.get("check", [])
            costs = option.get("cost", [])
            rewards = option.get("reward", [])

            # Phase gating: hide endgame options during normal play and
            # hide non-endgame options during endgame scoring.
            if is_endgame_ctx and option_phase != "endgame":
                continue
            if not is_endgame_ctx and option_phase == "endgame":
                continue

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

        # If no options remain after phase filtering, the card has nothing to
        # offer in this phase context — resolve silently with no effect.
        if not available_options:
            return {
                "success": True,
                "applied": {"type": "choice", "skipped": True,
                            "reason": f"No options for phase '{ctx_phase}'"}
            }

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

        Supports check types:
        - influence: Requires specific faction influence level
        - influence_threshold: Checks total influence across factions
        - council_seat: Requires high council seat
        - agent_on: Requires agent on specific location
        - bought: Requires specific card was bought this turn/round
        - buy_imperium: Checks if imperium card was bought (for triggers)
        - harvest: Requires harvest count (spice accumulated)
        - contracts_completed: Requires number of completed contracts
        - spies_placed: Requires number of spies placed on board
        - cards_in_play: Requires number of cards in play with specific faction
        - units_in_conflict: Requires number of units (troops + sandworms) in conflict
        - maker_hook: Requires player has the Maker hook token
        - agent_on_maker: Requires agent placed on Maker space (this_turn flag)
        - fremen_bond: Requires another Fremen faction card in play
        - faction_bond: Requires another card from specific faction in play
        - discarded_faction_card: Requires discarding a card from specific faction this turn
        - recalled_spy: Requires recalling a spy this turn
        - acquired_card: Requires acquiring specific card this turn
        - always: Always passes (unconditional)

        Returns success=True only if ALL checks pass.
        """
        player = self.state.get_player_by_id(player_id)

        for check in checks:
            check_type = check.get("type")

            if check_type == "influence":
                # Check faction influence level
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

            elif check_type == "influence_threshold":
                # Check total influence across all factions
                amount = check.get("amount", 0)
                total_influence = (
                    player.fremen_influence +
                    player.bene_gesserit_influence +
                    player.spacing_guild_influence +
                    player.emperor_influence
                )

                if total_influence < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} total influence (have {total_influence})"
                    }

            elif check_type == "council_seat":
                # Check high council seat ownership
                value = check.get("value", False)
                if player.has_high_council_sit != value:
                    return {
                        "success": False,
                        "error": "Requires council seat"
                    }

            elif check_type == "agent_on":
                # Check if agent is on specific location
                location = check.get("location")
                if not location:
                    continue

                # Check if player has agent at this location
                has_agent = location in player.agents_placed

                if not has_agent:
                    return {
                        "success": False,
                        "error": f"Requires agent on {location}"
                    }

            elif check_type == "bought":
                # Check if specific card was bought (acquired) this turn
                card_name = check.get("card")
                if not card_name:
                    continue

                # TODO: Track cards bought this turn
                # For now, we'll check if card is in player's deck/discard
                # This is approximate - full implementation needs turn tracking
                has_card = False
                for card in player.deck.cards + player.discard_pile.cards:
                    if card.name == card_name:
                        has_card = True
                        break

                if not has_card:
                    return {
                        "success": False,
                        "error": f"Requires buying {card_name}"
                    }

            elif check_type == "buy_imperium":
                # Trigger condition: check if any imperium card was bought
                # This is for conditional effects (e.g., "when you buy a card")
                # For now, always return True as this is a trigger, not a requirement
                # Full implementation would track this in action_executor
                continue

            elif check_type == "harvest":
                # Check spice harvest count
                amount = check.get("amount", 0)

                # Spice on hand represents harvested spice
                if player.spice < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} spice harvested (have {player.spice})"
                    }

            elif check_type == "contracts_completed":
                # Check number of completed contracts
                amount = check.get("amount", 0)

                # Count completed contracts
                completed_count = len(player.contracts_completed) if hasattr(player, 'contracts_completed') else 0

                if completed_count < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} completed contracts (have {completed_count})"
                    }

            elif check_type == "spies_placed":
                # Check number of spies placed on board
                amount = check.get("amount", 0)
                spies_count = len(player.spies_placed) if hasattr(player, 'spies_placed') else 0

                if spies_count < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} spies placed (have {spies_count})"
                    }

            elif check_type == "cards_in_play":
                # Check number of cards in play with specific faction
                faction = check.get("faction")
                amount = check.get("amount", 1)

                # Count cards in played_cards_this_turn with matching faction
                matching_cards = 0
                if hasattr(player, 'played_cards_this_turn'):
                    for card in player.played_cards_this_turn:
                        if hasattr(card, 'faction') and card.faction and faction:
                            # Normalize faction names for comparison
                            card_faction = card.faction.lower().replace(" ", "_")
                            check_faction = faction.lower().replace(" ", "_")
                            if card_faction == check_faction:
                                matching_cards += 1

                if matching_cards < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} {faction} cards in play (have {matching_cards})"
                    }

            elif check_type == "units_in_conflict":
                # Check total units (troops + sandworms) in conflict
                amount = check.get("amount", 0)

                # Count troops and sandworms in conflict
                troops = player.troops_in_conflict if hasattr(player, 'troops_in_conflict') else 0
                sandworms = player.sandworms_in_conflict if hasattr(player, 'sandworms_in_conflict') else 0
                total_units = troops + sandworms

                if total_units < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} units in conflict (have {total_units})"
                    }

            elif check_type == "maker_hook":
                # Check if player has the Maker hook (special token from Maker spaces)
                has_maker_hook = getattr(player, 'has_maker_hook', False)

                if not has_maker_hook:
                    return {
                        "success": False,
                        "error": "Requires Maker hook"
                    }

            elif check_type == "agent_on_maker":
                # Check if player placed agent on a Maker space this turn
                this_turn = check.get("this_turn", False)

                # Track if player visited a maker space
                placed_on_maker = getattr(player, 'placed_on_maker_this_turn', False)

                if this_turn and not placed_on_maker:
                    return {
                        "success": False,
                        "error": "Requires placing agent on Maker space this turn"
                    }

            elif check_type == "fremen_bond":
                # Check if player has other Fremen faction cards in play
                # Need at least one OTHER Fremen card in played_cards_this_turn
                fremen_cards_in_play = 0

                if hasattr(player, 'played_cards_this_turn'):
                    for card in player.played_cards_this_turn:
                        if hasattr(card, 'faction') and card.faction:
                            # Handle both string and list faction formats
                            factions = card.faction if isinstance(card.faction, list) else [card.faction]
                            for faction in factions:
                                if faction.lower() == "fremen":
                                    fremen_cards_in_play += 1
                                    break

                # Need at least 2 Fremen cards total (current card + 1 other)
                if fremen_cards_in_play < 2:
                    return {
                        "success": False,
                        "error": "Requires another Fremen card in play"
                    }

            elif check_type == "faction_bond":
                # Generic faction bond check (checks for any faction cards in play)
                target_faction = check.get("faction", "").lower().replace(" ", "_")
                faction_cards_in_play = 0

                if hasattr(player, 'played_cards_this_turn'):
                    for card in player.played_cards_this_turn:
                        if hasattr(card, 'faction') and card.faction:
                            # Handle both string and list faction formats
                            factions = card.faction if isinstance(card.faction, list) else [card.faction]
                            for faction in factions:
                                if faction.lower().replace(" ", "_") == target_faction:
                                    faction_cards_in_play += 1
                                    break

                # Need at least 2 cards of target faction total (current card + 1 other)
                if faction_cards_in_play < 2:
                    return {
                        "success": False,
                        "error": f"Requires another {target_faction} card in play"
                    }

            elif check_type == "discarded_faction_card":
                # Check if player discarded a card from specific faction this turn
                faction = check.get("faction", "").lower().replace(" ", "_")

                # Track discarded cards this turn
                discarded_faction_card = False
                if hasattr(player, 'discarded_cards_this_turn'):
                    for card in player.discarded_cards_this_turn:
                        if hasattr(card, 'faction') and card.faction:
                            # Handle both string and list faction formats
                            factions = card.faction if isinstance(card.faction, list) else [card.faction]
                            for card_faction in factions:
                                if card_faction.lower().replace(" ", "_") == faction:
                                    discarded_faction_card = True
                                    break
                        if discarded_faction_card:
                            break

                if not discarded_faction_card:
                    return {
                        "success": False,
                        "error": f"Requires discarding a {faction} card"
                    }

            elif check_type == "recalled_spy":
                # Check if player recalled a spy this turn
                this_turn = check.get("this_turn", False)
                recalled_spy = getattr(player, 'recalled_spy_this_turn', False)

                if this_turn and not recalled_spy:
                    return {
                        "success": False,
                        "error": "Requires recalling a spy this turn"
                    }

            elif check_type == "acquired_card":
                # Check if specific card was acquired this turn
                card_name = check.get("card", "").lower()
                this_turn = check.get("this_turn", False)

                # Track acquired cards this turn
                acquired_card = False
                if this_turn and hasattr(player, 'acquired_cards_this_turn'):
                    for card in player.acquired_cards_this_turn:
                        if hasattr(card, 'name') and card.name.lower().replace(" ", "_") == card_name:
                            acquired_card = True
                            break
                        # Also check by card ID for reserve cards
                        if hasattr(card, 'id') and card.id.lower().replace(" ", "_") == card_name:
                            acquired_card = True
                            break

                if not acquired_card:
                    return {
                        "success": False,
                        "error": f"Requires acquiring {card_name} this turn"
                    }

            elif check_type == "alliance":
                # Check if player has alliance with faction
                faction = check.get("faction", "").lower().replace(" ", "_")
                has_alliance = False

                if hasattr(player, 'alliances'):
                    has_alliance = faction in player.alliances

                if not has_alliance:
                    return {
                        "success": False,
                        "error": f"Requires alliance with {faction}"
                    }

            elif check_type == "cards_in_deck":
                # Check if deck has at least N cards
                amount = check.get("amount", 0)

                deck_count = len(player.deck.cards) if hasattr(player, 'deck') else 0

                if deck_count < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} cards in deck (have {deck_count})"
                    }

            elif check_type == "swordmaster":
                # Check if player has a Swordmaster
                value = check.get("value", True)
                has_swordmaster = getattr(player, 'has_swordmaster', False)

                if has_swordmaster != value:
                    return {
                        "success": False,
                        "error": "Requires Swordmaster" if value else "Must not have Swordmaster"
                    }

            elif check_type == "recalled_spy":
                # Check if player recalled a spy this turn
                this_turn = check.get("this_turn", True)
                recalled_spy = False

                if this_turn and hasattr(player, 'recalled_spy_this_turn'):
                    recalled_spy = player.recalled_spy_this_turn

                if not recalled_spy:
                    return {
                        "success": False,
                        "error": "Requires recalling a spy this turn"
                    }

            elif check_type == "contracts_completed":
                # Check if player has completed at least N contracts
                amount = check.get("amount", 0)
                contracts_count = len(player.contracts_completed) if hasattr(player, 'contracts_completed') else 0

                if contracts_count < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} completed contracts (have {contracts_count})"
                    }

            elif check_type == "board_space_faction":
                # Check if agent was placed on a board space of specific faction
                faction = check.get("faction", "").lower().replace(" ", "_")
                board_space_id = context.get("board_space_id") if context else None

                if not board_space_id:
                    return {
                        "success": False,
                        "error": "No board space context available"
                    }

                # Get board space from game state
                board_space = None
                if hasattr(self.game, 'board') and hasattr(self.game.board, 'spaces'):
                    for space in self.game.board.spaces:
                        if str(space.id) == str(board_space_id):
                            board_space = space
                            break

                if not board_space:
                    return {
                        "success": False,
                        "error": f"Board space {board_space_id} not found"
                    }

                # Check if board space has the required faction
                space_faction = getattr(board_space, 'faction', '').lower().replace(" ", "_")

                if space_faction != faction:
                    return {
                        "success": False,
                        "error": f"Board space is not {faction} (is {space_faction})"
                    }

            elif check_type == "sent_an_agent_on":
                # Generic check: player sent agent to specific target(s) this turn
                # target can be: "maker", "faction", specific faction names, etc.
                targets = check.get("target", [])
                if isinstance(targets, str):
                    targets = [targets]

                agent_sent = False
                if hasattr(player, 'agents_sent_this_turn'):
                    for board_space_id in player.agents_sent_this_turn:
                        # Get board space from game state
                        if hasattr(self.game, 'board') and hasattr(self.game.board, 'spaces'):
                            for space in self.game.board.spaces:
                                if str(space.id) == str(board_space_id):
                                    # Check against each target type
                                    for target in targets:
                                        target_lower = target.lower().replace(" ", "_")

                                        if target_lower == "maker":
                                            # Check if this is a Maker space
                                            space_type = getattr(space, 'type', '').lower()
                                            if space_type == "maker":
                                                agent_sent = True
                                                break

                                        elif target_lower == "faction":
                                            # Check if this space has any faction
                                            if hasattr(space, 'faction') and space.faction:
                                                agent_sent = True
                                                break

                                        else:
                                            # Check if space faction matches target
                                            space_faction = getattr(space, 'faction', '').lower().replace(" ", "_")
                                            if space_faction == target_lower:
                                                agent_sent = True
                                                break

                                    if agent_sent:
                                        break
                        if agent_sent:
                            break

                if not agent_sent:
                    target_str = ", ".join(targets) if targets else "specified target"
                    return {
                        "success": False,
                        "error": f"Requires sending agent to {target_str} board space this turn"
                    }

            elif check_type == "spying":
                # Check if player has spy on observation post for specific board space type
                # Standardized check name for consistency
                board_space_type = check.get("board_space_type", "").lower()

                spying_on_type = False
                if hasattr(player, 'spies_placed'):
                    for observation_post_id in player.spies_placed:
                        # Get observation post from game state
                        if hasattr(self.game, 'board') and hasattr(self.game.board, 'observation_posts'):
                            for observation_post in self.game.board.observation_posts:
                                if str(observation_post.id) == str(observation_post_id):
                                    # Check if this observation post watches board spaces of this type
                                    post_type = getattr(observation_post, 'watches_type', '').lower()
                                    if post_type == board_space_type:
                                        spying_on_type = True
                                        break
                        if spying_on_type:
                            break

                if not spying_on_type:
                    return {
                        "success": False,
                        "error": f"Requires spying on {board_space_type} board space"
                    }

            elif check_type == "other_faction_card_in_play":
                # Check if player has another card of specific faction in play (revealed)
                faction = check.get("faction", "").lower().replace(" ", "_")

                has_other_faction_card = False
                current_card_name = context.get("card") if context else None

                if hasattr(player, 'revealed_cards_this_turn'):
                    for card in player.revealed_cards_this_turn:
                        # Skip the current card
                        if current_card_name and hasattr(card, 'name') and card.name == current_card_name:
                            continue

                        if hasattr(card, 'faction'):
                            card_faction = card.faction
                            # Handle both string and list faction
                            if isinstance(card_faction, str):
                                if card_faction.lower().replace(" ", "_") == faction:
                                    has_other_faction_card = True
                                    break
                            elif isinstance(card_faction, list):
                                for f in card_faction:
                                    if f.lower().replace(" ", "_") == faction:
                                        has_other_faction_card = True
                                        break
                            if has_other_faction_card:
                                break

                if not has_other_faction_card:
                    return {
                        "success": False,
                        "error": f"Requires another {faction} card in play"
                    }

            elif check_type == "spies_on_board":
                # Check if player has at least N spies on board
                amount = check.get("amount", 2)
                spies_count = len(player.spies_placed) if hasattr(player, 'spies_placed') else 0

                if spies_count < amount:
                    return {
                        "success": False,
                        "error": f"Requires {amount} spies on board (have {spies_count})"
                    }

            elif check_type == "flip_conflict":
                # Check if the player has seen a conflict with a matching tag resolved.
                # Used by endgame intrigue cards (Crysknife, Desert Mouse, Ornithopter).
                # tag is a list like ["crysknife", "?"] — first element is the tag name,
                # "?" means wildcard/any additional constraint (ignored for now).
                # Data files use underscores; conflict cards use hyphens — normalise both.
                tags = check.get("tag", [])
                tag_name = tags[0] if tags else ""
                required_count = check.get("amount", 1)
                tag_norm = tag_name.lower().replace("_", "-")

                resolved = getattr(self.game.board, "resolved_conflicts", [])
                matched = sum(
                    1 for c in resolved
                    if getattr(c, "tag", "").lower().replace("_", "-") == tag_norm
                )
                if matched < required_count:
                    return {
                        "success": False,
                        "error": f"Requires {required_count} resolved '{tag_norm}' conflict(s) (found {matched})"
                    }

            elif check_type == "always":
                # Always passes
                continue

            else:
                # Unknown check type - log warning but don't fail
                # This allows game to continue even with unimplemented checks
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
            # Execute card trashing.
            # NOTE: card_info["card"] may be a live ImperiumCard object (from bot path)
            # OR a plain dict (when serialised via _make_choice_json_safe for the human).
            # We always resolve to the live card via player collection lookup.
            available_cards = choice_data.get("available_cards", [])
            player = self.state.get_player_by_id(player_id)

            # Find the selected card_info entry
            selected_card_info = None
            for card_info in available_cards:
                card_data = card_info.get("card", card_info)
                cid = card_data.id if hasattr(card_data, "id") else card_data.get("id", "")
                if str(cid) == str(selected_option_id):
                    selected_card_info = card_info
                    break

            if not selected_card_info:
                return {"success": False, "error": "Invalid card selection"}

            card_data = selected_card_info.get("card", selected_card_info)
            source = selected_card_info.get("source", "hand")
            card_id = card_data.id if hasattr(card_data, "id") else card_data.get("id", "")

            # Find and remove the live card from the appropriate collection
            live_card = None
            if source == "hand":
                live_card = next((c for c in player.hand.cards if str(c.id) == str(card_id)), None)
                if live_card:
                    player.hand.remove(live_card)
            elif source == "played":
                live_card = next((c for c in player.played_cards_this_turn if str(c.id) == str(card_id)), None)
                if live_card:
                    player.played_cards_this_turn.remove(live_card)
            elif source == "intrigue":
                live_card = next((c for c in player.intrigue_cards if str(c.id) == str(card_id)), None)
                if live_card:
                    player.intrigue_cards.remove(live_card)
            elif source == "discard":
                live_card = next((c for c in player.discard_pile.cards if str(c.id) == str(card_id)), None)
                if live_card:
                    player.discard_pile.remove(live_card)

            if live_card is None:
                return {"success": False, "error": f"Card {card_id} not found in {source}"}

            # Add to trash pile
            if hasattr(self.game, 'trash_pile'):
                self.game.trash_pile.append(live_card)

            return {
                "success": True,
                "applied": {
                    "type": "trash",
                    "card_trashed": live_card.name,
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
            # Execute contract acceptance.
            # available_contracts may contain live ContractCard objects (bot path)
            # or serialized dicts (human path via _make_choice_json_safe).
            # In either case, look up the live contract from the board.
            available_contracts = choice_data.get("available_contracts", [])
            player = self.state.get_player_by_id(player_id)

            # Allow skipping contract acceptance
            if str(selected_option_id) in ("skip", "none", ""):
                return {"success": True, "applied": {"type": "accept", "skipped": True}}

            # Enforce 2-contract cap
            if len(getattr(player, "contracts_active", [])) >= 2:
                return {"success": True, "applied": {"type": "accept", "skipped": True}}

            # Determine the selected contract ID
            selected_cid = None
            for c in available_contracts:
                c_id = c.id if hasattr(c, "id") else c.get("id", "")
                if str(c_id) == str(selected_option_id):
                    selected_cid = str(c_id)
                    break

            if not selected_cid:
                return {"success": False, "error": "Contract not found"}

            # Resolve to the live contract object on the board
            contract = next(
                (c for c in self.game.board.contract_row if str(c.id) == selected_cid),
                None
            )
            if not contract:
                return {"success": False, "error": "Contract not in row"}

            # Add to player's active contracts
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

        elif choice_type == "spy_post":
            # Execute spy placement on chosen observation post
            post_id = selected_option_id
            player = self.state.get_player_by_id(player_id)
            amount = choice_data.get("amount", 1)

            if player.spies_available < amount:
                return {"success": False, "error": "No spies available"}

            if post_id in player.spies_placed:
                return {"success": False, "error": "Already have spy at that post"}

            # Find post name for display
            post_name = post_id
            for post_info in choice_data.get("available_posts", []):
                if str(post_info["post_id"]) == str(post_id):
                    post_name = post_info.get("post_name", post_id)
                    break

            player.spies_available -= amount
            player.spies_placed.append(str(post_id))

            return {
                "success": True,
                "applied": {
                    "type": "play",
                    "unit": "spy",
                    "amount": amount,
                    "post_id": post_id,
                    "post_name": post_name
                }
            }

        elif choice_type == "influence_faction":
            # Apply influence to the chosen faction
            faction = selected_option_id  # e.g. "fremen", "bene_gesserit", etc.
            player = self.state.get_player_by_id(player_id)
            total_influence = choice_data.get("amount", 1)

            valid_factions = choice_data.get("factions", ["fremen", "bene_gesserit", "spacing_guild", "emperor"])
            if faction not in valid_factions:
                return {"success": False, "error": f"Invalid faction choice: {faction}"}

            if self.influence_manager:
                result = self.influence_manager.add_influence(player_id, faction, total_influence)
                if not result.get("success"):
                    return result
                return {
                    "success": True,
                    "applied": {
                        "type": "influence",
                        "target": faction,
                        "amount": total_influence,
                        "vp_gained": result.get("vp_gained", 0),
                        "alliance_gained": result.get("alliance_gained", False)
                    }
                }
            else:
                if faction == "fremen":
                    player.fremen_influence += total_influence
                elif faction == "bene_gesserit":
                    player.bene_gesserit_influence += total_influence
                elif faction == "spacing_guild":
                    player.spacing_guild_influence += total_influence
                elif faction == "emperor":
                    player.emperor_influence += total_influence
                else:
                    return {"success": False, "error": f"Unknown faction: {faction}"}

                return {
                    "success": True,
                    "applied": {
                        "type": "influence",
                        "target": faction,
                        "amount": total_influence
                    }
                }

        elif choice_type == "trash_to_acquire":
            # Trash chosen card from hand and unlock reserve acquisition
            card_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            card_to_trash = None
            for c in player.hand.cards[:]:
                if str(c.id) == str(card_id):
                    card_to_trash = c
                    break

            if not card_to_trash:
                return {"success": False, "error": f"Card {card_id} not found in hand"}

            player.hand.cards.remove(card_to_trash)

            if not hasattr(player, 'trashed_cards'):
                player.trashed_cards = []
            player.trashed_cards.append(card_to_trash.name if hasattr(card_to_trash, 'name') else str(card_to_trash))

            if not hasattr(player, 'can_acquire_from_reserves'):
                player.can_acquire_from_reserves = False
            player.can_acquire_from_reserves = True

            return {
                "success": True,
                "applied": {
                    "type": "trash_to_acquire",
                    "card_trashed": card_to_trash.name if hasattr(card_to_trash, 'name') else str(card_to_trash)
                }
            }

        elif choice_type == "discard_card":
            # Move selected card from its source pile to the discard pile.
            # card_info["card"] may be a live object or a serialized dict.
            card_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            available = choice_data.get("available_cards", [])
            selected = None
            for ci in available:
                card_data = ci.get("card", ci)
                cid = card_data.id if hasattr(card_data, "id") else card_data.get("id", "")
                if str(cid) == str(card_id):
                    selected = ci
                    break

            if not selected:
                return {"success": False, "error": f"Card {card_id} not available to discard"}

            card_data = selected.get("card", selected)
            source = selected.get("source", "hand")
            cid = card_data.id if hasattr(card_data, "id") else card_data.get("id", "")

            # Find and remove the live card
            live_card = None
            if source == "hand":
                live_card = next((c for c in player.hand.cards if str(c.id) == str(cid)), None)
                if live_card:
                    player.hand.remove(live_card)
            elif source == "played":
                live_card = next((c for c in player.played_cards_this_turn if str(c.id) == str(cid)), None)
                if live_card:
                    player.played_cards_this_turn.remove(live_card)
            else:
                return {"success": False, "error": f"Unsupported discard source: {source}"}

            if live_card is None:
                return {"success": False, "error": f"Card {cid} not found in {source}"}

            player.discard_pile.add_card(live_card)

            return {
                "success": True,
                "applied": {
                    "type": "discard",
                    "card_discarded": live_card.name,
                    "from_source": source
                }
            }

        elif choice_type == "choose_opponent_discard":
            # Selected option is the target opponent's player_id.
            # Force the target to discard `amount` cards (random pick from hand).
            target_id = selected_option_id
            amount = choice_data.get("amount", 1)

            target = self.state.get_player_by_id(target_id)
            if not target:
                return {"success": False, "error": "Target player not found"}

            n = min(amount, len(target.hand.cards))
            discarded = []
            for _ in range(n):
                if not target.hand.cards:
                    break
                card = random.choice(target.hand.cards)
                target.hand.cards.remove(card)
                target.discard_pile.add_card(card)
                discarded.append(card.name)

            return {
                "success": True,
                "applied": {
                    "type": "opponent_discard",
                    "target": getattr(target, 'name', target_id),
                    "amount": len(discarded),
                    "cards_discarded": discarded
                }
            }

        elif choice_type == "choose_reserve_card":
            # Player picks which reserve pile to acquire from (free, no persuasion cost)
            pile_id = selected_option_id  # "prepare_the_way" or "spice_must_flow"
            player = self.state.get_player_by_id(player_id)
            amount = choice_data.get("amount", 1)

            if pile_id == "prepare_the_way":
                pile = self.game.board.reserve_prepare_the_way
            elif pile_id == "spice_must_flow":
                pile = self.game.board.reserve_spice_must_flow
            else:
                return {"success": False, "error": f"Unknown reserve pile: {pile_id}"}

            if not pile:
                return {"success": False, "error": f"Reserve pile {pile_id} is empty"}

            acquired = []
            for _ in range(min(amount, len(pile))):
                if not pile:
                    break
                card = pile.pop(0)
                player.discard_pile.add_card(card)
                acquired.append(card.name)

            return {
                "success": True,
                "applied": {
                    "type": "acquire",
                    "source": pile_id,
                    "cards_acquired": acquired
                }
            }

        elif choice_type == "acquire_reserve_card":
            # Free acquisition from a specific reserve pile
            pile_id = choice_data.get("card", "")  # set at choice creation
            player = self.state.get_player_by_id(player_id)
            amount = choice_data.get("amount", 1)

            if pile_id == "prepare_the_way":
                pile = self.game.board.reserve_prepare_the_way
            elif pile_id == "spice_must_flow":
                pile = self.game.board.reserve_spice_must_flow
            else:
                return {"success": False, "error": f"Unknown reserve pile: {pile_id}"}

            if not pile:
                return {"success": False, "error": f"Reserve pile {pile_id} is empty"}

            acquired = []
            for _ in range(min(amount, len(pile))):
                if not pile:
                    break
                card = pile.pop(0)
                player.discard_pile.add_card(card)
                acquired.append(card.name)

            return {
                "success": True,
                "applied": {
                    "type": "acquire",
                    "source": pile_id,
                    "cards_acquired": acquired
                }
            }

        elif choice_type == "play_spy_on_space":
            # Lady Margot Fenring's signet — place a spy directly on a board space
            space_id = selected_option_id
            player = self.state.get_player_by_id(player_id)
            amount = choice_data.get("amount", 1)

            # Validate the space is eligible (avoid double-placement)
            eligible_ids = [str(e["space_id"]) for e in choice_data.get("eligible_spaces", [])]
            if str(space_id) not in eligible_ids:
                return {"success": False, "error": f"Space {space_id} not eligible for spy placement"}

            if player.spies_available < amount:
                return {"success": False, "error": "No spies available"}

            player.spies_available -= amount
            player.spies_placed.append(str(space_id))

            # Find space name for the log
            space_name = space_id
            for e in choice_data.get("eligible_spaces", []):
                if str(e["space_id"]) == str(space_id):
                    space_name = e["space_name"]
                    break

            return {
                "success": True,
                "applied": {
                    "type": "ply",
                    "agent": "spy",
                    "amount": amount,
                    "space_id": space_id,
                    "space_name": space_name
                }
            }

        elif choice_type == "acquire_card":
            # Free acquisition from imperium row — selected_option_id is the card id
            card_id = selected_option_id
            player = self.state.get_player_by_id(player_id)

            target_card = None
            for c in self.game.board.imperium_row:
                if str(c.id) == str(card_id):
                    target_card = c
                    break

            if not target_card:
                return {"success": False, "error": f"Card {card_id} not in imperium row"}

            self.game.board.imperium_row.remove(target_card)
            player.discard_pile.add_card(target_card)

            # Refill row
            if hasattr(self.game.board, 'refill_imperium_row'):
                self.game.board.refill_imperium_row()

            # Track acquisition (for contracts that check acquisitions this turn)
            if not hasattr(player, 'acquired_cards_this_turn'):
                player.acquired_cards_this_turn = []
            player.acquired_cards_this_turn.append(target_card)

            return {
                "success": True,
                "applied": {
                    "type": "acquire",
                    "source": "imperium_row",
                    "card_acquired": target_card.name
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

    # ==================== INTRIGUE-SPECIFIC EFFECT HANDLERS ====================

    def _handle_action(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle action effect (intrigue cards with cost/reward pattern).

        Format:
        {
            "type": "action",
            "phase": "plot" | "combat" | "endgame",
            "cost": [effect objects],
            "reward": [effect objects]
        }

        Example: Buy Access - Pay 5 solari to gain 2 influence
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Check if we're in the correct phase
        phase = effect.get("phase")
        current_phase = context.get("phase")

        # Phase validation (if phase is specified)
        # Note: This is approximate - real validation should check GamePhase enum
        if phase and current_phase != phase:
            return {
                "success": False,
                "error": f"Action can only be played during {phase} phase"
            }

        # Pay cost
        cost = effect.get("cost", [])
        if cost:
            # For now, use simple cost deduction
            # TODO: Use effect resolver to handle complex costs
            for cost_effect in cost:
                if cost_effect.get("type") == "resource":
                    resource = cost_effect.get("resource")
                    amount = cost_effect.get("amount", 0)

                    if resource == "solari":
                        if player.solari < amount:
                            return {"success": False, "error": f"Need {amount} solari"}
                        player.solari -= amount
                    elif resource == "spice":
                        if player.spice < amount:
                            return {"success": False, "error": f"Need {amount} spice"}
                        player.spice -= amount
                    elif resource == "water":
                        if player.water < amount:
                            return {"success": False, "error": f"Need {amount} water"}
                        player.water -= amount

        # Apply reward
        reward = effect.get("reward", [])
        if reward:
            reward_result = self.resolve_effects(player_id, reward, context)
            if not reward_result["success"]:
                return reward_result

        return {
            "success": True,
            "effect_type": "action",
            "applied": [f"Action effect resolved"],
            "cost_paid": cost,
            "reward_gained": reward
        }

    def _handle_conditional_reward(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle conditional reward effect (intrigue cards with trigger conditions).

        Format:
        {
            "type": "conditional_reward",
            "phase": "plot" | "combat" | "endgame",
            "condition": {
                "type": "buy_imperium" | "contracts_completed" | "agent_on" | etc.,
                "target": "any" | specific card/faction/location,
                "amount": number (optional threshold)
            },
            "reward": [effect objects]
        }

        Example: Call to Arms - When you buy an imperium card, gain 1 troop

        This registers the conditional reward in active tracking.
        When matching conditions are met during effect resolution,
        _check_and_trigger_conditional_rewards() will apply the reward.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        condition = effect.get("condition", {})
        condition_type = condition.get("type")
        reward = effect.get("reward", [])
        card_name = context.get("card", "Unknown Card")

        # Register this conditional reward for the player
        if player_id not in self.active_conditional_rewards:
            self.active_conditional_rewards[player_id] = []

        self.active_conditional_rewards[player_id].append({
            "condition": condition,
            "reward": reward,
            "card_name": card_name,
            "phase": effect.get("phase")
        })

        return {
            "success": True,
            "effect_type": "conditional_reward",
            "applied": [f"Conditional reward active: {condition_type} (from {card_name})"],
            "condition": condition,
            "reward": reward
        }

    def _handle_endgame_condition(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle end game condition effect (VP bonuses at game end).

        Evaluated immediately when called — call at game end for each player.
        Condition types:
          - contracts_completed: len(player.contracts_completed) >= amount
          - spice_must_flow_tokens: count of "The Spice Must Flow" cards in
            the player's entire deck (deck + hand + discard + played)
          - influence: any single faction influence >= amount
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        condition = effect.get("condition", {})
        ctype = condition.get("type", "")
        amount = condition.get("amount", 1)
        target = condition.get("target", "")

        condition_met = False

        if ctype == "contracts_completed":
            completed = len(getattr(player, "contracts_completed", []))
            condition_met = completed >= amount

        elif ctype == "spice_must_flow_tokens":
            # Count all "The Spice Must Flow" cards across the player's full deck
            smf_count = 0
            all_piles = [
                getattr(player.deck, "cards", []),
                getattr(player.hand, "cards", []),
                getattr(player.discard_pile, "cards", []),
                getattr(player, "played_cards_this_turn", []),
                getattr(player, "acquired_cards_this_turn", []),
            ]
            for pile in all_piles:
                for card in pile:
                    if getattr(card, "name", "") == "The Spice Must Flow":
                        smf_count += 1
            condition_met = smf_count >= amount

        elif ctype == "influence":
            if target == "any":
                # Any faction at the required level
                condition_met = any(
                    getattr(player, f"{faction}_influence", 0) >= amount
                    for faction in ["fremen", "bene_gesserit", "spacing_guild", "emperor"]
                )
            else:
                condition_met = getattr(player, f"{target}_influence", 0) >= amount

        if not condition_met:
            return {
                "success": True,
                "effect_type": "endgame_condition",
                "applied": [],
                "condition_met": False,
            }

        # Condition met — apply the reward
        reward = effect.get("reward", [])
        reward_result = self.resolve_effects(player_id, reward, context)
        applied = reward_result.get("effects_applied", [f"endgame reward: {reward}"])

        return {
            "success": True,
            "effect_type": "endgame_condition",
            "condition_met": True,
            "applied": applied,
        }

    def _handle_conditional_multi(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Staban Tuek's signet: offer conditional optional bonuses based on where
        the agent was placed.

        Format:
        {
            "type": "conditional_multi",
            "options": [
                {
                    "id": "green_space_bonus",
                    "check": [{"type": "agent_placed_on", "space_type": "green"}],
                    "cost": [...],
                    "reward": [...],
                    "description": "..."
                },
                ...
            ]
        }

        Each option is only available if its check passes for the current
        placement location (passed in context["placement_location"]).
        Returns a `choice` with only the eligible options so the player can
        decide whether to take any of them.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        placement_location = context.get("placement_location")
        options = effect.get("options", [])

        # Filter to options whose checks pass
        eligible = []
        for opt in options:
            checks = opt.get("check", [])
            if self._evaluate_conditional_multi_checks(checks, placement_location):
                eligible.append(opt)

        if not eligible:
            return {
                "success": True,
                "effect_type": "conditional_multi",
                "applied": ["No conditional bonuses available for this space"],
            }

        # Build a choice so the player picks which (if any) bonus to take
        choice_options = []
        for opt in eligible:
            choice_options.append({
                "id": opt.get("id", "option"),
                "description": opt.get("description", ""),
                "cost": opt.get("cost", []),
                "reward": opt.get("reward", []),
            })
        # Add a "none" option so it's optional
        choice_options.append({"id": "none", "description": "No bonus"})

        return {
            "success": True,
            "effect_type": "conditional_multi",
            "applied": [],
            "choice_required": True,
            "choice_data": {
                "type": "conditional_multi_choice",
                "options": choice_options,
                "player_id": player_id,
            },
        }

    def _evaluate_conditional_multi_checks(
        self, checks: list, placement_location
    ) -> bool:
        """Check if a conditional_multi option's checks pass for this placement."""
        if not checks:
            return True
        for check in checks:
            ctype = check.get("type")
            if ctype == "agent_placed_on":
                space_type = check.get("space_type", "")
                if placement_location is None:
                    return False
                if space_type == "green":
                    # Green = neutral spaces (no faction affiliation)
                    faction = getattr(placement_location, "faction", None)
                    if faction:
                        return False
                elif space_type == "faction":
                    faction = getattr(placement_location, "faction", None)
                    if not faction:
                        return False
            # Unknown check type — pass through
        return True

    # ==================== LEADER PASSIVE / RESTRICTION HANDLERS ====================

    def _handle_restrict(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Shaddam Corrino IV signet — restrict player actions this turn.

        {"type": "restrict", "restriction": "no_troop_deployment_this_turn"}

        Sets a flag on the player consumed by execute_place_agent / combat phase.
        The restriction is cleared during the Recall phase.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        restriction = effect.get("restriction", "")
        restrictions = getattr(player, "turn_restrictions", [])
        if restriction and restriction not in restrictions:
            restrictions.append(restriction)
        player.turn_restrictions = restrictions

        return {
            "success": True,
            "applied": [f"Restricted: {restriction}"],
        }

    def _check_influence_reached_passives(
        self, player_id: str, faction: str
    ) -> list:
        """
        Called after any influence gain. Checks if the player's leader has an
        influence_reached passive that just triggered (i.e., the relevant faction
        influence exactly hit the threshold this gain).

        Returns a list of choice_data dicts if rewards need resolving, else [].
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []

        leader = getattr(player, "leader", None)
        if not leader:
            return []

        # Read passive from leader model (passive_ability = raw JSON dict)
        passive_data = getattr(leader, "passive_ability", None)
        if not passive_data:
            return []

        checks = passive_data.get("check", [])
        reward = passive_data.get("reward", [])
        if not checks or not reward:
            return []

        # Look for influence_reached check matching the faction that just changed
        for check in checks:
            if check.get("type") != "influence_reached":
                continue
            target = check.get("target", "")
            amount = check.get("amount", 0)
            if target != faction and target != "any":
                continue

            # Check if influence just reached or crossed the threshold.
            # We check if current >= amount (already applied) and that we haven't
            # previously fired (track with a set on the player).
            attr = f"{faction}_influence"
            current = getattr(player, attr, 0)
            fired_key = f"_passive_fired_{leader.name}_{faction}_{amount}"
            already_fired = getattr(player, fired_key, False)
            if current >= amount and not already_fired:
                setattr(player, fired_key, True)
                self.resolve_effects(player_id, reward, {"phase": "passive", "source": "passive_influence_reached"})
        return []

    def check_and_apply_reveal_passive(self, player_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Called after a player reveals their hand. Checks leader passives that fire
        at the reveal phase:
        - Feyd-Rautha: may recall a spy → +2 swords
        - Gurney Halleck: if combat strength ≥ 6 → +1 persuasion
        Returns a result dict with effects_applied and choices_required.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        leader = getattr(player, "leader", None)
        if not leader:
            return {"success": True, "effects_applied": [], "choices_required": []}

        name = getattr(leader, "name", "")
        applied = []
        choices = []

        if name == "Feyd Rautha Harkonnen":
            # Passive "Devious Strength": may recall a spy → +2 swords
            if player.spies_placed:
                choices.append({
                    "type": "reveal_passive_choice",
                    "leader": name,
                    "description": "Recall a spy to gain +2 swords?",
                    "options": [
                        {"id": "yes", "description": "+2 swords (recall 1 spy)"},
                        {"id": "no",  "description": "Skip"},
                    ],
                })

        elif name == "Gurney Halleck":
            # Passive "Always Smiling": combat strength ≥ 6 → +1 persuasion
            strength = player.combat_strength if hasattr(player, "combat_strength") else 0
            if strength >= 6:
                player.temp_persuasion = getattr(player, "temp_persuasion", 0) + 1
                applied.append("Gurney Halleck passive: +1 persuasion (strength ≥ 6)")

        elif name == "Muad'Dib":
            # Passive: sandworm in conflict → draw 1 intrigue (checked in combat)
            pass

        return {"success": True, "effects_applied": applied, "choices_required": choices}

    def _trigger_muaddib_sandworm_passive(self, player_id: str, worms_gained: int) -> None:
        """
        Muad'Dib's passive: whenever he recruits/gains a sandworm (worm resource
        effect fires), he draws 1 intrigue card per worm gained.
        Called from within _handle_resource for worm/sandworm gains.
        """
        if worms_gained <= 0:
            return
        player = self.state.get_player_by_id(player_id)
        if not player:
            return
        leader = getattr(player, "leader", None)
        if not leader or getattr(leader, "name", "") != "Muad'Dib":
            return
        # Once-per-round limit: only fire once regardless of how many worms are gained
        if getattr(player, "_muaddib_passive_fired_this_round", False):
            return
        player._muaddib_passive_fired_this_round = True
        if self.game.board.intrigue_deck:
            card = self.game.board.intrigue_deck.pop(0)
            player.intrigue_cards.append(card)

    # ==================== CONDITIONAL REWARD TRIGGER SYSTEM ====================

    def _check_and_trigger_conditional_rewards(
        self,
        player_id: str,
        triggering_effect: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if any active conditional rewards should trigger based on the effect just applied.

        This is called after each effect during resolution when monitor_triggers is enabled.
        It checks all active conditional rewards for this player and triggers matching ones.

        Args:
            player_id: Player who just had an effect applied
            triggering_effect: The effect that was just applied (may trigger rewards)
            context: Context dict with phase, card, location info

        Returns:
            Dict with triggered rewards' results, or None if no triggers
        """
        # Check if player has any active conditional rewards
        if player_id not in self.active_conditional_rewards:
            return None

        active_rewards = self.active_conditional_rewards[player_id]
        if not active_rewards:
            return None

        triggered_results = []

        # Check each active conditional reward
        for reward_data in active_rewards:
            condition = reward_data.get("condition", {})
            condition_type = condition.get("type")

            # Check if this effect triggers the condition
            should_trigger = False

            if condition_type == "buy_imperium":
                # Trigger when player acquires a card
                # This would be set by acquire_card action
                # For now, check if context indicates card acquisition
                if context.get("acquiring_card") or triggering_effect.get("type") == "acquire":
                    target = condition.get("target", "any")
                    if target == "any":
                        should_trigger = True
                    elif target in context.get("acquired_card_name", ""):
                        should_trigger = True

            elif condition_type == "agent_on":
                # Trigger when agent placed on specific location
                target_location = condition.get("target")
                current_location = context.get("location")
                if target_location and current_location == target_location:
                    should_trigger = True

            elif condition_type == "harvest":
                # Trigger when harvesting spice
                if triggering_effect.get("type") == "resource" and triggering_effect.get("resource") == "spice":
                    # Check if amount threshold met
                    threshold = condition.get("amount", 1)
                    spice_gained = triggering_effect.get("amount", 0)
                    if spice_gained >= threshold:
                        should_trigger = True

            elif condition_type == "influence":
                # Trigger when gaining influence with specific faction
                if triggering_effect.get("type") == "influence":
                    target_faction = condition.get("target", "any")
                    effect_faction = triggering_effect.get("target")
                    if target_faction == "any" or target_faction == effect_faction:
                        should_trigger = True

            elif condition_type == "resource":
                # Trigger when gaining specific resource
                target_resource = condition.get("target")
                if triggering_effect.get("type") == "resource":
                    effect_resource = triggering_effect.get("resource")
                    if effect_resource == target_resource:
                        should_trigger = True

            # If condition met, apply the reward
            if should_trigger:
                reward = reward_data.get("reward", [])
                card_name = reward_data.get("card_name", "Unknown")

                # Apply reward (without trigger monitoring to avoid infinite loops)
                reward_result = self.resolve_effects(
                    player_id,
                    reward,
                    {**context, "monitor_triggers": False, "triggered_by": card_name}
                )

                if reward_result.get("success"):
                    triggered_results.append({
                        "card": card_name,
                        "condition": condition_type,
                        "effects": reward_result.get("effects_applied", [])
                    })

        if triggered_results:
            return {
                "success": True,
                "effects_applied": [f"Triggered: {r['card']} ({r['condition']})" for r in triggered_results]
            }

        return None

    def register_conditional_reward(
        self,
        player_id: str,
        condition: Dict[str, Any],
        reward: List[Dict[str, Any]],
        card_name: str = "Unknown"
    ):
        """
        Manually register a conditional reward (for intrigue cards played during plot phase).

        Args:
            player_id: Player who has the conditional reward
            condition: Condition dict with type, target, amount
            reward: List of effect objects to apply when triggered
            card_name: Name of card providing the reward
        """
        if player_id not in self.active_conditional_rewards:
            self.active_conditional_rewards[player_id] = []

        self.active_conditional_rewards[player_id].append({
            "condition": condition,
            "reward": reward,
            "card_name": card_name
        })

    def clear_conditional_rewards(self, player_id: str):
        """
        Clear all conditional rewards for a player (called at end of round).

        Args:
            player_id: Player whose rewards to clear
        """
        if player_id in self.active_conditional_rewards:
            self.active_conditional_rewards[player_id] = []

    def clear_all_conditional_rewards(self):
        """Clear all conditional rewards for all players (round reset)."""
        self.active_conditional_rewards = {}

    # ==================== CARD 28-30 NEW EFFECT HANDLERS ====================

    def _handle_multiple(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generic multiplier effect: Apply reward X times based on count of Y.

        Supports:
        - "sandworm": Count sandworms in conflict
        - "contract": Count completed contracts
        - "spy": Count spies placed on board
        - "sword_card": Count OTHER revealed cards that provided swords this turn
        - "emperor_card" or "emperor_card_revealed": Count revealed Emperor cards this turn

        Args:
            effect: {
                "type": "multiple",
                "per": "sandworm"|"contract"|"spy"|"sword_card"|"emperor_card_revealed",
                "reward": [<effect objects>]
            }

        Examples:
            {"type": "multiple", "per": "sandworm", "reward": [{"type": "draw", "deck": "deck", "amount": 1}]}
            {"type": "multiple", "per": "contract", "reward": [{"type": "resource", "resource": "persuasion", "amount": 1}]}
            {"type": "multiple", "per": "spy", "reward": [{"type": "influence", "target": "any", "amount": 1}]}
        """
        player = self.state.get_player_by_id(player_id)
        per_type = effect.get("per", "")
        reward_effects = effect.get("reward", [])

        # Count based on per_type
        multiplier = 0

        if per_type == "sandworm":
            multiplier = getattr(player, 'sandworms_in_conflict', 0)

        elif per_type == "contract":
            multiplier = len(player.contracts_completed) if hasattr(player, 'contracts_completed') else 0

        elif per_type == "spy":
            # Count spies placed (for each spy, grant influence with that faction)
            # Special handling: need to track which factions are being spied on
            # Can be filtered by 'target' parameter (list of allowed factions)
            allowed_factions = effect.get("target", ["fremen", "bene_gesserit", "spacing_guild", "emperor"])

            spied_factions = set()
            if hasattr(player, 'spies_placed'):
                for observation_post_id in player.spies_placed:
                    # Find which observation post
                    for observation_post in self.game.board.observation_posts:
                        if str(observation_post.id) == str(observation_post_id):
                            # Determine faction from observation post name
                            faction_name = observation_post.name.lower().replace(" ", "_")
                            # Only count if faction is in allowed list
                            if faction_name in allowed_factions:
                                spied_factions.add(faction_name)

            # For each spied faction, apply the reward
            if len(spied_factions) == 0:
                return {
                    "success": True,
                    "effects_applied": ["No spies placed on allowed factions"]
                }

            # Apply reward for each faction
            all_effects_applied = []
            for faction in spied_factions:
                # Clone reward effects and set target to this faction
                for reward_effect in reward_effects:
                    modified_reward = reward_effect.copy()
                    # If influence effect without target, set to this faction
                    if modified_reward.get('type') == 'influence' and modified_reward.get('target') == 'any':
                        modified_reward['target'] = faction

                    result = self.resolve_effects(
                        player_id,
                        [modified_reward],
                        {**context, "monitor_triggers": False}
                    )
                    if result.get("success"):
                        all_effects_applied.extend(result.get("effects_applied", []))

            return {
                "success": True,
                "effects_applied": all_effects_applied or [f"Applied rewards for {len(spied_factions)} factions"]
            }

        elif per_type == "sword_card":
            # Count OTHER revealed cards that provided swords this turn
            if hasattr(player, 'revealed_cards_this_turn'):
                current_card_name = context.get("card") if context else None
                for card in player.revealed_cards_this_turn:
                    # Skip the current card
                    if current_card_name and hasattr(card, 'name') and card.name == current_card_name:
                        continue

                    # Check if card has reveal_effects with sword
                    if hasattr(card, 'reveal_effects'):
                        for reveal_effect in card.reveal_effects:
                            if isinstance(reveal_effect, dict):
                                # Check for sword resource
                                if (reveal_effect.get('type') == 'resource' and
                                    reveal_effect.get('resource') == 'sword'):
                                    multiplier += 1
                                    break  # Count card only once
                                # Check for sword shorthand
                                elif reveal_effect.get('type') == 'sword':
                                    multiplier += 1
                                    break

        elif per_type == "emperor_card" or per_type == "emperor_card_revealed":
            # Count revealed Emperor cards this turn (including current card)
            if hasattr(player, 'revealed_cards_this_turn'):
                for card in player.revealed_cards_this_turn:
                    if hasattr(card, 'faction'):
                        card_faction = card.faction
                        # Handle both string and list faction
                        if isinstance(card_faction, str):
                            if card_faction.lower() == "emperor":
                                multiplier += 1
                        elif isinstance(card_faction, list):
                            if "Emperor" in card_faction or "emperor" in card_faction:
                                multiplier += 1

        elif per_type == "fremen_card_revealed":
            # Count revealed Fremen cards this turn (including current card)
            if hasattr(player, 'revealed_cards_this_turn'):
                for card in player.revealed_cards_this_turn:
                    if hasattr(card, 'faction'):
                        card_faction = card.faction
                        # Handle both string and list faction
                        if isinstance(card_faction, str):
                            if card_faction.lower() == "fremen":
                                multiplier += 1
                        elif isinstance(card_faction, list):
                            if "Fremen" in card_faction or "fremen" in card_faction:
                                multiplier += 1

        else:
            return {
                "success": False,
                "error": f"Unknown multiplier type: {per_type}"
            }

        # Apply reward multiplier times
        if multiplier == 0:
            return {
                "success": True,
                "effects_applied": [f"No {per_type}s to multiply"]
            }

        all_effects_applied = []
        for _ in range(multiplier):
            result = self.resolve_effects(
                player_id,
                reward_effects,
                {**context, "monitor_triggers": False}
            )
            if result.get("success"):
                all_effects_applied.extend(result.get("effects_applied", []))

        return {
            "success": True,
            "effects_applied": all_effects_applied or [f"Applied {multiplier}x reward for {per_type}"]
        }

    def _handle_deck_manipulation(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Look at top N cards of deck, then draw/discard/trash one each.

        Card 30 - Long Live the Fighters reveal effect.

        Args:
            effect: {
                "type": "deck_manipulation",
                "look": 3,
                "draw": 1,
                "discard": 1,
                "trash": 1
            }
        """
        player = self.state.get_player_by_id(player_id)

        look_count = effect.get("look", 3)
        draw_count = effect.get("draw", 1)
        discard_count = effect.get("discard", 1)
        trash_count = effect.get("trash", 1)

        # Look at top N cards
        top_cards = []
        for i in range(min(look_count, len(player.deck.cards))):
            if i < len(player.deck.cards):
                top_cards.append(player.deck.cards[-(i+1)])  # Top cards are at end of list

        if len(top_cards) < look_count:
            # Need to shuffle discard into deck
            if player.discard_pile.cards:
                player.deck.cards.extend(player.discard_pile.cards)
                player.discard_pile.cards.clear()
                player.deck.shuffle()

                # Try again
                for i in range(min(look_count, len(player.deck.cards))):
                    if i < len(player.deck.cards) and i >= len(top_cards):
                        top_cards.append(player.deck.cards[-(i+1)])

        if len(top_cards) == 0:
            return {
                "success": True,
                "effects_applied": ["No cards in deck to manipulate"]
            }

        # For AI/bot: make random choices
        # For human: this would require a choice prompt
        # TODO: Implement choice system for human players

        # Remove cards from deck
        for card in top_cards:
            if card in player.deck.cards:
                player.deck.cards.remove(card)

        # Random selection for bot
        import random
        remaining_cards = top_cards.copy()

        # Draw one
        if draw_count > 0 and remaining_cards:
            drawn_card = random.choice(remaining_cards)
            remaining_cards.remove(drawn_card)
            player.hand.add_card(drawn_card)

        # Discard one
        if discard_count > 0 and remaining_cards:
            discarded_card = random.choice(remaining_cards)
            remaining_cards.remove(discarded_card)
            player.discard_pile.add_card(discarded_card)

        # Trash one
        if trash_count > 0 and remaining_cards:
            trashed_card = random.choice(remaining_cards)
            remaining_cards.remove(trashed_card)
            # Trashed cards removed from game (don't add anywhere)

        # Put remaining cards back on top of deck
        for card in remaining_cards:
            player.deck.cards.append(card)

        return {
            "success": True,
            "effects_applied": [f"Manipulated top {len(top_cards)} cards (drew/discarded/trashed)"],
            "choices_required": []  # TODO: Add choice for human players
        }

    def _handle_influence_double(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 34 - Overthrow agent effect.

        Doubles the influence gained from this board space.
        When placed on an alliance space, gain 2 influence instead of 1.

        This is a modifier effect that changes how the board space influence works.
        It should be tracked and applied when the board space processes influence.

        Args:
            effect: {
                "type": "influence_double",
                "description": "Gain 2 influence instead of 1"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Mark that this player should get doubled influence from the current board space
        if not hasattr(player, 'influence_double_active'):
            player.influence_double_active = False

        player.influence_double_active = True

        return {
            "success": True,
            "effects_applied": ["Influence gains doubled for this board space"],
            "influence_double": True  # Signal to board space processor
        }

    def _handle_acquire_with_solari(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 36 - Price is No Object agent effect.

        Allows player to acquire a card using solari instead of persuasion.
        This is a modifier effect that changes the acquisition rules for this turn.

        Args:
            effect: {
                "type": "acquire_with_solari",
                "description": "Acquire card using solari instead of persuasion"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Mark that this player can acquire with solari this turn
        if not hasattr(player, 'can_acquire_with_solari'):
            player.can_acquire_with_solari = False

        player.can_acquire_with_solari = True

        return {
            "success": True,
            "effects_applied": ["Can acquire cards with solari instead of persuasion this turn"],
            "acquire_with_solari": True  # Signal to acquisition system
        }

    def _handle_choice_bot_autoselect(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        OLD BOT-ONLY choice handler - auto-selects first valid option.

        This is deprecated in favor of _handle_choice at line 1420 which returns
        choice_required for proper human/bot handling.

        Card 37 - Priority Contracts agent effect.

        Presents the player with a choice between multiple options.
        Each option can have checks and rewards.

        For AI/bot: randomly select first valid option.
        For human: would require choice prompt.

        Args:
            effect: {
                "type": "choice",
                "options": [
                    {
                        "reward": [...]
                    },
                    {
                        "check": [...],
                        "reward": [...]
                    }
                ]
            }
        """
        player = self.state.get_player_by_id(player_id)
        options = effect.get("options", [])

        if not options:
            return {
                "success": False,
                "error": "No options provided for choice"
            }

        # Find first valid option (checks pass)
        valid_options = []
        for i, option in enumerate(options):
            checks = option.get("check", [])

            if checks:
                # Evaluate checks for this option
                check_result = self._evaluate_checks(player_id, checks, context)
                if check_result.get("success"):
                    valid_options.append(i)
            else:
                # No checks means always valid
                valid_options.append(i)

        if not valid_options:
            # If no options are valid, fail gracefully
            # (Player might not meet requirements for any option)
            return {
                "success": True,
                "effects_applied": ["No valid choice options available"]
            }

        # For AI/bot: select first valid option
        # For human: would prompt for choice
        # TODO: Implement choice system for human players
        selected_index = valid_options[0]
        selected_option = options[selected_index]

        # Apply the rewards from selected option
        rewards = selected_option.get("reward", [])
        if rewards:
            result = self.resolve_effects(player_id, rewards, {**context, "monitor_triggers": False})
            return {
                "success": True,
                "effects_applied": result.get("effects_applied", [f"Choice option {selected_index + 1} selected"]),
                "choice_made": selected_index
            }
        else:
            return {
                "success": True,
                "effects_applied": [f"Choice option {selected_index + 1} selected (no effects)"],
                "choice_made": selected_index
            }

    def _handle_bypass_troops_deployment_rule(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 41 - Sardaukar Coordination agent effect.

        Allows player to deploy any troops recruited this turn directly to the Conflict.
        This bypasses the normal deployment rules for this turn.

        Args:
            effect: {
                "type": "bypass_troops_deployment_rule",
                "description": "You may deploy any troops you recruit this turn to the Conflict"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Mark that this player can bypass deployment rules this turn
        if not hasattr(player, 'can_bypass_deployment_rule'):
            player.can_bypass_deployment_rule = False

        player.can_bypass_deployment_rule = True

        return {
            "success": True,
            "effects_applied": ["Can bypass troop deployment rules this turn"],
            "bypass_deployment_rule": True  # Signal to recruitment system
        }

    def _handle_trash_to_acquire(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 43 - Shishakli agent effect.

        Trash a card from hand to acquire a card from the reserves.

        Args:
            effect: {
                "type": "trash_to_acquire",
                "description": "Trash a card to acquire a card from the reserves"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Check if player has cards to trash
        if not hasattr(player, 'hand') or not hasattr(player.hand, 'cards'):
            return {
                "success": False,
                "error": "No hand to trash from"
            }

        if len(player.hand.cards) == 0:
            return {
                "success": False,
                "error": "No cards in hand to trash"
            }

        # Human players must pick; bots auto-select first card
        if player.is_human:
            # Use the standard {"card": obj, "source": "hand"} format so
            # _make_choice_json_safe serialises it correctly and execute_choice
            # can look the card up by id (same pattern as trash_card).
            available_cards = [
                {"card": c, "source": "hand"}
                for c in player.hand.cards
            ]
            return {
                "success": True,
                "choice_required": True,
                "choice_data": {
                    "type": "trash_to_acquire",
                    "available_cards": available_cards
                }
            }

        card_to_trash = player.hand.cards[0]
        player.hand.cards.remove(card_to_trash)

        # Track trashed card
        if not hasattr(player, 'trashed_cards'):
            player.trashed_cards = []
        player.trashed_cards.append(card_to_trash.name if hasattr(card_to_trash, 'name') else str(card_to_trash))

        # Now allow player to acquire from reserves
        # This would trigger acquisition system
        # For now, just mark that player can acquire from reserves
        if not hasattr(player, 'can_acquire_from_reserves'):
            player.can_acquire_from_reserves = False

        player.can_acquire_from_reserves = True

        return {
            "success": True,
            "effects_applied": [f"Trashed {card_to_trash.name if hasattr(card_to_trash, 'name') else 'card'}, can acquire from reserves"],
            "trash_to_acquire": True  # Signal to acquisition system
        }

    def _handle_trade(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 45 - Smuggler's Haven agent effect.

        Trade resources for rewards (pay costs to get rewards).

        Args:
            effect: {
                "type": "trade",
                "cost": [{"type": "resource", "resource": "spice", "amount": 4}],
                "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
            }
        """
        costs = effect.get("cost", [])
        rewards = effect.get("reward", [])

        if not costs:
            return {
                "success": False,
                "error": "No costs specified for trade"
            }

        if not rewards:
            return {
                "success": False,
                "error": "No rewards specified for trade"
            }

        # A trade is OPTIONAL: the player MAY pay the cost for the reward.
        # If they can't afford it, skip silently so the rest of the agent's
        # effects still resolve (matches _handle_conditional behaviour).
        cost_check = self._check_costs(player_id, costs)
        if not cost_check.get("success"):
            return {
                "success": True,
                "applied": {
                    "type": "trade",
                    "declined": True,
                    "reason": "Cannot afford cost"
                }
            }

        # Affordable: present the optional accept/decline choice. We reuse the
        # "conditional" choice type since it has the same accept/decline shape
        # and is already handled by both the human UI and the bot resolver.
        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "conditional",
                "costs": costs,
                "rewards": rewards
            }
        }

    def _handle_acquire_card(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 47, 48 - Acquire card effect.

        Allows player to acquire a card from the Imperium row or reserves.
        This is a signal effect that marks the player as able to acquire.

        Args:
            effect: {
                "type": "acquire_card"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Mark that player can acquire a card
        if not hasattr(player, 'can_acquire_card'):
            player.can_acquire_card = 0

        player.can_acquire_card += 1

        return {
            "success": True,
            "effects_applied": ["Can acquire a card"],
            "acquire_card": True  # Signal to acquisition system
        }

    def _handle_trash_hand_card(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 54 - Treacherous Maneuver agent effect.

        Trash this card and a card of specific faction from hand.

        Args:
            effect: {
                "type": "trash_hand_card",
                "faction": "emperor",
                "description": "Trash this card and an Emperor card from hand"
            }
        """
        player = self.state.get_player_by_id(player_id)
        required_faction = effect.get("faction", "").lower().replace(" ", "_")

        # Trash the current card (self)
        current_card_name = context.get("card") if context else None
        if current_card_name:
            # Find and remove from hand
            card_found = False
            if hasattr(player, 'hand') and hasattr(player.hand, 'cards'):
                for card in player.hand.cards[:]:
                    if hasattr(card, 'name') and card.name == current_card_name:
                        player.hand.cards.remove(card)
                        card_found = True
                        break

            if card_found:
                # Track trashed card
                if not hasattr(player, 'trashed_cards'):
                    player.trashed_cards = []
                player.trashed_cards.append(current_card_name)

        # Find and trash a card of required faction from hand
        faction_card_found = False
        faction_card_name = None

        if hasattr(player, 'hand') and hasattr(player.hand, 'cards'):
            for card in player.hand.cards[:]:
                if hasattr(card, 'faction'):
                    card_faction = card.faction
                    # Handle both string and list faction
                    matches_faction = False
                    if isinstance(card_faction, str):
                        if card_faction.lower().replace(" ", "_") == required_faction:
                            matches_faction = True
                    elif isinstance(card_faction, list):
                        for f in card_faction:
                            if f.lower().replace(" ", "_") == required_faction:
                                matches_faction = True
                                break

                    if matches_faction:
                        faction_card_name = card.name if hasattr(card, 'name') else str(card)
                        player.hand.cards.remove(card)
                        faction_card_found = True
                        break

        if not faction_card_found:
            return {
                "success": False,
                "error": f"No {required_faction} card in hand to trash"
            }

        # Track trashed faction card
        if not hasattr(player, 'trashed_cards'):
            player.trashed_cards = []
        player.trashed_cards.append(faction_card_name)

        return {
            "success": True,
            "effects_applied": [f"Trashed {current_card_name or 'this card'} and {faction_card_name}"]
        }

    def _handle_ignore_influence_requirements(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 57 - Undercover Asset agent effect.

        Ignore Influence requirements on board spaces when sending an Agent this turn.

        Args:
            effect: {
                "type": "ignore_influence_requirements",
                "description": "Ignore Influence requirements on board spaces when sending an Agent this turn"
            }
        """
        player = self.state.get_player_by_id(player_id)

        # Mark that this player can ignore influence requirements this turn
        if not hasattr(player, 'ignore_influence_requirements'):
            player.ignore_influence_requirements = False

        player.ignore_influence_requirements = True

        return {
            "success": True,
            "effects_applied": ["Can ignore influence requirements this turn"],
            "ignore_influence_requirements": True  # Signal to board space system
        }

    def _handle_deploy_or_retreat_troop(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 58 - Unswerving Loyalty Fremen bond effect.

        You may deploy or retreat one of your troops.

        Args:
            effect: {
                "type": "deploy_or_retreat_troop",
                "amount": 1,
                "description": "You may deploy or retreat one of your troops"
            }
        """
        player = self.state.get_player_by_id(player_id)
        amount = effect.get("amount", 1)

        # This is a choice effect that would require player input
        # For AI/bot: default to deploying if troops available
        # For human: would prompt for choice

        if player.troops_in_garrison >= amount:
            # Deploy troops to conflict
            player.troops_in_garrison -= amount
            player.troops_in_conflict += amount
            return {
                "success": True,
                "effects_applied": [f"Deployed {amount} troop(s) to conflict"]
            }
        elif player.troops_in_conflict >= amount:
            # Retreat troops to garrison
            player.troops_in_conflict -= amount
            player.troops_in_garrison += amount
            return {
                "success": True,
                "effects_applied": [f"Retreated {amount} troop(s) to garrison"]
            }
        else:
            return {
                "success": False,
                "error": "No troops available to deploy or retreat"
            }

    def _handle_return_to_hand(
        self,
        player_id: str,
        effect: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Card 59 - Weirding Woman agent effect.

        Return a card from play to your hand.

        Args:
            effect: {
                "type": "return_to_hand",
                "target": "self",
                "description": "Return this card from play to your hand"
            }
        """
        player = self.state.get_player_by_id(player_id)
        target = effect.get("target", "self")

        if target == "self":
            # Return the current card from play to hand
            current_card_name = context.get("card") if context else None

            if not current_card_name:
                return {
                    "success": False,
                    "error": "No card context for returning to hand"
                }

            # Find the card in play area
            card_found = False
            card_to_return = None

            if hasattr(player, 'play_area'):
                for card in player.play_area[:]:
                    if hasattr(card, 'name') and card.name == current_card_name:
                        card_to_return = card
                        player.play_area.remove(card)
                        card_found = True
                        break

            if not card_found:
                return {
                    "success": False,
                    "error": f"Card {current_card_name} not found in play area"
                }

            # Add card to hand
            if hasattr(player, 'hand') and hasattr(player.hand, 'add_card'):
                player.hand.add_card(card_to_return)
            elif hasattr(player, 'hand') and hasattr(player.hand, 'cards'):
                player.hand.cards.append(card_to_return)

            return {
                "success": True,
                "effects_applied": [f"Returned {current_card_name} to hand"]
            }
        else:
            # TODO: Handle returning other cards
            return {
                "success": False,
                "error": f"Returning target {target} not implemented"
            }

    def _handle_cost(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle cost/reward pattern - pay a cost to get a reward.

        Format:
        {
            "type": "cost",
            "payment": {"type": "trash_intrigue", "amount": 1},
            "reward": [...]
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        payment = effect.get('payment', {})
        reward = effect.get('reward', [])

        # Try to pay the cost
        # For now, just mark it as optional choice (player can choose to pay or not)
        # TODO: Implement actual payment validation
        payment_result = {"success": True, "effects_applied": ["Cost payment (stub)"]}

        # If payment succeeded, give reward
        if payment_result.get('success'):
            reward_result = self.resolve_effects(player_id, reward, context)
            return {
                "success": True,
                "effects_applied": payment_result.get('effects_applied', []) + reward_result.get('effects_applied', [])
            }

        return {"success": False, "error": "Payment failed"}

    def _handle_exchange(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle exchange pattern - pay a cost to get a reward (similar to cost).

        Format:
        {
            "type": "exchange",
            "cost": [{"type": "discard", "deck": "hand", "amount": 1}],
            "reward": [{"type": "draw", "deck": "deck", "amount": 1}]
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        cost = effect.get('cost', [])
        reward = effect.get('reward', [])

        # Pay the cost
        cost_result = self.resolve_effects(player_id, cost, context)

        if cost_result.get('success'):
            # If cost paid, give reward
            reward_result = self.resolve_effects(player_id, reward, context)
            return {
                "success": True,
                "effects_applied": cost_result.get('effects_applied', []) + reward_result.get('effects_applied', [])
            }

        return {"success": False, "error": "Cost payment failed"}

    def _handle_bypass_influence_requirement_rule(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle bypassing influence requirements for acquiring cards.

        Format:
        {
            "type": "bypass_influence_requirment_rule"
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        # Set a flag on the player to indicate they can bypass influence requirements
        if not hasattr(player, 'can_bypass_influence_requirements'):
            player.can_bypass_influence_requirements = False

        player.can_bypass_influence_requirements = True

        return {
            "success": True,
            "effects_applied": ["Can bypass influence requirements"]
        }

    # ==================== LEADER-SPECIFIC EFFECT HANDLERS ====================

    def _handle_play_spy(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle playing a spy (Staban Tuek signet).

        Format:
        {
            "type": "play_spy",
            "description": "Play a spy anywhere"
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        # Check if player has spies available
        if player.spies_available <= 0:
            return {"success": False, "error": "No spies available"}

        # Set a flag indicating player can place a spy
        # The actual placement will be handled by action_executor
        if not hasattr(player, 'can_place_spy_from_signet'):
            player.can_place_spy_from_signet = False

        player.can_place_spy_from_signet = True

        return {
            "success": True,
            "effects_applied": ["Can place spy"],
            "requires_action": "place_spy"  # Signals that player needs to choose where to place
        }

    def _handle_ply(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle ply effect (Lady Margot Fenring - play spy on any space matching agent_icon).

        Format:
        {
            "type": "ply",
            "agent": "spy",
            "amount": 1,
            "target": "blue"       # icon name, e.g. "blue" matches both "blue" and "bene_gesserit"
        }

        Raises a play_spy_on_space choice with all eligible board spaces so
        the player can pick one. The chosen space's id is added to spies_placed.
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        agent_type = effect.get('agent', 'spy')
        amount = effect.get('amount', 1)
        target = effect.get('target')

        if agent_type != 'spy':
            return {"success": False, "error": f"Unknown agent type: {agent_type}"}

        if player.spies_available < amount:
            return {"success": False, "error": "Not enough spies available"}

        def _icon_matches(space_icon, target_icon):
            """A space matches 'blue' if its icon is 'blue' or 'bene_gesserit', etc."""
            if not space_icon:
                return False
            icons = space_icon if isinstance(space_icon, list) else [space_icon]
            # Direct match
            if target_icon in icons:
                return True
            # Color-to-faction aliasing
            color_aliases = {
                "blue": ["bene_gesserit"],
                "yellow": ["fremen"],
                "green": ["spacing_guild"],
                "red": ["emperor"],
            }
            for alias in color_aliases.get(target_icon, []):
                if alias in icons:
                    return True
            return False

        # Build list of eligible spaces (not already spied by this player)
        eligible = []
        for space in self.game.board.spaces:
            if not _icon_matches(getattr(space, 'agent_icon', None), target):
                continue
            if str(space.id) in [str(s) for s in player.spies_placed]:
                continue
            eligible.append({
                "space_id": str(space.id),
                "space_name": space.name
            })

        if not eligible:
            return {
                "success": True,
                "applied": {"type": "ply", "agent": agent_type, "amount": 0,
                            "reason": "no eligible spaces"}
            }

        return {
            "success": True,
            "choice_required": True,
            "choice_data": {
                "type": "play_spy_on_space",
                "amount": amount,
                "target": target,
                "eligible_spaces": eligible
            }
        }

    def _handle_transform_leader(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle leader transformation (Lady Jessica → Reverend Mother).

        Format:
        {
            "type": "transform_leader",
            "target": "reverend_mother"
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        target_leader = effect.get('target')

        if not target_leader:
            return {"success": False, "error": "No target leader specified"}

        # Import ReverendMother class
        try:
            from ...models.leader import ReverendMother
        except ImportError:
            return {"success": False, "error": "ReverendMother class not found"}

        # Transform the leader
        if target_leader == 'reverend_mother':
            old_leader = player.leader.name
            player.leader = ReverendMother()

            return {
                "success": True,
                "effects_applied": [f"Transformed {old_leader} to Reverend Mother"]
            }

        return {"success": False, "error": f"Unknown transformation target: {target_leader}"}

    def _handle_retrigger_board_space(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle retriggering a board space effect (Reverend Mother passive).

        Format:
        {
            "type": "retrigger_board_space"
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        # Get the location from context
        location = context.get('location') if context else None

        if not location:
            return {"success": False, "error": "No location in context to retrigger"}

        # Get the board space effects
        if hasattr(location, 'reward') and location.reward:
            # Resolve the board space effects again
            from ..actions.action_executor import ActionExecutor
            executor = ActionExecutor(self.game)

            # Re-resolve location effects
            result = self.resolve_effects(player_id, location.reward, context)

            return {
                "success": True,
                "effects_applied": [f"Retriggered {location.name}"] + result.get('effects_applied', [])
            }

        return {"success": False, "error": "Location has no effects to retrigger"}

    def _handle_contract_choice_expansion(self, player_id: str, effect: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle expanding contract choices (Shaddam Corrino IV passive - Sardaukar contracts).

        Format:
        {
            "type": "contract_choice_expansion",
            "sources": ["board", "sardaukar_reserve"]
        }
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": f"Player {player_id} not found"}

        sources = effect.get('sources', [])

        # Set a flag on the player indicating they can choose from expanded sources
        if not hasattr(player, 'contract_sources'):
            player.contract_sources = ['board']  # Default

        player.contract_sources = sources

        return {
            "success": True,
            "effects_applied": [f"Can choose contracts from: {', '.join(sources)}"]
        }
