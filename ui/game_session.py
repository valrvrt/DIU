"""GameSession — wraps the engine for the web UI.

Mirrors SimpleCLI.setup_game() but with no display logic. Owns:
  - the Game instance
  - all managers (Phase, Deck, Combat, Makers, Influence, VP, Contract,
    EffectResolver, ActionGenerator, ActionExecutor)
  - bots for non-human players
  - a rolling event log so the frontend can show what bots just did

Pure Python. No I/O. The API layer (Phase 2) calls into this.
"""

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
from src.engine.actions.action_executor import ActionExecutor
from src.engine.effects.effect_resolver import EffectResolver
from src.models.game import Game, GamePhase
from src.models.player import Player
from src.bots import HeuristicBot

from .serializer import serialize_state


class GameSession:
    """
    Owns one game's worth of state for the duration of a play session.

    Construction is the single setup step: call GameSession.new() to build
    a fresh game with managers + bots wired up. After that, state mutates
    in place as actions are executed.
    """

    def __init__(self, game: Game, managers: Dict[str, Any], bots: Dict[str, Any],
                 human_player_id: str):
        self.game = game
        self.managers = managers
        self.bots = bots
        self.human_player_id = human_player_id
        # Rolling list of human-readable strings describing recent events.
        # Frontend reads this to show an activity feed.
        self.event_log: List[Dict[str, Any]] = []
        # Pending choice — set when an action returns choices_required.
        # The frontend must POST /action {type: "resolve_choice", ...} next.
        self.pending_choice: Optional[Dict[str, Any]] = None

    # ───────────────── construction ─────────────────

    @classmethod
    def new(cls, player_count: int = 3, human_name: str = "Player",
            selected_leaders: Optional[List[int]] = None) -> "GameSession":
        """
        Build a fresh game with all managers + bots ready to play.

        Mirrors SimpleCLI.setup_game() — same manager order, same wiring.
        """
        if player_count not in (3, 4):
            raise ValueError("player_count must be 3 or 4")

        game, _setup_info = GameSetup.create_game(
            player_count=player_count,
            human_player_name=human_name,
            selected_leaders=selected_leaders,
        )

        # Mark seat 0 as the human (matches SimpleCLI convention).
        human_player = game.players[0]
        human_player.is_human = True
        for p in game.players[1:]:
            p.is_human = False

        # Managers — order matters for cross-references.
        deck_manager = DeckManager(game)
        influence_manager = InfluenceManager(game)
        victory_point_manager = VictoryPointManager(game)
        effect_resolver = EffectResolver(game, influence_manager=influence_manager)
        combat_manager = CombatManager(
            game,
            effect_resolver=effect_resolver,
            victory_point_manager=victory_point_manager,
        )
        makers_manager = MakersManager(game)
        phase_manager = PhaseManager(
            game,
            deck_manager=deck_manager,
            combat_manager=combat_manager,
            makers_manager=makers_manager,
        )
        action_generator = ActionGenerator(game, phase_manager, effect_resolver)
        action_executor = ActionExecutor(game, phase_manager, deck_manager, effect_resolver)
        contract_manager = ContractManager(game)

        managers = {
            "phase_manager": phase_manager,
            "deck_manager": deck_manager,
            "combat_manager": combat_manager,
            "makers_manager": makers_manager,
            "action_generator": action_generator,
            "action_executor": action_executor,
            "influence_manager": influence_manager,
            "victory_point_manager": victory_point_manager,
            "effect_resolver": effect_resolver,
            "contract_manager": contract_manager,
            "game": game,
        }

        # Bots for everyone except the human (seat 0).
        bots: Dict[str, Any] = {}
        for p in game.players[1:]:
            bots[p.player_id] = HeuristicBot(p, managers)

        # Bring game out of SETUP so it's playable.
        game.current_phase = GamePhase.PLAYER_TURNS
        game.current_round = 1
        if game.board.conflict_deck:
            game.board.current_conflict = game.board.conflict_deck.pop(0)

        return cls(
            game=game,
            managers=managers,
            bots=bots,
            human_player_id=human_player.player_id,
        )

    # ───────────────── convenience properties ─────────

    @property
    def human_player(self) -> Player:
        return self.game.get_player(self.human_player_id)

    @property
    def is_human_turn(self) -> bool:
        return (
            self.game.current_phase == GamePhase.PLAYER_TURNS
            and self.game.current_player.player_id == self.human_player_id
        )

    # ───────────────── event log ────────────────────

    def log(self, event_type: str, **fields) -> None:
        """Append a structured event the frontend can render."""
        entry = {"type": event_type}
        entry.update(fields)
        self.event_log.append(entry)
        # Cap log length so we don't grow unbounded.
        if len(self.event_log) > 200:
            self.event_log = self.event_log[-200:]

    def drain_log(self) -> List[Dict[str, Any]]:
        """Return + clear the event log. Frontend gets events once."""
        events = self.event_log
        self.event_log = []
        return events

    # ───────────────── state snapshot ───────────────

    def snapshot(self) -> Dict[str, Any]:
        """
        Return the full state envelope the frontend renders from.

        Includes: serialized game state (private view for human), pending
        choice (if any), and any new events accumulated since last snapshot.
        """
        return {
            "state": serialize_state(self.game, viewer_player_id=self.human_player_id),
            "pending_choice": self.pending_choice,
            "is_human_turn": self.is_human_turn,
            "events": self.drain_log(),
        }
