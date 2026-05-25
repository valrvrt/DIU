"""
Integration tests for CombatManager with PhaseManager.

Tests that combat resolution works correctly within the game flow.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, CardType, ConflictCard
from src.models.deck import Deck
from src.models.board import Board
from src.engine.managers.phase_manager import PhaseManager
from src.engine.managers.combat_manager import CombatManager


def setup_test_game():
    """Create a game with combat setup."""
    # Create leaders
    leader1 = LeaderCard(id="leader1", name="Leader 1", type="Leader", card_type=CardType.LEADER)
    leader2 = LeaderCard(id="leader2", name="Leader 2", type="Leader", card_type=CardType.LEADER)

    # Create players
    player1 = Player(
        player_id="player1",
        name="Player 1",
        leader=leader1,
        color="blue",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=5,
        spice=1
    )

    player2 = Player(
        player_id="player2",
        name="Player 2",
        leader=leader2,
        color="red",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=5,
        spice=1
    )

    # Create conflict card with proper rewards format
    conflict = ConflictCard(
        id="test_conflict",
        name="Test Conflict",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards={
            "1": [  # 1st place
                {"type": "resource", "resource": "victory_point", "amount": 2},
                {"type": "resource", "resource": "solari", "amount": 3}
            ],
            "2": [  # 2nd place
                {"type": "resource", "resource": "victory_point", "amount": 1}
            ]
        }
    )

    # Create board
    board = Board()
    board.current_conflict = conflict
    board.conflict_deck = []  # Empty for now

    # Create game
    game = Game(
        players=[player1, player2],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS
    )

    return game, player1, player2, conflict


def test_combat_phase_resolves():
    """Test that combat phase resolves conflict when explicitly triggered."""
    print("\n=== Test: Combat Phase Resolves ===")

    game, player1, player2, conflict = setup_test_game()

    # Setup combat strength
    player1.troops_in_conflict = 3  # 6 strength
    player2.troops_in_conflict = 2  # 4 strength

    # Create managers
    combat_manager = CombatManager(game)

    # Combat must be resolved explicitly (game loop responsibility)
    result = combat_manager.resolve_conflict(intrigue_round_complete=True)
    assert result["success"] == True, f"Combat resolution failed: {result.get('error')}"

    # Check conflict is resolved
    assert game.board.current_conflict is None, "Conflict should be resolved"
    assert len(game.board.resolved_conflicts) == 1, "Should have 1 resolved conflict"

    # Check winner got the card
    assert len(player1.conflict_cards_won) == 1, "Player 1 should have won the card"

    # Check rewards distributed
    assert player1.victory_points == 2, "Player 1 should have 2 VP"
    assert player2.victory_points == 1, "Player 2 should have 1 VP"

    print("✓ Combat phase resolves correctly")


def test_complete_combat_flow_with_phase_manager():
    """Test complete flow: PLAYER_TURNS → COMBAT → (resolve) → MAKERS."""
    print("\n=== Test: Complete Combat Flow ===")

    game, player1, player2, conflict = setup_test_game()

    # Setup
    player1.troops_in_conflict = 4
    player2.troops_in_conflict = 2

    # Mark both as revealed
    player1.has_revealed_this_round = True
    player2.has_revealed_this_round = True

    # Create managers
    combat_manager = CombatManager(game)
    phase_manager = PhaseManager(game, combat_manager)

    # Set to PLAYER_TURNS
    game.current_phase = GamePhase.PLAYER_TURNS

    # Advance from PLAYER_TURNS to COMBAT
    assert phase_manager.should_advance_phase() == True, "Should advance (all revealed)"

    result = phase_manager.advance_phase()
    assert game.current_phase == GamePhase.COMBAT, "Should be in COMBAT phase"

    # Game loop must explicitly resolve combat (not auto-resolved)
    combat_result = combat_manager.resolve_conflict(intrigue_round_complete=True)
    assert combat_result["success"] == True, "Combat resolution should succeed"
    assert game.board.current_conflict is None, "Conflict should be resolved"

    # Advance to MAKERS
    assert phase_manager.should_advance_phase() == True, "Should advance (conflict resolved)"

    result = phase_manager.advance_phase()
    assert game.current_phase == GamePhase.MAKERS, "Should be in MAKERS phase"

    print("✓ Complete combat flow works")


def test_troops_cleaned_up_after_combat():
    """Test that troops are returned to reserve after combat."""
    print("\n=== Test: Troops Cleaned Up After Combat ===")

    game, player1, player2, conflict = setup_test_game()

    # Setup troops
    player1.troops_in_conflict = 3
    player1.troops_in_reserve = 6

    player2.troops_in_conflict = 2
    player2.troops_in_reserve = 8

    # Create managers
    combat_manager = CombatManager(game)

    # Resolve combat explicitly
    result = combat_manager.resolve_conflict(intrigue_round_complete=True)
    assert result["success"] == True

    # Troops should be back in reserve
    assert player1.troops_in_conflict == 0, "Player 1 should have 0 troops in conflict"
    assert player1.troops_in_reserve == 9, f"Player 1 should have 9 in reserve, got {player1.troops_in_reserve}"

    assert player2.troops_in_conflict == 0, "Player 2 should have 0 troops in conflict"
    assert player2.troops_in_reserve == 10, f"Player 2 should have 10 in reserve, got {player2.troops_in_reserve}"

    print("✓ Troops cleaned up after combat")


def test_sandworms_die_after_combat():
    """Test that sandworms die after combat phase cleanup."""
    print("\n=== Test: Sandworms Die After Combat ===")

    game, player1, player2, conflict = setup_test_game()

    # Setup sandworms
    player1.troops_in_conflict = 2
    player1.sandworms_in_conflict = 1

    player2.troops_in_conflict = 1

    # Create managers
    combat_manager = CombatManager(game)
    phase_manager = PhaseManager(game, combat_manager)

    # Resolve combat
    game.current_phase = GamePhase.COMBAT
    phase_manager._initialize_phase(GamePhase.COMBAT)

    # Cleanup COMBAT phase (sandworms should die)
    phase_manager._cleanup_phase(GamePhase.COMBAT)

    # Check sandworms are gone
    assert player1.sandworms_in_conflict == 0, "Sandworms should be dead"

    print("✓ Sandworms die after combat")


def test_tied_combat_rewards():
    """Test rewards when players tie for first place."""
    print("\n=== Test: Tied Combat Rewards (No Conflict Card) ===")

    game, player1, player2, conflict = setup_test_game()

    # Both have same strength
    player1.troops_in_conflict = 3  # 6 strength
    player2.troops_in_conflict = 3  # 6 strength

    # Create managers
    combat_manager = CombatManager(game)

    # Resolve combat explicitly
    result = combat_manager.resolve_conflict(intrigue_round_complete=True)
    assert result["success"] == True

    # Per game rules: tied 1st = NO conflict card, both ranked as 2nd place
    # Both get 2nd place rewards (ranked 2nd since they tied)
    assert player1.victory_points == 1, f"Player 1 should have 1 VP (2nd place), got {player1.victory_points}"
    assert player2.victory_points == 1, f"Player 2 should have 1 VP (2nd place), got {player2.victory_points}"

    # Neither gets the conflict card (tied for 1st)
    assert len(player1.conflict_cards_won) == 0, "Tied player 1 should NOT get conflict card"
    assert len(player2.conflict_cards_won) == 0, "Tied player 2 should NOT get conflict card"

    print("✓ Tied combat rewards correct (no conflict card)")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("COMBAT INTEGRATION TESTS")
    print("="*70)

    test_combat_phase_auto_resolves()
    test_complete_combat_flow_with_phase_manager()
    test_troops_cleaned_up_after_combat()
    test_sandworms_die_after_combat()
    test_tied_combat_rewards()

    print("\n" + "="*70)
    print("✅ ALL COMBAT INTEGRATION TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
