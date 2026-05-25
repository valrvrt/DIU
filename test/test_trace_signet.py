"""Trace signet resolution with detailed output."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.leader import FeydRautha
from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.models.board import Board
from src.engine.core.game_state import GameState
from src.engine.effects.effect_resolver import EffectResolver


def test_trace():
    # Create game
    game = Game()
    game.board = Board()

    leader = FeydRautha()

    player = Player(
        player_id="test_player",
        name="Feyd",
        color="blue",
        leader=leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    game.players = [player]
    state = GameState(game)

    print("="*80)
    print("TRACING SIGNET RESOLUTION")
    print("="*80)

    resolver = EffectResolver(game)
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )

    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    print(f"Result: {result}")


if __name__ == "__main__":
    test_trace()
