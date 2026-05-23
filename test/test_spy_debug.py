"""Debug spy placement."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.setup.game_setup import GameSetup
from src.engine.effects.effect_resolver import EffectResolver

# Create game
game, setup_info = GameSetup.create_game(player_count=2)
player = game.players[0]

# Initialize spy resources
player.spies_available = 3

# Create effect resolver
resolver = EffectResolver(game)

# Test spy placement effect
effect = {
    "type": "play",
    "unit": "spy",
    "amount": 2
}

context = {
    "card": "Covert Operation",
    "phase": "reveal",
    "player_id": player.player_id
}

print(f"Before: spies_available={player.spies_available}, spies_placed={player.spies_placed}")
print(f"Board has {len(game.board.observation_posts)} observation posts")

result = resolver.resolve_effects(player.player_id, [effect], context)

print(f"Result: {result}")
print(f"After: spies_available={player.spies_available}, spies_placed={player.spies_placed}")
