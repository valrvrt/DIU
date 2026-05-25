"""
Test PhaseManager integration with MakersManager.

Validates that:
1. PhaseManager automatically calls MakersManager when entering MAKERS phase
2. Bonus spice is added correctly during phase transitions
3. Multiple rounds accumulate bonus spice properly
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.game import Game, GamePhase
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.phase_manager import PhaseManager
from src.engine.managers.makers_manager import MakersManager


def create_test_game_with_maker_spaces():
    """Create a test game with maker spaces."""
    game = Game()
    board = Board()

    # Create maker spaces
    deep_desert = BoardSpace(
        id=9,
        name="Deep Desert",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True,
        is_maker_space=True
    )
    deep_desert.occupied_by = None

    haga_bassin = BoardSpace(
        id=10,
        name="Haga Bassin",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True,
        is_maker_space=True
    )
    haga_bassin.occupied_by = None

    imperial_bassin = BoardSpace(
        id=11,
        name="Imperial Bassin",
        faction=None,
        agent_icon="yellow",
        is_combat_space=True,
        is_maker_space=True
    )
    imperial_bassin.occupied_by = None

    board.spaces = [deep_desert, haga_bassin, imperial_bassin]

    # Add dummy conflict deck to prevent game over
    board.conflict_deck = ["conflict1", "conflict2", "conflict3"]

    game.board = board
    game.current_phase = GamePhase.COMBAT  # Start before MAKERS

    return game, deep_desert, haga_bassin, imperial_bassin


# ==================== TESTS ====================

def test_phase_manager_triggers_makers_phase():
    """Test that PhaseManager automatically triggers MAKERS phase."""
    print("\n=== Test: PhaseManager Triggers MAKERS Phase ===")

    game, deep_desert, haga_bassin, imperial_bassin = create_test_game_with_maker_spaces()

    # Create PhaseManager (it will auto-create MakersManager)
    phase_manager = PhaseManager(game)

    # Advance to MAKERS phase
    game.current_phase = GamePhase.MAKERS
    phase_manager._initialize_phase(GamePhase.MAKERS)

    # All unoccupied maker spaces should have 1 bonus spice
    assert deep_desert.spice_bonus == 1
    assert haga_bassin.spice_bonus == 1
    assert imperial_bassin.spice_bonus == 1

    print("✓ PhaseManager automatically triggers MAKERS phase")
    print(f"  Bonus spice added to all 3 maker spaces")


def test_makers_phase_in_round_progression():
    """Test MAKERS phase during normal round progression."""
    print("\n=== Test: MAKERS Phase in Round Progression ===")

    game, deep_desert, haga_bassin, imperial_bassin = create_test_game_with_maker_spaces()
    phase_manager = PhaseManager(game)

    # Round 1: COMBAT → MAKERS
    game.current_phase = GamePhase.COMBAT
    phase_manager.advance_phase()

    # Should now be in MAKERS phase
    assert game.current_phase == GamePhase.MAKERS
    assert deep_desert.spice_bonus == 1

    # MAKERS → RECALL
    phase_manager.advance_phase()
    assert game.current_phase == GamePhase.RECALL

    # RECALL → BEGIN_ROUND (new round)
    phase_manager.advance_phase()
    assert game.current_phase == GamePhase.BEGIN_ROUND

    # Skip to next MAKERS phase
    game.current_phase = GamePhase.MAKERS
    phase_manager._initialize_phase(GamePhase.MAKERS)

    # Bonus spice should have accumulated
    assert deep_desert.spice_bonus == 2  # 1 from round 1 + 1 from round 2

    print("✓ MAKERS phase works in round progression")
    print(f"  Bonus spice after 2 rounds: {deep_desert.spice_bonus}")


def test_occupied_spaces_skipped_during_phase_transition():
    """Test that occupied maker spaces don't get bonus spice during phase transition."""
    print("\n=== Test: Occupied Spaces Skipped ===")

    game, deep_desert, haga_bassin, imperial_bassin = create_test_game_with_maker_spaces()
    phase_manager = PhaseManager(game)

    # Occupy Deep Desert
    deep_desert.occupied_by = "player1"

    # Execute MAKERS phase
    game.current_phase = GamePhase.MAKERS
    phase_manager._initialize_phase(GamePhase.MAKERS)

    # Occupied space should NOT get bonus (attribute won't exist if never updated)
    assert getattr(deep_desert, 'spice_bonus', 0) == 0

    # Unoccupied spaces should get bonus
    assert haga_bassin.spice_bonus == 1
    assert imperial_bassin.spice_bonus == 1

    print("✓ Occupied spaces correctly skipped during phase transition")


