"""Debug test to trace signet resolution."""

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


def test_debug():
    # Create game
    game = Game()
    game.board = Board()

    leader = FeydRautha()
    print(f"Leader type: {type(leader).__name__}")
    print(f"Has signet_ring: {hasattr(leader, 'signet_ring')}")
    print(f"signet_ring callable: {callable(getattr(leader, 'signet_ring', None))}")

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

    # Call signet_ring directly
    print("\n--- Direct signet_ring() call ---")
    signet_result = leader.signet_ring(state, "test_player", {"phase": "reveal"})
    print(f"signet_ring result: {signet_result}")
    print(f"Effects returned: {signet_result.get('effects')}")

    # Now resolve through effect resolver
    print("\n--- Through effect resolver ---")
    resolver = EffectResolver(game)
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )
    print(f"Effect resolver result: {result}")


if __name__ == "__main__":
    test_debug()
