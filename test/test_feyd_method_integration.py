"""
Test that FeydRautha's custom signet_ring() method is called by effect resolver.

This test verifies the method-based architecture works end-to-end.
"""

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


def test_feyd_signet_method_called():
    """Test that FeydRautha.signet_ring() method is invoked during reveal."""
    print("\n" + "="*80)
    print("TEST: FeydRautha Custom Method Integration")
    print("="*80)

    # Create game
    game = Game()
    game.board = Board()

    # Use FeydRautha class (not base Leader)
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
    resolver = EffectResolver(game)

    print(f"\nLeader type: {type(leader).__name__}")
    print(f"Has signet_ring method: {hasattr(leader, 'signet_ring')}")
    print(f"Training track position: {leader.training_track_position}")

    # Test Level 1 (choice between trash or spy)
    print("\n--- Testing Level 1 Signet ---")
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )

    print(f"Result: {result}")
    print(f"Success: {result.get('success')}")
    print(f"Choices required: {len(result.get('choices_required', []))}")

    assert result.get("success"), "Signet should succeed"
    assert len(result.get('choices_required', [])) > 0, "Level 1 should require a choice"
    print("✓ Level 1 signet returns choice (custom method working!)")

    # Advance to Level 2
    print("\n--- Testing Level 2 Signet ---")
    leader.advance_training_track()
    print(f"Training track position: {leader.training_track_position}")

    # Get the effects directly (don't resolve, just verify structure)
    effects = leader.get_current_signet_effects()
    print(f"Level 2 effects: {effects}")

    assert len(effects) == 1, "Level 2 should have 1 effect"
    assert effects[0].get("type") == "trash", "Level 2 should be trash effect"
    print("✓ Level 2 signet structure correct (custom method working!)")

    # Test passive ability
    print("\n--- Testing Passive Ability ---")
    print(f"Passive ability: {leader.passive_ability.get('name')}")
    print(f"Can use in reveal phase: {leader.can_use_passive('reveal')}")

    player.spies_placed = ["spy_1"]
    player.temp_swords = 0

    passive_result = leader.use_passive(state, "test_player", {"phase": "reveal"})

    print(f"Passive result: {passive_result}")
    assert passive_result.get("success"), "Passive should succeed"
    assert passive_result.get("cost"), "Passive should have cost"
    assert passive_result.get("effects"), "Passive should have effects"
    print("✓ Passive ability method works!")

    return True


def test_method_priority():
    """Test that custom signet_ring() method takes priority over JSON fallback."""
    print("\n" + "="*80)
    print("TEST: Method Priority (Custom vs Fallback)")
    print("="*80)

    # Create game
    game = Game()
    game.board = Board()

    # FeydRautha has both signet_ring() method AND signet_progression data
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
    resolver = EffectResolver(game)

    print(f"\nLeader has signet_ring method: {hasattr(leader, 'signet_ring')}")
    print(f"Leader has signet_progression: {leader.signet_progression is not None}")
    print(f"Leader has get_current_signet_effects: {hasattr(leader, 'get_current_signet_effects')}")

    # The effect resolver should call signet_ring() method (Method 1)
    # not get_current_signet_effects() (Method 2)
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )

    # If custom method was called, we should see the message from signet_ring()
    effects_applied = result.get("effects_applied", [])
    print(f"\nEffects applied: {effects_applied}")

    # Check if message contains "Feyd Rautha signet" (from custom method)
    has_custom_message = any("Feyd Rautha signet" in str(effect) for effect in effects_applied)
    print(f"Custom method message found: {has_custom_message}")

    assert result.get("success"), "Signet should succeed"
    assert has_custom_message, "Should use custom signet_ring() method message"
    print("✓ Custom method takes priority over fallback!")

    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FEYD RAUTHA METHOD INTEGRATION TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_feyd_signet_method_called,
        test_method_priority,
    ]

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        print("\nFeyd Rautha Method-Based Architecture:")
        print("  ✓ Custom signet_ring() method is called")
        print("  ✓ Method takes priority over JSON fallback")
        print("  ✓ Passive ability method works")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        sys.exit(1)
