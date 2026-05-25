#!/usr/bin/env python3
"""
Test spy placement during on_acquire_effects.
Skipped: uses old Game() constructor API (pre-GameSetup refactor).
"""

import pytest
pytestmark = pytest.mark.skip(reason="Uses obsolete Game() constructor API")

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_spy_on_acquire():
    """Test spy placement via on_acquire_effects."""

    # Create a test game
    game = Game()
    players_config = [
        {"name": "Test Player", "type": "human"},
        {"name": "Bot", "type": "bot"}
    ]
    game.setup(players_config)
    state = GameState(game)
    resolver = EffectResolver(game, state)

    player = game.players[0]
    player_id = player.player_id

    # Print initial spy state
    print("\n" + "="*60)
    print("TESTING SPY PLACEMENT ON ACQUIRE")
    print("="*60)
    print(f"\nInitial state:")
    print(f"  Spies available: {player.spies_available}")
    print(f"  Spies placed: {player.spies_placed if hasattr(player, 'spies_placed') else 'N/A'}")

    # Define spy placement effect (as found in on_acquire_effects)
    on_acquire_effects = [
        {
            "type": "play",
            "unit": "spy",
            "amount": 1
        }
    ]

    # Resolve the effect
    context = {
        "card": "Test Card",
        "phase": "acquire",
        "player_id": player_id
    }

    print(f"\nResolving on_acquire spy placement effect...")
    result = resolver.resolve_effects(player_id, on_acquire_effects, context)

    print(f"\nResult:")
    print(f"  Success: {result.get('success')}")
    print(f"  Choices required: {result.get('choices_required')}")
    print(f"  Error: {result.get('error', 'None')}")

    if result.get('applied_effects'):
        print(f"  Applied effects: {result.get('applied_effects')}")

    print(f"\nFinal state:")
    print(f"  Spies available: {player.spies_available}")
    print(f"  Spies placed: {player.spies_placed if hasattr(player, 'spies_placed') else 'N/A'}")

    # Verify the spy was actually placed
    expected_spies = 2  # Started with 3, placed 1
    if player.spies_available == expected_spies:
        if hasattr(player, 'spies_placed') and len(player.spies_placed) == 1:
            print(f"\n✓ SUCCESS: Spy was placed on observation post {player.spies_placed[0]}")
        else:
            print(f"\n✗ FAIL: Spy count decreased but spy not tracked in spies_placed!")
    else:
        print(f"\n✗ FAIL: Expected {expected_spies} spies available, got {player.spies_available}")

    print("="*60 + "\n")

if __name__ == "__main__":
    test_spy_on_acquire()
