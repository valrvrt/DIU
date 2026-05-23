"""
Test Feyd Rautha's branching signet progression.

Level 3 has two paths:
- Trash option → skip level 3.1, go straight to level 4 (at position 3)
- Spy option → go through level 3.1 first (gain 2 spice), then level 4 (at position 4)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.leader import FeydRautha


def test_level_3_branching():
    """Test that level 3 choice affects subsequent progression."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Level 3 Branching Progression")
    print("="*80)

    leader = FeydRautha()

    # Advance to position 2 (Level 3)
    leader.training_track_position = 2
    print(f"\nPosition 2 (Level 3):")
    effects = leader.get_current_signet_effects()
    print(f"  Effects: {effects[0] if effects else 'None'}")
    assert len(effects) == 1, "Should have level 3"
    assert effects[0].get('id') == 3, "Should be level 3"
    assert effects[0].get('type') == 'choice', "Level 3 should be a choice"
    print("  ✓ Level 3 is a choice")

    # Test Path A: Player chooses "trash" at level 3
    print("\n--- Path A: Choose 'trash' at level 3 ---")
    leader.level_3_choice = "trash"
    leader.training_track_position = 3

    print(f"\nPosition 3 (after choosing trash):")
    effects = leader.get_current_signet_effects()
    print(f"  Effects: {effects}")
    # Level 4 rewards are extracted: troop + spy (2 effects)
    assert len(effects) == 2, "Should have level 4 rewards (troop + spy)"
    assert effects[0].get('resource') == 'troop', "First effect should be troop"
    assert effects[1].get('type') == 'play' and effects[1].get('unit') == 'spy', "Second effect should be place spy"
    print("  ✓ Skipped level 3.1, went straight to level 4 (repeatable)")

    # Test Path B: Player chooses "spy" at level 3
    print("\n--- Path B: Choose 'spy' at level 3 ---")
    leader2 = FeydRautha()
    leader2.training_track_position = 2
    leader2.level_3_choice = "spy"
    leader2.training_track_position = 3

    print(f"\nPosition 3 (after choosing spy):")
    effects = leader2.get_current_signet_effects()
    print(f"  Effects: {effects}")
    # Level 3.1 reward is extracted: gain 2 spice (1 effect)
    assert len(effects) == 1, "Should have level 3.1 reward"
    assert effects[0].get('type') == 'resource', "Should be resource effect"
    assert effects[0].get('resource') == 'spice', "Should gain spice"
    assert effects[0].get('amount') == 2, "Should gain 2 spice"
    print("  ✓ Went to level 3.1 (gain 2 spice)")

    # Advance to position 4
    leader2.training_track_position = 4
    print(f"\nPosition 4 (after level 3.1):")
    effects = leader2.get_current_signet_effects()
    print(f"  Effects: {effects}")
    # Level 4 rewards: troop + spy (2 effects)
    assert len(effects) == 2, "Should have level 4 rewards"
    assert effects[0].get('resource') == 'troop', "First effect should be troop"
    print("  ✓ Advanced to level 4 (repeatable)")

    return True


def test_default_path():
    """Test default path when level_3_choice is not set."""
    print("\n" + "="*80)
    print("TEST: Default Path (level_3_choice = None)")
    print("="*80)

    leader = FeydRautha()
    leader.training_track_position = 3

    print(f"\nPosition 3 (level_3_choice not set):")
    effects = leader.get_current_signet_effects()
    print(f"  Effects: {effects}")
    print(f"  level_3_choice: {leader.level_3_choice}")

    # Default should be level 3.1 (spy path) - extracted reward
    assert len(effects) == 1, "Should have level 3.1 reward"
    assert effects[0].get('type') == 'resource', "Should be resource effect"
    assert effects[0].get('resource') == 'spice', "Should be spice (level 3.1)"
    assert effects[0].get('amount') == 2, "Should gain 2 spice"
    print("  ✓ Defaults to level 3.1 (spy path) when choice not set")

    return True


def test_full_progression():
    """Test complete progression through all positions."""
    print("\n" + "="*80)
    print("TEST: Full Progression (All Positions)")
    print("="*80)

    leader = FeydRautha()

    positions = [
        (0, 1, "Level 1 - choice"),
        (1, 2, "Level 2 - trash"),
        (2, 3, "Level 3 - choice"),
    ]

    for pos, expected_id, description in positions:
        leader.training_track_position = pos
        effects = leader.get_current_signet_effects()
        print(f"\nPosition {pos}: {description}")
        print(f"  Expected ID: {expected_id}, Got: {effects[0].get('id') if effects else 'None'}")
        assert len(effects) > 0, f"Position {pos} should have effects"
        assert effects[0].get('id') == expected_id, f"Position {pos} should be level {expected_id}"
        print(f"  ✓ Correct")

    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FEYD RAUTHA BRANCHING PROGRESSION TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_level_3_branching,
        test_default_path,
        test_full_progression,
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
        print("\nFeyd Rautha Branching Progression:")
        print("  ✓ Level 3 offers choice")
        print("  ✓ Trash option → skip to level 4")
        print("  ✓ Spy option → level 3.1 (gain 2 spice) → level 4")
        print("  ✓ Default path is spy (level 3.1)")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        sys.exit(1)
