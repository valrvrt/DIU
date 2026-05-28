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

    # available_cards: list of {"card": ImperiumCard|IntrigueCard, "source": str}
    if "available_cards" in result:
        def _safe_card(card):
            if hasattr(card, "factions"):  # ImperiumCard
                return _imperium_card(card)
            if hasattr(card, "id") and hasattr(card, "name"):  # IntrigueCard or others
                return {"id": str(card.id), "name": card.name,
                        "cost": getattr(card, "cost", 0),
                        "type": type(card).__name__}
            return {"id": str(card), "name": str(card)}
        result["available_cards"] = [
            {"card": _safe_card(item["card"]), "source": item.get("source", "")}
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
        # Count of pending contract-accept tokens earned this turn
        # (from placing on Accept Contract space or card effects)
        self._pending_contract_accepts: int = 0
        # When set, the human just placed an agent on a combat space and
        # needs to choose how many troops to deploy from garrison.
        # Shape: {"location_name": str, "max_troops": int, "bonus": int}
        self._pending_troop_deployment: Optional[Dict[str, Any]] = None
        # History of resolved conflicts for UI display
        self._conflict_history: List[Dict[str, Any]] = []

    # ──────── construction ────────

    @classmethod
    def new(cls, player_count: int = 3, human_name: str = "Player",
            selected_leaders: Optional[List[int]] = None) -> "GameSession":
        if player_count not in (3, 4):
            raise ValueError("player_count must be 3 or 4")

        # If only the human's leader was provided, fill in random bot leaders
        if selected_leaders and len(selected_leaders) == 1:
            from src.loaders.leader_loader import load_leaders
            human_lid = selected_leaders[0]
            all_leaders = [l for l in load_leaders() if l.name != "Reverend Mother"]
            others = [l for l in all_leaders if l.leader_id != human_lid]
            bot_leaders = _random.sample(others, player_count - 1)
            selected_leaders = [human_lid] + [l.leader_id for l in bot_leaders]

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
        action_gen = self.managers["action_generator"]
        phase = self.game.current_phase.value if hasattr(self.game.current_phase, "value") \
                else str(self.game.current_phase)

        if self.pending_choice:
            # Preserve the underlying game phase so the UI can still show
            # context (e.g. keep showing the Done button during acquisition).
            underlying = "acquisition" if human.has_revealed_this_round else "agent_turn"
            return {"phase": "choice", "underlying_phase": underlying,
                    "pending_choice": self.pending_choice}

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
                "can_accept_contract": self._pending_contract_accepts > 0,
            }

        return {"phase": phase}

    def snapshot(self) -> Dict[str, Any]:
        state = serialize_state(self.game, viewer_player_id=self.human_player_id)
        state["available_actions"] = self._compute_available_actions()
        return {
            "state": state,
            "pending_choice": self.pending_choice,
            "pending_troop_deployment": self._pending_troop_deployment,
            "is_human_turn": self.is_human_turn,
            "events": self.drain_log(),
            "conflict_history": self._conflict_history,
        }

    # ──────── choice queue management ────────

    def _queue_choices(self, choices: List[Dict]) -> None:
        if not choices:
            return
        safe = [_make_choice_json_safe(c) for c in choices]
        # Count accept_contract choices — player earns one token per accept effect
        for c in safe:
            if c.get("type") == "accept_contract":
                self._pending_contract_accepts += 1
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
        if self._pending_troop_deployment and action_type != "deploy_troops":
            return {"error": "Must deploy troops first", **self.snapshot()}

        dispatch = {
            "place_agent": self._do_place_agent,
            "deploy_troops": self._do_deploy_troops,
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
        action_exec = self.managers["action_executor"]
        human = self.human_player

        card_id = d.get("card_id", "")
        location_id = str(d.get("location_id", ""))

        card = next((c for c in human.hand.cards if c.id == card_id), None)
        if card is None:
            return {"success": False, "error": f"Card {card_id} not in hand"}

        location = self.game.board.get_space_by_id(location_id)
        if location is None:
            try:
                location = self.game.board.get_space_by_id(int(location_id))
            except Exception:
                pass
        if location is None:
            return {"success": False, "error": f"Location {location_id} not found"}

        # Always pass troops_to_deploy=0 so location rewards (including troop
        # bonuses like Arrakeen's +1) are applied BEFORE the player picks how
        # many troops to deploy from garrison.
        action = PlaceAgentAction(
            player_id=self.human_player_id,
            card=card,
            location=location,
            placement_type=location.agent_icon,
            troops_to_deploy=0,
        )
        result = action_exec.execute_place_agent(action)
        if result.get("success"):
            self.log("place_agent", player=human.name, card=card.name, location=location.name)
            # If this is a combat space, queue a pending troop deployment prompt
            if location.is_combat_space:
                # Bonus deployable troops from location's reward (e.g. Arrakeen +1)
                bonus = sum(
                    e.get("amount", 0) for e in (location.reward or [])
                    if isinstance(e, dict)
                    and e.get("type") == "resource"
                    and e.get("resource") in ("troop", "troops")
                )
                # Standard rule allows up to 2 from garrison per agent;
                # Arrakeen-style bonus increases that cap by N.
                max_troops = min(2 + bonus, human.troops_in_garrison)
                if max_troops > 0:
                    self._pending_troop_deployment = {
                        "location_name": location.name,
                        "max_troops": max_troops,
                        "bonus": bonus,
                    }
        return result

    def _do_deploy_troops(self, d: Dict) -> Dict:
        if not self._pending_troop_deployment:
            return {"success": False, "error": "No troop deployment pending"}
        action_exec = self.managers["action_executor"]
        num = max(0, int(d.get("troops", 0)))
        max_troops = self._pending_troop_deployment.get("max_troops", 0)
        if num > max_troops:
            return {"success": False, "error": f"Cannot deploy more than {max_troops} troops"}
        result = action_exec.deploy_troops_to_conflict(self.human_player_id, num)
        if result.get("success"):
            if num > 0:
                self.log("deploy_troops", player=self.human_player.name,
                         count=num, location=self._pending_troop_deployment.get("location_name"))
            self._pending_troop_deployment = None
            # After deploying, complete the turn (auto-reveal if no agents left)
            self._run_bots_agent_phase()
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
        source = d.get("source", "row") or "row"

        # Find card in imperium_row or reserve
        card = next((c for c in self.game.board.imperium_row if c.id == card_id), None)
        if card is None and self.game.board.reserve_prepare_the_way:
            top = self.game.board.reserve_prepare_the_way[0]
            if top.id == card_id:
                card, source = top, "prepare"   # execute_acquire_card expects "prepare"
        if card is None and self.game.board.reserve_spice_must_flow:
            top = self.game.board.reserve_spice_must_flow[0]
            if top.id == card_id:
                card, source = top, "spice"     # execute_acquire_card expects "spice"

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

        # Must have earned the right to accept a contract this turn
        if self._pending_contract_accepts <= 0:
            return {"success": False, "error": "You need to trigger an 'Accept Contract' effect first (place an agent on the Accept Contract space)"}

        contract_id = str(d.get("contract_id", ""))
        contract = next(
            (c for c in self.game.board.contract_row if str(c.id) == contract_id), None
        )
        if contract is None:
            return {"success": False, "error": f"Contract {contract_id} not available"}

        result = contract_manager.acquire_contract(self.human_player_id, contract)
        if result.get("success"):
            self._pending_contract_accepts -= 1  # consume the token
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

        # If this was an accept_contract choice, consume the pending token
        if choice_data.get("type") == "accept_contract":
            self._pending_contract_accepts = max(0, self._pending_contract_accepts - 1)

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
        """Run bots in turn order.

        If the human still has agents to place, each bot takes exactly ONE step
        (place one agent, or auto-reveal if they have none left).  This keeps
        turns interleaved: human → bots (once each) → human → bots (once each).

        Once the human has already revealed, we run all bots to completion so
        the round can finish.
        """
        human = self.human_player

        if human.has_revealed_this_round:
            # Human is done placing agents; drain all remaining bot turns.
            max_passes = 15
            for _ in range(max_passes):
                any_pending = False
                for player in self.game.players:
                    if player.player_id == self.human_player_id:
                        continue
                    if player.has_revealed_this_round:
                        continue
                    any_pending = True
                    if player.agents_available <= 0:
                        self._bot_auto_reveal(player)
                    else:
                        self._bot_take_turn(player)
                if not any_pending:
                    break
        else:
            # Human still has agents: each bot takes exactly ONE turn.
            for player in self.game.players:
                if player.player_id == self.human_player_id:
                    continue
                if player.has_revealed_this_round:
                    continue
                if player.agents_available <= 0:
                    self._bot_auto_reveal(player)
                else:
                    self._bot_take_turn(player)
                    # If that was their last agent, reveal them immediately.
                    if player.agents_available <= 0 and not player.has_revealed_this_round:
                        self._bot_auto_reveal(player)

        # Auto-reveal the human if they have no agents left.
        # Skip if troop deployment is still pending — it will trigger another
        # call to this function after the player responds to the picker.
        if (not human.has_revealed_this_round
                and human.agents_available <= 0
                and not self._pending_troop_deployment):
            self._human_auto_reveal()

    def _human_auto_reveal(self) -> None:
        self._pending_troop_deployment = None  # can't deploy after auto-reveal
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
                imperium = list(opts.get("imperium_row", []))
                reserve_prepare = list(opts.get("reserve_prepare", []))
                reserve_spice   = list(opts.get("reserve_spice", []))
                reserve_cards   = reserve_prepare + reserve_spice
                all_cards = imperium + reserve_cards
                card = bot.decide_card_to_acquire(all_cards)
                if card is None:
                    break
                # Determine source based on which pile the card came from
                if card in reserve_prepare:
                    source = "prepare"
                elif card in reserve_spice:
                    source = "spice"
                else:
                    source = "row"
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
                    # Build per-player strength summary for the UI
                    strength_summary = []
                    for p in self.game.players:
                        ps = combat_result.get("player_strengths", {}).get(p.player_id, {})
                        strength_summary.append({
                            "name": p.name,
                            "strength": ps.get("total_strength", 0),
                            "is_human": getattr(p, "is_human", False),
                        })
                    # Sort by strength desc
                    strength_summary.sort(key=lambda x: -x["strength"])
                    self.log("combat_resolved",
                             winner=winner or "(tied)",
                             conflict=conflict_name,
                             strength_summary=strength_summary,
                             tied=len(winners) == 0)
                    # Record in conflict history
                    conflict_card = self.game.board.resolved_conflicts[-1] if self.game.board.resolved_conflicts else None
                    history_entry = {
                        "round": self.game.current_round,
                        "name": conflict_name,
                        "level": getattr(conflict_card, "level", 0) if conflict_card else 0,
                        "winner": winner or "(tied)",
                        "tied": len(winners) == 0,
                        "rewards": {},
                        "worm_players": [],
                    }
                    # Collect per-rank rewards and worm info
                    for rd in combat_result.get("rewards", []):
                        if rd.get("sandworm_doubled"):
                            history_entry["worm_players"].append(rd["player"])
                        rank_k = str(rd["rank"])
                        history_entry["rewards"].setdefault(rank_k, [])
                        history_entry["rewards"][rank_k].append({
                            "player": rd["player"],
                            "sandworm_doubled": rd.get("sandworm_doubled", False),
                        })
                    self._conflict_history.append(history_entry)
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
            result = makers_manager.execute_makers_phase()
            if result.get("total_bonus_added", 0) > 0:
                self.log("makers", spaces=[s["space"] for s in result.get("spaces_updated", [])])
        except Exception as e:
            self.log("error", msg=f"Makers error: {e}")

        # Reset per-round tokens
        self._pending_contract_accepts = 0
        self._pending_troop_deployment = None

        # ── recall ──
        for player in self.game.players:
            # Discard played cards → discard pile
            try:
                deck_manager.discard_played_cards(player.player_id)
            except Exception:
                pass
            # Discard remaining hand → discard pile
            try:
                deck_manager.discard_hand(player.player_id)
            except Exception:
                pass

            # Reset state
            player.agents_available = player.total_available_agents
            player.has_revealed_this_round = False
            player.turn_restrictions = []
            player._muaddib_passive_fired_this_round = False
            player.temp_persuasion = 0
            player.temp_swords = 0

            # Draw new hand of 5 (auto-shuffles discard if deck is empty)
            deck_manager.draw_cards(player.player_id, 5)
            self.log("recall", player=player.name)

            # Check harvest contracts
            if contract_manager:
                try:
                    contract_manager.check_harvest_contracts(player.player_id)
                except Exception:
                    pass

        # Clear all board space occupants for the next round
        if self.game.board:
            for space in self.game.board.spaces:
                space.occupied_by = None
                if hasattr(space, 'agents_placed'):
                    space.agents_placed = []

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