def test_multiple_rounds_accumulation():
    """Test bonus spice accumulation over multiple rounds."""
    print("\n=== Test: Multiple Rounds Accumulation ===")

    game, deep_desert, haga_bassin, imperial_bassin = create_test_game_with_maker_spaces()
    phase_manager = PhaseManager(game)

    # Round 1
    game.current_phase = GamePhase.MAKERS
    phase_manager._initialize_phase(GamePhase.MAKERS)
    assert deep_desert.spice_bonus == 1

    # Round 2
    phase_manager._initialize_phase(GamePhase.MAKERS)
    assert deep_desert.spice_bonus == 2

    # Round 3
    phase_manager._initialize_phase(GamePhase.MAKERS)
    assert deep_desert.spice_bonus == 3

    # Round 4 - occupy Deep Desert before MAKERS
    deep_desert.occupied_by = "player1"
    phase_manager._initialize_phase(GamePhase.MAKERS)
    assert deep_desert.spice_bonus == 3  # Unchanged (occupied)

    # Other spaces continue accumulating
    assert haga_bassin.spice_bonus == 4
    assert imperial_bassin.spice_bonus == 4

    print("✓ Bonus spice accumulates correctly over multiple rounds")
    print(f"  Deep Desert (occupied): {deep_desert.spice_bonus}")
    print(f"  Haga Bassin: {haga_bassin.spice_bonus}")
    print(f"  Imperial Bassin: {imperial_bassin.spice_bonus}")


def test_custom_makers_manager_can_be_injected():
    """Test that a custom MakersManager can be injected into PhaseManager."""
    print("\n=== Test: Custom MakersManager Injection ===")

    game, deep_desert, haga_bassin, imperial_bassin = create_test_game_with_maker_spaces()

    # Create custom MakersManager
    custom_makers = MakersManager(game)

    # Inject into PhaseManager
    phase_manager = PhaseManager(game, makers_manager=custom_makers)

    # Verify it's the same instance
    assert phase_manager.makers_manager is custom_makers

    # Execute MAKERS phase
    game.current_phase = GamePhase.MAKERS
    phase_manager._initialize_phase(GamePhase.MAKERS)

    # Should still work correctly
    assert deep_desert.spice_bonus == 1

    print("✓ Custom MakersManager can be injected")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all PhaseManager + MakersManager integration tests."""
    print("=" * 70)
    print("PHASE MANAGER + MAKERS MANAGER INTEGRATION TESTS")
    print("=" * 70)

    try:
        test_phase_manager_triggers_makers_phase()
        test_makers_phase_in_round_progression()
        test_occupied_spaces_skipped_during_phase_transition()
        test_multiple_rounds_accumulation()
        test_custom_makers_manager_can_be_injected()

        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        print("\nKey Validations:")
        print("  ✓ PhaseManager automatically triggers MAKERS phase")
        print("  ✓ MAKERS phase works in normal round progression")
        print("  ✓ Occupied spaces are skipped correctly")
        print("  ✓ Bonus spice accumulates over multiple rounds")
        print("  ✓ Custom MakersManager can be injected")
        print("\n🎉 PhaseManager + MakersManager integration complete!")

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
