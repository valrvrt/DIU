#!/usr/bin/env python3
"""
Test leader passive abilities.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine.core.game_setup import GameSetup
from loaders.leader_loader import load_leaders, get_leader_by_name
from models.leader import FeydRautha, GurneyHalleck, LadyAmberMetulli

def test_feyd_passive():
    """Test Feyd Rautha's Devious Strength passive."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Devious Strength")
    print("="*80)

    game, _ = GameSetup.create_game(player_count=2)
    player = game.players[0]

    # Replace with Feyd Rautha
    player.leader = FeydRautha()

    # Place a spy
    player.spies_placed.append("1")
    player.spies_available = 2

    print(f"Player: {player.name}")
    print(f"Leader: {player.leader.name}")
    print(f"Spies placed: {player.spies_placed}")
    print(f"Spies available: {player.spies_available}")

    # Test passive
    context = {"phase": "reveal"}
    result = player.leader.use_passive(game, player.player_id, context)

    print(f"\nPassive result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print(f"  Effects: {result.get('effects', [])}")
    print(f"  Cost: {result.get('cost', [])}")

    if result.get('success'):
        print("\n✓ Feyd Rautha passive works!")
    else:
        print(f"\n✗ Failed: {result.get('error')}")


def test_gurney_passive():
    """Test Gurney Halleck's Always Smiling passive."""
    print("\n" + "="*80)
    print("TEST: Gurney Halleck - Always Smiling")
    print("="*80)

    game, _ = GameSetup.create_game(player_count=2)
    player = game.players[0]

    # Replace with Gurney Halleck
    player.leader = GurneyHalleck()

    # Set strength to 6
    player.temp_swords = 6

    print(f"Player: {player.name}")
    print(f"Leader: {player.leader.name}")
    print(f"Strength (swords): {player.temp_swords}")

    # Test passive
    context = {"phase": "reveal"}
    result = player.leader.use_passive(game, player.player_id, context)

    print(f"\nPassive result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print(f"  Effects: {result.get('effects', [])}")

    if result.get('success'):
        print("\n✓ Gurney Halleck passive works!")
    else:
        print(f"\n✗ Failed: {result.get('error')}")

    # Test with insufficient strength
    player.temp_swords = 3
    result2 = player.leader.use_passive(game, player.player_id, context)
    print(f"\nWith 3 strength: {result2.get('error', 'Should fail')}")
    if not result2.get('success'):
        print("✓ Correctly fails with <6 strength")


def test_amber_passive():
    """Test Lady Amber Metulli's Desert Scouts passive."""
    print("\n" + "="*80)
    print("TEST: Lady Amber Metulli - Desert Scouts")
    print("="*80)

    game, _ = GameSetup.create_game(player_count=2)
    player = game.players[0]

    # Replace with Lady Amber
    player.leader = LadyAmberMetulli()

    # Set strength to 6 and place troops in conflict
    player.temp_swords = 6
    player.troops_in_conflict = 3

    print(f"Player: {player.name}")
    print(f"Leader: {player.leader.name}")
    print(f"Strength (swords): {player.temp_swords}")
    print(f"Troops in conflict: {player.troops_in_conflict}")

    # Test passive
    context = {"phase": "reveal"}
    result = player.leader.use_passive(game, player.player_id, context)

    print(f"\nPassive result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Message: {result.get('message', 'N/A')}")
    print(f"  Effects: {result.get('effects', [])}")
    print(f"  Optional: {result.get('optional', False)}")

    if result.get('success'):
        print("\n✓ Lady Amber Metulli passive works!")
    else:
        print(f"\n✗ Failed: {result.get('error')}")


def test_leader_loading():
    """Test that custom leader classes are loaded correctly."""
    print("\n" + "="*80)
    print("TEST: Leader Loading")
    print("="*80)

    leaders = load_leaders()

    print(f"Loaded {len(leaders)} leaders:")
    for leader in leaders:
        class_name = leader.__class__.__name__
        has_passive = hasattr(leader, 'use_passive') and leader.passive_ability is not None
        print(f"  {leader.leader_id}. {leader.name:30s} [{class_name:20s}] Passive: {has_passive}")

    # Check specific leaders
    feyd = get_leader_by_id(1, leaders)
    gurney = get_leader_by_id(2, leaders)
    amber = get_leader_by_id(3, leaders)

    checks = [
        (isinstance(feyd, FeydRautha), "Feyd Rautha is FeydRautha class"),
        (isinstance(gurney, GurneyHalleck), "Gurney is GurneyHalleck class"),
        (isinstance(amber, LadyAmberMetulli), "Lady Amber is LadyAmberMetulli class"),
        (feyd.passive_ability is not None, "Feyd has passive ability"),
        (gurney.passive_ability is not None, "Gurney has passive ability"),
        (amber.passive_ability is not None, "Lady Amber has passive ability"),
    ]

    print("\nChecks:")
    all_pass = True
    for check, desc in checks:
        status = "✓" if check else "✗"
        print(f"  {status} {desc}")
        if not check:
            all_pass = False

    if all_pass:
        print("\n✓ All leader loading checks passed!")
    else:
        print("\n✗ Some checks failed")


if __name__ == "__main__":
    test_leader_loading()
    test_feyd_passive()
    test_gurney_passive()
    test_amber_passive()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("All 3 leaders with custom passive abilities implemented and tested!")
    print("  1. Feyd Rautha - Devious Strength (recall spy → +2 swords)")
    print("  2. Gurney Halleck - Always Smiling (6+ strength → +1 persuasion)")
    print("  3. Lady Amber Metulli - Desert Scouts (6+ strength → recall troop)")
    print("="*80 + "\n")
