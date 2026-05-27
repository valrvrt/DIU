"""Extended GameSession with action execution, bot loop, and game phase management."""

import random as _random
from typing import Any, Dict, List, Optional

from src.engine.core.game_setup import GameSetup
from src.engine.managers.phase_manager import PhaseManager
from src.engine.managers.deck_manager import DeckManager
from src.engine.managers.combat_manager import CombatManager
from src.engine.managers.makers_manager import MakersManager
from src.engine.managers.influence_manager import InfluenceManager
from src.engine.managers.victory_point_manager import VictoryPointManager
from src.engine.managers.contract_manager import ContractManager
from src.engine.actions.action_generator import ActionGenerator
from src.engine.actions.action_executor import (
    ActionExecutor, PlaceAgentAction, RevealAction, AcquireCardAction,
    PlayIntrigueAction, DeployTroopsAction,
)
from src.engine.effects.effect_resolver import EffectResolver
from src.models.game import Game, GamePhase
from src.models.player import Player
from src.bots import HeuristicBot

from .serializer import serialize_state, _imperium_card, _intrigue_card, _contract_card


# ─────────────────────── choice serialization ──────────────────

def _make_choice_json_safe(choice_data: Dict) -> Dict:
    """
    Convert a choices_required entry into a JSON-safe dict.

    effect_resolver embeds live objects (ImperiumCard, ContractCard, etc.)
    inside choice_data. We need to serialize them before sending over HTTP.
    """
    result = {k: v for k, v in choice_data.items()}

    # available_cards: list of {"card": ImperiumCard, "source": str}
    if "available_cards" in result:
        result["available_cards"] = [
            {
                "card": _imperium_card(item["card"]) if hasattr(item.get("card"), "cost")
                        else {"id": str(item.get("card", "")), "name": str(item.get("card", ""))},
                "source": item.get("source", ""),
            }
            for item in result["available_cards"]
        ]

    # available_contracts: list of ContractCard objects
    if "available_contracts" in result:
        result["available_contracts"] = [
            _contract_card(c) if hasattr(c, "completion_type")
            else {"id": str(c), "name": str(c)}
            for c in result["available_contracts"]
        ]

    return result


# ──────────────────────── GameSession ──────────────────────────

