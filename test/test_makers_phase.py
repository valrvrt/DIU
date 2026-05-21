"""
Test MAKERS phase functionality.

Validates that:
1. Bonus spice accumulates on unoccupied maker spaces
2. Bonus spice is NOT added to occupied maker spaces
3. Players collect bonus spice when placing agents on maker spaces
4. Bonus spice resets after collection
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.game import Game, GamePhase
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.makers_manager import MakersManager


def create_test_board_with_maker_spaces():
    """Create a board with maker spaces for testing."""
    board = Board()

    # Create maker spaces (like Deep Desert, Haga Bassin, Imperial Bassin)
    deep_desert = BoardSpace(
        id=9,
        name="Deep Desert",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True
    )
    deep_desert.maker = True
    deep_desert.bonus_spice = 0
    deep_desert.occupied_by = None

    haga_bassin = BoardSpace(
        id=10,
        name="Haga Bassin",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True
    )
    haga_bassin.maker = True
    haga_bassin.bonus_spice = 0
    haga_bassin.occupied_by = None

    imperial_bassin = BoardSpace(
        id=11,
        name="Imperial Bassin",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True
    )
    imperial_bassin.maker = True
    imperial_bassin.bonus_spice = 0
    imperial_bassin.occupied_by = None

    # Create a non-maker space
    fremkit = BoardSpace(
        id=1,
        name="Fremkit",
        faction="fremen",
        agent_icon="fremen",
        is_combat_space=True
    )
    fremkit.maker = False
    fremkit.occupied_by = None

    board.spaces = [deep_desert, haga_bassin, imperial_bassin, fremkit]

    return board, deep_desert, haga_bassin, imperial_bassin


# ==================== TESTS ====================

def test_makers_phase_adds_bonus_spice():
    """Test that MAKERS phase adds 1 spice to each unoccupied maker space."""
    print("\n=== Test: MAKERS Phase Adds Bonus Spice ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    makers_manager = MakersManager(game)

    # Execute MAKERS phase
    result = makers_manager.execute_makers_phase()

    assert result["success"] == True
    assert result["total_bonus_added"] == 3  # 3 unoccupied maker spaces
    assert len(result["spaces_updated"]) == 3

    # Each maker space should have 1 bonus spice
    assert deep_desert.bonus_spice == 1
    assert haga_bassin.bonus_spice == 1
    assert imperial_bassin.bonus_spice == 1

    print("✓ MAKERS phase adds bonus spice correctly")
    print(f"  Total bonus added: {result['total_bonus_added']}")
    print(f"  Spaces updated: {[s['space'] for s in result['spaces_updated']]}")


def test_makers_phase_skips_occupied_spaces():
    """Test that MAKERS phase does NOT add spice to occupied maker spaces."""
    print("\n=== Test: MAKERS Phase Skips Occupied Spaces ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    # Occupy Deep Desert
    deep_desert.occupied_by = "player1"

    makers_manager = MakersManager(game)

    # Execute MAKERS phase
    result = makers_manager.execute_makers_phase()

    assert result["success"] == True
    assert result["total_bonus_added"] == 2  # Only 2 unoccupied spaces

    # Occupied space should NOT get bonus
    assert deep_desert.bonus_spice == 0  # Unchanged

    # Unoccupied spaces should get bonus
    assert haga_bassin.bonus_spice == 1
    assert imperial_bassin.bonus_spice == 1

    print("✓ MAKERS phase correctly skips occupied spaces")
    print(f"  Spaces updated: {len(result['spaces_updated'])} (should be 2)")


def test_bonus_spice_accumulates_over_rounds():
    """Test that bonus spice accumulates round after round if unclaimed."""
    print("\n=== Test: Bonus Spice Accumulates Over Rounds ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    makers_manager = MakersManager(game)

    # Round 1: Add 1 spice to each
    makers_manager.execute_makers_phase()
    assert deep_desert.bonus_spice == 1

    # Round 2: Add 1 more spice to each
    makers_manager.execute_makers_phase()
    assert deep_desert.bonus_spice == 2

    # Round 3: Add 1 more spice to each
    makers_manager.execute_makers_phase()
    assert deep_desert.bonus_spice == 3

    print("✓ Bonus spice accumulates correctly over rounds")
    print(f"  Deep Desert after 3 rounds: {deep_desert.bonus_spice} spice")


def test_claim_bonus_spice():
    """Test that claiming bonus spice returns the accumulated amount and resets."""
    print("\n=== Test: Claim Bonus Spice ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    # Accumulate spice over 3 rounds
    deep_desert.bonus_spice = 3

    makers_manager = MakersManager(game)

    # Claim bonus spice
    claimed = makers_manager.claim_bonus_spice(deep_desert, "player1")

    assert claimed == 3
    assert deep_desert.bonus_spice == 0  # Reset after claiming

    print("✓ Claiming bonus spice works correctly")
    print(f"  Claimed: {claimed} spice")
    print(f"  Remaining: {deep_desert.bonus_spice} spice")


def test_get_maker_spaces_status():
    """Test getting status of all maker spaces."""
    print("\n=== Test: Get Maker Spaces Status ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    # Set up different states
    deep_desert.bonus_spice = 3
    haga_bassin.bonus_spice = 1
    haga_bassin.occupied_by = "player1"
    imperial_bassin.bonus_spice = 2

    makers_manager = MakersManager(game)

    status = makers_manager.get_maker_spaces_status()

    assert len(status) == 3

    # Find Deep Desert status
    dd_status = next(s for s in status if s["name"] == "Deep Desert")
    assert dd_status["occupied"] == False
    assert dd_status["bonus_spice"] == 3

    # Find Haga Bassin status
    hb_status = next(s for s in status if s["name"] == "Haga Bassin")
    assert hb_status["occupied"] == True
    assert hb_status["occupied_by"] == "player1"
    assert hb_status["bonus_spice"] == 1

    print("✓ Getting maker spaces status works")
    print(f"  Maker spaces: {len(status)}")


def test_non_maker_spaces_ignored():
    """Test that non-maker spaces are not affected by MAKERS phase."""
    print("\n=== Test: Non-Maker Spaces Ignored ===")

    game = Game()
    board, deep_desert, haga_bassin, imperial_bassin = create_test_board_with_maker_spaces()
    game.board = board

    # Get the non-maker space (Fremkit)
    fremkit = board.spaces[3]
    assert fremkit.maker == False

    makers_manager = MakersManager(game)

    # Execute MAKERS phase
    result = makers_manager.execute_makers_phase()

    # Fremkit should NOT have bonus_spice attribute or it should be 0
    bonus = getattr(fremkit, 'bonus_spice', 0)
    assert bonus == 0

    print("✓ Non-maker spaces are correctly ignored")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all MAKERS phase tests."""
    print("=" * 70)
    print("MAKERS PHASE TESTS")
    print("=" * 70)

    try:
        test_makers_phase_adds_bonus_spice()
        test_makers_phase_skips_occupied_spaces()
        test_bonus_spice_accumulates_over_rounds()
        test_claim_bonus_spice()
        test_get_maker_spaces_status()
        test_non_maker_spaces_ignored()

        print("\n" + "=" * 70)
        print("✅ ALL MAKERS PHASE TESTS PASSED")
        print("=" * 70)
        print("\nKey Validations:")
        print("  ✓ Bonus spice added to unoccupied maker spaces")
        print("  ✓ Occupied maker spaces skipped correctly")
        print("  ✓ Bonus spice accumulates over multiple rounds")
        print("  ✓ Claiming bonus spice works and resets counter")
        print("  ✓ Maker spaces status can be queried")
        print("  ✓ Non-maker spaces are not affected")
        print("\n🎉 MAKERS phase is complete!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
