"""
Test intrigue cards 39-42 work correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.models.board import Board
from src.engine.effects.effect_resolver import EffectResolver


def test_card_39_strategic_stockpiling():
    """Test Strategic Stockpiling (Card 39) - two separate effects."""
    print("\n" + "="*80)
    print("TEST: Card 39 - Strategic Stockpiling")
    print("="*80)

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

    # Give player resources
    player.spice = 10
    player.water = 10
    player.fremen_influence = 4
    player.victory_points = 0

    game.players = [player]
    resolver = EffectResolver(game)

    # Test Effect 1: Pay 5 spice → 1 VP
    print("\n--- Effect 1: Pay 5 spice for 1 VP ---")
    effect1 = {
        "type": "action",
        "phase": "plot",
        "cost": [{"type": "resource", "resource": "spice", "amount": 5}],
        "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
    }

    result = resolver.resolve_effects("test_player", [effect1], {"phase": "plot"})
    print(f"  Result: {result.get('success')}")
    print(f"  Spice: {player.spice} (should be 5)")
    print(f"  VP: {player.victory_points} (should be 1)")

    assert player.spice == 5, "Should have spent 5 spice"
    assert player.victory_points == 1, "Should have gained 1 VP"
    print("  ✓ Effect 1 works!")

    # Test Effect 2: If 3+ Fremen influence, pay 3 water → 1 VP
    print("\n--- Effect 2: If 3+ Fremen influence, pay 3 water for 1 VP ---")
    effect2 = {
        "type": "action",
        "phase": "plot",
        "check": [{"type": "influence", "target": "fremen", "amount": 3}],
        "cost": [{"type": "resource", "resource": "water", "amount": 3}],
        "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
    }

    result = resolver.resolve_effects("test_player", [effect2], {"phase": "plot"})
    print(f"  Result: {result.get('success')}")
    print(f"  Water: {player.water} (should be 7)")
    print(f"  VP: {player.victory_points} (should be 2)")

    assert player.water == 7, "Should have spent 3 water"
    assert player.victory_points == 2, "Should have gained another VP"
    print("  ✓ Effect 2 works!")

    return True


def test_card_42_weirding_combat():
    """Test Weirding Combat (Card 42) - unconditional + conditional swords."""
    print("\n" + "="*80)
    print("TEST: Card 42 - Weirding Combat")
    print("="*80)

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

    # Give player Bene Gesserit influence
    player.bene_gesserit_influence = 4
    player.temp_swords = 0

    game.players = [player]
    resolver = EffectResolver(game)

    # Test Effect 1: Get 3 swords (unconditional)
    print("\n--- Effect 1: Get 3 swords (unconditional) ---")
    effect1 = {
        "type": "action",
        "phase": "combat",
        "reward": [{"type": "resource", "resource": "sword", "amount": 3}]
    }

    result = resolver.resolve_effects("test_player", [effect1], {"phase": "combat"})
    print(f"  Result: {result.get('success')}")
    print(f"  Swords: {player.temp_swords} (should be 3)")

    assert player.temp_swords == 3, "Should have 3 swords"
    print("  ✓ Effect 1 works!")

    # Test Effect 2: If 3+ BG influence, get 2 more swords
    print("\n--- Effect 2: If 3+ BG influence, get 2 more swords ---")
    effect2 = {
        "type": "action",
        "phase": "combat",
        "check": [{"type": "influence", "target": "bene_gesserit", "amount": 3}],
        "reward": [{"type": "resource", "resource": "sword", "amount": 2}]
    }

    result = resolver.resolve_effects("test_player", [effect2], {"phase": "combat"})
    print(f"  Result: {result.get('success')}")
    print(f"  Swords: {player.temp_swords} (should be 5)")

    assert player.temp_swords == 5, "Should have 5 swords total (3+2)"
    print("  ✓ Effect 2 works!")

    # Test with insufficient influence
    print("\n--- Test with insufficient BG influence ---")
    player2 = Player(
        player_id="test_player2",
        name="Test2",
        color="red",
        leader=None,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )
    player2.bene_gesserit_influence = 2  # Not enough
    player2.temp_swords = 0
    game.players.append(player2)

    # Effect 1 should still work
    result = resolver.resolve_effects("test_player2", [effect1], {"phase": "combat"})
    assert player2.temp_swords == 3, "Should still get base 3 swords"

    # Effect 2 should not trigger (check fails)
    result = resolver.resolve_effects("test_player2", [effect2], {"phase": "combat"})
    print(f"  Player with 2 BG influence - swords: {player2.temp_swords} (should still be 3)")
    assert player2.temp_swords == 3, "Should not get bonus swords"
    print("  ✓ Check requirement works correctly!")

    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("INTRIGUE CARDS 39-42 TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_card_39_strategic_stockpiling,
        test_card_42_weirding_combat,
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
        print("\n✓ ALL INTRIGUE CARD TESTS PASSED!")
        print("\nIntrigue Cards 39-42:")
        print("  ✓ Strategic Stockpiling (two separate effects)")
        print("  ✓ Weirding Combat (unconditional + conditional)")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        sys.exit(1)
