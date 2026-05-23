"""Check which _handle_choice method is in the handlers dict."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game
from src.models.board import Board
from src.engine.effects.effect_resolver import EffectResolver


def test_which():
    game = Game()
    game.board = Board()
    resolver = EffectResolver(game)

    choice_handler = resolver.handlers.get("choice")
    print(f"Choice handler: {choice_handler}")
    print(f"Function name: {choice_handler.__name__}")
    print(f"Line number (approx): {choice_handler.__code__.co_firstlineno}")
    print(f"Docstring preview: {choice_handler.__doc__[:100] if choice_handler.__doc__ else 'None'}...")


if __name__ == "__main__":
    test_which()
