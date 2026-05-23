"""Test if _handle_choice is being called."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.models.board import Board
from src.engine.effects.effect_resolver import EffectResolver


# Monkey patch to trace
original_handle_choice = EffectResolver._handle_choice


def traced_handle_choice(self, player_id, effect, context):
    print(f"\n_handle_choice called!")
    print(f"  player_id: {player_id}")
    print(f"  effect: {effect}")
    print(f"  context: {context}")
    result = original_handle_choice(self, player_id, effect, context)
    print(f"  result: {result}")
    return result


EffectResolver._handle_choice = traced_handle_choice


def test_trace():
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

    # Test choice effect
    choice_effect = {
        "type": "choice",
        "required": True,
        "options": [
            {
                "id": "option1",
                "reward": [{"type": "resource", "resource": "solari", "amount": 2}]
            }
        ]
    }

    print("="*80)
    print("Testing choice effect")
    print("="*80)

    result = resolver.resolve_effects(
        "test_player",
        [choice_effect],
        {"phase": "reveal"}
    )

    print("\n" + "="*80)
    print("FINAL RESULT")
    print("="*80)
    print(f"Result: {result}")


if __name__ == "__main__":
    test_trace()
