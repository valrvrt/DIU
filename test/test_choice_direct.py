"""Test choice effect directly."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.models.board import Board
from src.engine.effects.effect_resolver import EffectResolver


def test_choice_direct():
    # Create game
    game = Game()
    game.board = Board()

    player = Player(
        player_id="test_player",
        name="Test",
        color="blue",
        leader=None,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    game.players = [player]
    resolver = EffectResolver(game)

    # Test choice effect directly
    choice_effect = {
        "id": 1,
        "type": "choice",
        "required": True,
        "options": [
            {
                "id": "trash",
                "cost": [{"type": "resource", "resource": "solari", "amount": 1}],
                "reward": [{"type": "trash", "deck": ["hand", "played"], "amount": 1}]
            },
            {
                "id": "spy",
                "reward": [{"type": "play", "unit": "spy", "amount": 1}]
            }
        ]
    }

    print("Resolving choice effect directly:")
    result = resolver.resolve_effects(
        "test_player",
        [choice_effect],
        {"phase": "reveal"}
    )

    print(f"Result: {result}")
    print(f"Choices required: {result.get('choices_required', [])}")


if __name__ == "__main__":
    test_choice_direct()