class GameSession:
    """Owns one complete game session for the web UI layer."""

    def __init__(self, game: Game, managers: Dict[str, Any], bots: Dict[str, Any],
                 human_player_id: str):
        self.game = game
        self.managers = managers
        self.bots = bots
        self.human_player_id = human_player_id
        self.event_log: List[Dict[str, Any]] = []
        self.pending_choice: Optional[Dict[str, Any]] = None
        self._choices_queue: List[Dict[str, Any]] = []
        # Track which phase of the round we're in for acquisition
        self._human_acquisition_done: bool = False

    # ──────── construction ────────

    @classmethod
    def new(cls, player_count: int = 3, human_name: str = "Player",
            selected_leaders: Optional[List[int]] = None) -> "GameSession":
        if player_count not in (3, 4):
            raise ValueError("player_count must be 3 or 4")

        game, _ = GameSetup.create_game(
            player_count=player_count,
            human_player_name=human_name,
            selected_leaders=selected_leaders,
        )

        human_player = game.players[0]
        human_player.is_human = True
        for p in game.players[1:]:
            p.is_human = False

        deck_manager = DeckManager(game)
        influence_manager = InfluenceManager(game)
        victory_point_manager = VictoryPointManager(game)
        effect_resolver = EffectResolver(game, influence_manager=influence_manager)
        combat_manager = CombatManager(
            game, effect_resolver=effect_resolver,
            victory_point_manager=victory_point_manager,
        )
        makers_manager = MakersManager(game)
        phase_manager = PhaseManager(
            game, deck_manager=deck_manager, combat_manager=combat_manager,
            makers_manager=makers_manager,
        )
        action_generator = ActionGenerator(game, phase_manager, effect_resolver)
        action_executor = ActionExecutor(game, phase_manager, deck_manager, effect_resolver)
        contract_manager = ContractManager(game)

        managers = {
            "phase_manager": phase_manager, "deck_manager": deck_manager,
            "combat_manager": combat_manager, "makers_manager": makers_manager,
            "action_generator": action_generator, "action_executor": action_executor,
            "influence_manager": influence_manager,
            "victory_point_manager": victory_point_manager,
            "effect_resolver": effect_resolver, "contract_manager": contract_manager,
            "game": game,
        }

        bots: Dict[str, Any] = {}
        for p in game.players[1:]:
            bots[p.player_id] = HeuristicBot(p, managers)

        game.current_phase = GamePhase.PLAYER_TURNS
        game.current_round = 1
        if game.board.conflict_deck:
            game.board.current_conflict = game.board.conflict_deck.pop(0)

        return cls(game=game, managers=managers, bots=bots,
                   human_player_id=human_player.player_id)

    # ──────── properties ────────

    @property
    def human_player(self) -> Player:
        return self.game.get_player(self.human_player_id)

    @property
    def is_human_turn(self) -> bool:
        return (
            self.game.current_phase == GamePhase.PLAYER_TURNS
            and self.game.current_player.player_id == self.human_player_id
            and not self.human_player.has_revealed_this_round
        )

    # ──────── event log ────────

    def log(self, event_type: str, **fields) -> None:
        entry = {"type": event_type}
        entry.update(fields)
        self.event_log.append(entry)
        if len(self.event_log) > 200:
            self.event_log = self.event_log[-200:]

    def drain_log(self) -> List[Dict[str, Any]]:
        events, self.event_log = self.event_log, []
        return events

    # ──────── state snapshot ────────

    def _compute_available_actions(self) -> Dict[str, Any]:
        """What can the human do right now?"""
        human = self.human_player
        if self.pending_choice:
            return {"phase": "choice", "pending_choice": self.pending_choice}

        action_gen = self.managers["action_generator"]
        phase = self.game.current_phase.value if hasattr(self.game.current_phase, "value") \
                else str(self.game.current_phase)

        if phase == "player_turns" and not human.has_revealed_this_round:
            # Agent turn: can place agent or reveal
            playable = []
            for card in action_gen.get_playable_imperium_cards(self.human_player_id):
                locs = action_gen.get_valid_locations_for_card(self.human_player_id, card)
                # locs is a list of (BoardSpace, placement_type) tuples
                loc_ids = [str(space.id) for space, _ in locs] if locs else []
                playable.append({
                    "card_id": card.id,
                    "card_name": card.name,
                    "valid_location_ids": loc_ids,
                })
            opts = action_gen.get_acquisition_options(self.human_player_id)
            troop_opts = action_gen.get_troop_deployment_options(self.human_player_id)
            return {
                "phase": "agent_turn",
                "can_reveal": True,
                "can_place_agent": bool(playable) and human.agents_available > 0,
                "playable_cards": playable,
                "max_troops": troop_opts.get("max_from_garrison", 0),
            }

        if phase == "player_turns" and human.has_revealed_this_round:
            # Acquisition turn
            opts = action_gen.get_acquisition_options(self.human_player_id)
            persuasion = getattr(human, "temp_persuasion", 0)
            return {
                "phase": "acquisition",
                "persuasion_left": persuasion,
                "imperium_row": [_imperium_card(c) for c in opts.get("imperium_row", [])],
                "reserve_prepare": (
                    {"card": _imperium_card(opts["reserve_prepare"][0]),
                     "remaining": len(opts["reserve_prepare"])}
                    if opts.get("reserve_prepare") else None
                ),
                "reserve_spice": (
                    {"card": _imperium_card(opts["reserve_spice"][0]),
                     "remaining": len(opts["reserve_spice"])}
                    if opts.get("reserve_spice") else None
                ),
                "contract_row": [_contract_card(c) for c in self.game.board.contract_row],
            }

        return {"phase": phase}

    def snapshot(self) -> Dict[str, Any]:
        state = serialize_state(self.game, viewer_player_id=self.human_player_id)
        state["available_actions"] = self._compute_available_actions()
        return {
            "state": state,
            "pending_choice": self.pending_choice,
            "is_human_turn": self.is_human_turn,
            "events": self.drain_log(),
        }

    # ──────── choice queue management ────────

    def _queue_choices(self, choices: List[Dict]) -> None:
        if not choices:
            return
        safe = [_make_choice_json_safe(c) for c in choices]
        self._choices_queue.extend(safe)
        if not self.pending_choice:
            self.pending_choice = self._choices_queue.pop(0)

    def _clear_pending_choice(self) -> None:
        self.pending_choice = None
        if self._choices_queue:
            self.pending_choice = self._choices_queue.pop(0)

    # ──────── action dispatch ────────

    def execute_action(self, action_dict: Dict) -> Dict:
        action_type = action_dict.get("type", "")

        # Resolve a pending choice
        if action_type == "resolve_choice":
            return self._do_resolve_choice(action_dict)

        # Only allow human actions when it's their turn
        human = self.human_player
        if self.pending_choice:
            return {"error": "A choice must be resolved first", **self.snapshot()}

        dispatch = {
            "place_agent": self._do_place_agent,
            "reveal": self._do_reveal,
            "acquire_card": self._do_acquire_card,
            "acquire_contract": self._do_acquire_contract,
            "play_intrigue": self._do_play_intrigue,
            "end_acquisition": self._do_end_acquisition,
        }
        handler = dispatch.get(action_type)
        if handler is None:
            return {"error": f"Unknown action: {action_type}", **self.snapshot()}

        result = handler(action_dict)
        if not result.get("success"):
            return {"error": result.get("error", "Action failed"), **self.snapshot()}

        choices = result.get("choices_required", [])
        if choices:
            self._queue_choices(choices)

        if not self.pending_choice:
            self._post_action_advance(action_type)

        return self.snapshot()

    # ──────── human action handlers ────────

    def _do_place_agent(self, d: Dict) -> Dict:
        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]
        human = self.human_player

        card_id = d.get("card_id", "")
        location_id = str(d.get("location_id", ""))
        troops = int(d.get("troops", 0))

        card = next((c for c in human.hand.cards if c.id == card_id), None)
        if card is None:
            return {"success": False, "error": f"Card {card_id} not in hand"}

        location = self.game.board.get_space_by_id(location_id)
        if location is None:
            # Try int lookup
            try:
                location = self.game.board.get_space_by_id(int(location_id))
            except Exception:
                pass
        if location is None:
            return {"success": False, "error": f"Location {location_id} not found"}

        action = PlaceAgentAction(
            player_id=self.human_player_id,
            card=card,
            location=location,
            placement_type=location.agent_icon,
            troops_to_deploy=troops,
        )
        result = action_exec.execute_place_agent(action)
        if result.get("success"):
            self.log("place_agent", player=human.name, card=card.name, location=location.name)
        return result

    def _do_reveal(self, d: Dict) -> Dict:
        action_exec = self.managers["action_executor"]
        human = self.human_player
        result = action_exec.execute_reveal(RevealAction(player_id=self.human_player_id))
        if result.get("success"):
            self.log("reveal", player=human.name, persuasion=result.get("total_persuasion", 0))
            # Apply reveal passive
            effect_resolver = self.managers["effect_resolver"]
            if hasattr(effect_resolver, "check_and_apply_reveal_passive"):
                passive = effect_resolver.check_and_apply_reveal_passive(self.human_player_id, {})
                if passive and passive.get("choices_required"):
                    result.setdefault("choices_required", [])
                    result["choices_required"].extend(passive["choices_required"])
        return result

    def _do_acquire_card(self, d: Dict) -> Dict:
        action_exec = self.managers["action_executor"]
        human = self.human_player
        card_id = d.get("card_id", "")
        source = d.get("source", "row")

        # Find card in imperium_row or reserve
        card = next((c for c in self.game.board.imperium_row if c.id == card_id), None)
        if card is None and self.game.board.reserve_prepare_the_way:
            top = self.game.board.reserve_prepare_the_way[0]
            if top.id == card_id:
                card, source = top, "reserve"
        if card is None and self.game.board.reserve_spice_must_flow:
            top = self.game.board.reserve_spice_must_flow[0]
            if top.id == card_id:
                card, source = top, "reserve"

        if card is None:
            return {"success": False, "error": f"Card {card_id} not available"}

        persuasion = getattr(human, "temp_persuasion", 0)
        if card.cost > persuasion:
            return {"success": False, "error": f"Not enough persuasion (have {persuasion}, need {card.cost})"}

        result = action_exec.execute_acquire_card(AcquireCardAction(
            player_id=self.human_player_id, card=card, source=source
        ))
        if result.get("success"):
            # Note: action_executor already deducts card.cost from temp_persuasion; don't double-deduct
            self.log("acquire_card", player=human.name, card=card.name, cost=card.cost)
            # Contract completions
            for comp in result.get("contract_completions", {}).get("completed_contracts", []):
                self.log("contract_completed", player=human.name, contract=comp.get("contract", ""))
        return result

    def _do_acquire_contract(self, d: Dict) -> Dict:
        contract_manager = self.managers.get("contract_manager")
        if contract_manager is None:
            return {"success": False, "error": "No contract manager"}

        contract_id = str(d.get("contract_id", ""))
        contract = next(
            (c for c in self.game.board.contract_row if str(c.id) == contract_id), None
        )
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not available"}

        result = contract_manager.acquire_contract(self.human_player_id, contract)
        if result.get("success"):
            self.log("acquire_contract", player=self.human_player.name,
                     contract=contract.name, completed=result.get("completed", False))
        return result

    def _do_play_intrigue(self, d: Dict) -> Dict:
        action_exec = self.managers["action_executor"]
        human = self.human_player
        card_id = d.get("card_id", "")

        card = next((c for c in human.intrigue_cards if c.id == card_id), None)
        if card is None:
            return {"success": False, "error": f"Intrigue {card_id} not in hand"}

        result = action_exec.execute_play_intrigue(PlayIntrigueAction(
            player_id=self.human_player_id, intrigue_card=card
        ))
        if result.get("success"):
            self.log("play_intrigue", player=human.name, card=card.name)
        return result

    def _do_end_acquisition(self, d: Dict) -> Dict:
        self._human_acquisition_done = True
        self.log("end_acquisition", player=self.human_player.name)
        return {"success": True, "choices_required": []}

    def _do_resolve_choice(self, d: Dict) -> Dict:
        if self.pending_choice is None:
            return {"error": "No pending choice", **self.snapshot()}

        choice_data = self.pending_choice
        option_id = d.get("option_id", "")
        effect_resolver = self.managers["effect_resolver"]

        try:
            effect_resolver.execute_choice(self.human_player_id, choice_data, option_id)
        except Exception as e:
            return {"error": str(e), **self.snapshot()}

        self._clear_pending_choice()
        if not self.pending_choice:
            self._post_action_advance("resolve_choice")
        return self.snapshot()

    # ──────── post-action game flow ────────

    def _post_action_advance(self, action_type: str) -> None:
        """Advance the game after a human action that raised no pending choices."""
        if action_type in ("place_agent", "reveal", "resolve_choice"):
            # Run bots' agent turns (they place agents or reveal)
            self._run_bots_agent_phase()
            # Do NOT auto-advance past human acquisition:
            # when all players have revealed, the frontend will see
            # phase="acquisition" and the human must click "Done Buying"

        elif action_type == "end_acquisition":
            self._run_bot_acquisitions()
            self._run_automated_phases()
            self._start_next_round()

        # acquire_card / acquire_contract / play_intrigue: no advance needed

    def _run_bots_agent_phase(self) -> None:
        """Run bots in turn until it's the human's turn again (or all revealed)."""
        for player in self.game.players:
            if player.player_id == self.human_player_id:
                continue
            if player.has_revealed_this_round:
                continue
            if player.agents_available <= 0:
                self._bot_auto_reveal(player)
            else:
                self._bot_take_turn(player)

        # Auto-reveal human if they have no agents left
        human = self.human_player
        if not human.has_revealed_this_round and human.agents_available <= 0:
            self._human_auto_reveal()

    def _human_auto_reveal(self) -> None:
        action_exec = self.managers["action_executor"]
        result = action_exec.execute_reveal(RevealAction(player_id=self.human_player_id))
        if result.get("success"):
            self.log("auto_reveal", player=self.human_player.name,
                     persuasion=result.get("total_persuasion", 0))

    def _bot_auto_reveal(self, player: Player) -> None:
        action_exec = self.managers["action_executor"]
        result = action_exec.execute_reveal(RevealAction(player_id=player.player_id))
        if result.get("success"):
            self.log("reveal", player=player.name,
                     persuasion=result.get("total_persuasion", 0))
            choices = result.get("choices_required", [])
            if choices:
                self._bot_resolve_choices(player, choices)

    def _bot_take_turn(self, player: Player) -> None:
        bot = self.bots.get(player.player_id)
        if bot is None:
            return
        action_exec = self.managers["action_executor"]

        # ~30% chance to play a plot intrigue first
        plot_intrigues = [
            c for c in player.intrigue_cards
            if hasattr(c, "phases") and any(p.value == "Plot" for p in c.phases)
        ]
        if plot_intrigues and _random.random() < 0.3:
            card = _random.choice(plot_intrigues)
            result = action_exec.execute_play_intrigue(PlayIntrigueAction(
                player_id=player.player_id, intrigue_card=card
            ))
            if result.get("success"):
                self.log("play_intrigue", player=player.name, card=card.name)
                self._bot_resolve_choices(player, result.get("choices_required", []))

        action = bot.decide_agent_action()
        if action is None:
            self._bot_auto_reveal(player)
        else:
            result = action_exec.execute_place_agent(action)
            if result.get("success"):
                self.log("bot_action",
                         player=player.name,
                         card=action.card.name,
                         location=action.location.name,
                         troops=action.troops_to_deploy,
                         effects=self._summarize_agent_effects(action.card))
                self._bot_resolve_choices(player, result.get("choices_required", []))
            else:
                # Fallback: reveal
                self._bot_auto_reveal(player)

    def _bot_resolve_choices(self, player: Player, choices: List[Dict]) -> None:
        effect_resolver = self.managers["effect_resolver"]
        for choice_data in choices:
            ctype = choice_data.get("type", "")
            opts = choice_data.get("options", [])
            available = [o for o in opts if o.get("available", True)]

            if ctype == "choice" and available:
                chosen = _random.choice(available)
                effect_resolver.execute_choice(player.player_id, choice_data, chosen["id"])
            elif ctype in ("spy_post", "play_spy"):
                posts = choice_data.get("available_posts", [])
                if posts:
                    chosen = _random.choice(posts)
                    pid = chosen.get("post_id") if isinstance(chosen, dict) else chosen
                    effect_resolver.execute_choice(player.player_id, choice_data, pid)
            elif ctype == "influence_faction":
                factions = choice_data.get("factions", [])
                if factions:
                    effect_resolver.execute_choice(player.player_id, choice_data,
                                                   _random.choice(factions))
            elif ctype == "conditional":
                chosen_id = "accept" if _random.random() < 0.5 else "decline"
                effect_resolver.execute_choice(player.player_id, choice_data, chosen_id)
            elif ctype in ("trash_card", "discard_card"):
                cards = choice_data.get("available_cards", [])
                if cards:
                    chosen = _random.choice(cards)
                    cid = chosen.get("card", chosen).id if hasattr(
                        chosen.get("card", chosen) if isinstance(chosen, dict) else chosen, "id"
                    ) else str(chosen)
                    try:
                        effect_resolver.execute_choice(player.player_id, choice_data, cid)
                    except Exception:
                        pass
            elif ctype == "accept_contract":
                contracts = choice_data.get("available_contracts", [])
                if contracts:
                    effect_resolver.execute_choice(player.player_id, choice_data,
                                                   contracts[0].id if hasattr(contracts[0], "id") else str(contracts[0]))
            elif ctype == "recall_agent":
                locs = choice_data.get("placed_locations", [])
                if locs:
                    effect_resolver.execute_choice(player.player_id, choice_data, locs[0])
            elif ctype == "steal_intrigue":
                targets = choice_data.get("valid_targets", [])
                if targets:
                    t = _random.choice(targets)
                    effect_resolver.execute_choice(player.player_id, choice_data, t["player_id"])
            # Unknown choices: silently skip

    def _summarize_agent_effects(self, card) -> str:
        """Return a short string describing a card's agent effects."""
        effects = getattr(card, "agent_effects", []) or []
        parts = []
        for e in effects[:4]:
            t = e.get("type", "")
            amt = e.get("amount", 1)
            res = e.get("resource", "")
            if t == "resource":
                parts.append(f"+{amt} {res}")
            elif t == "draw":
                deck = e.get("deck", "")
                parts.append(f"draw {amt}{' intrigue' if deck=='intrigue' else ''}")
            elif t == "influence":
                parts.append(f"+{amt} inf")
            elif t == "victory_point":
                parts.append(f"+{amt} VP")
        return ", ".join(parts) if parts else ""

    def _run_bot_acquisitions(self) -> None:
        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]
        contract_manager = self.managers.get("contract_manager")

        for player in self.game.players:
            if player.player_id == self.human_player_id:
                continue
            bot = self.bots.get(player.player_id)
            if bot is None:
                continue

            # Buy up to 5 cards
            for _ in range(5):
                opts = action_gen.get_acquisition_options(player.player_id)
                all_cards = list(opts.get("imperium_row", [])) + list(opts.get("reserve_cards", []))
                card = bot.decide_card_to_acquire(all_cards)
                if card is None:
                    break
                source = "reserve" if card in opts.get("reserve_cards", []) else "row"
                result = action_exec.execute_acquire_card(
                    AcquireCardAction(player_id=player.player_id, card=card, source=source)
                )
                if not result.get("success"):
                    break
                self.log("acquire_card", player=player.name, card=card.name, cost=card.cost)
                self._bot_resolve_choices(player, result.get("choices_required", []))

            # 50% chance to accept a contract if slot open
            if contract_manager and len(getattr(player, "contracts_active", [])) < 2:
                row = getattr(self.game.board, "contract_row", [])
                if row and _random.random() < 0.5:
                    contract = row[0]
                    result = contract_manager.acquire_contract(player.player_id, contract)
                    if result.get("success"):
                        self.log("acquire_contract", player=player.name, contract=contract.name)

    def _run_automated_phases(self) -> None:
        """Run combat → makers → recall phases (no human input needed)."""
        phase_manager = self.managers["phase_manager"]
        deck_manager = self.managers["deck_manager"]
        combat_manager = self.managers["combat_manager"]
        contract_manager = self.managers.get("contract_manager")
        effect_resolver = self.managers["effect_resolver"]

        # ── combat ──
        if self.game.board.current_conflict:
            conflict_name = self.game.board.current_conflict.name
            try:
                # Pass intrigue_round_complete=True to skip intrigue phase (web UI handles no intrigue round)
                combat_result = combat_manager.resolve_conflict(intrigue_round_complete=True)
                if combat_result.get("success"):
                    winners = combat_result.get("winners", [])
                    winner = winners[0] if winners else ""
                    self.log("combat_resolved", winner=winner or "(tied)", conflict=conflict_name)
                    for p in self.game.players:
                        p.troops_in_conflict = 0
                        p.sandworms_in_conflict = 0
            except Exception as e:
                self.log("error", msg=f"Combat error: {e}")

        # Clear Shaddam restriction
        for p in self.game.players:
            if "no_troop_deployment_this_turn" in getattr(p, "turn_restrictions", []):
                p.turn_restrictions.remove("no_troop_deployment_this_turn")

        # ── makers (spice accumulation) ──
        try:
            makers_manager = self.managers["makers_manager"]
            makers_manager.run_makers_phase()
        except Exception:
            pass

        # ── recall ──
        for player in self.game.players:
            player.agents_available = player.total_available_agents
            player.has_revealed_this_round = False
            player.turn_restrictions = []
            player._muaddib_passive_fired_this_round = False
            player.temp_persuasion = 0

            deck_manager.draw_cards(player.player_id, 5)
            self.log("recall", player=player.name)

            # Check harvest contracts
            if contract_manager:
                try:
                    contract_manager.check_harvest_contracts(player.player_id)
                except Exception:
                    pass

    def _start_next_round(self) -> None:
        """Increment round, draw new conflict, reset acquisition flag."""
        if self._check_game_end():
            self.game.current_phase = GamePhase.GAME_OVER
            return

        self.game.current_round += 1
        self._human_acquisition_done = False
        self.log("new_round", round=self.game.current_round)

        if self.game.board.conflict_deck:
            self.game.board.current_conflict = self.game.board.conflict_deck.pop(0)
            self.log("new_conflict",
                     conflict=self.game.board.current_conflict.name
                     if self.game.board.current_conflict else "")

    def _check_game_end(self) -> bool:
        for player in self.game.players:
            if player.victory_points >= 10:
                return True
        if self.game.current_round >= 10:
            return True
        return False
