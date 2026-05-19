"""
Unit tests for CombatManager.

Tests combat strength calculation, ranking with ties, and reward distribution.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, CardType, ConflictCard
from src.models.deck import Deck
from src.models.board import Board
from src.engine.combat_manager import CombatManager


def setup_test_game():
    """Create a minimal game for combat testing."""
    # Create leaders
    leader1 = LeaderCard(
        id="leader1",
        name="Leader 1",
        type="Leader",
        card_type=CardType.LEADER
    )

    leader2 = LeaderCard(
        id="leader2",
        name="Leader 2",
        type="Leader",
        card_type=CardType.LEADER
    )

    leader3 = LeaderCard(
        id="leader3",
        name="Leader 3",
        type="Leader",
        card_type=CardType.LEADER
    )

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

    player3 = Player(
        player_id="player3",
        name="Player 3",
        leader=leader3,
        color="green",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=5,
        spice=1
    )

    # Create conflict card
    conflict = ConflictCard(
        id="test_conflict",
        name="Test Conflict",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[
            {"victory_points": 2, "solari": 3},  # 1st place
            {"victory_points": 1},                # 2nd place
            {"spice": 1}                         # 3rd place
        ]
    )

    # Create board
    board = Board()
    board.current_conflict = conflict

    # Create game
    game = Game(
        players=[player1, player2, player3],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.COMBAT
    )

    return game, player1, player2, player3, conflict


# ==================== STRENGTH CALCULATION TESTS ====================

def test_calculate_combat_strength():
    """Test combat strength calculation formula."""
    print("\n=== Test: Combat Strength Calculation ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1: 3 troops, 1 sandworm, 2 swords
    player1.troops_in_conflict = 3
    player1.sandworms_in_conflict = 1
    player1.temp_swords = 2

    # Expected: (3*2) + (1*3) + 2 = 6 + 3 + 2 = 11
    strength = combat_manager.calculate_combat_strength("player1")
    assert strength == 11, f"Expected 11, got {strength}"

    print("✓ Combat strength calculated correctly")


def test_participation_requires_troops_or_sandworms():
    """Test that only swords doesn't allow participation."""
    print("\n=== Test: Participation Requirements ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1: Only swords, no troops/sandworms
    player1.troops_in_conflict = 0
    player1.sandworms_in_conflict = 0
    player1.temp_swords = 5

    assert not combat_manager.is_participating_in_combat("player1"), "Should not participate with only swords"

    # Player 2: Has troops
    player2.troops_in_conflict = 1
    player2.sandworms_in_conflict = 0
    player2.temp_swords = 0

    assert combat_manager.is_participating_in_combat("player2"), "Should participate with troops"

    # Player 3: Has sandworm
    player3.troops_in_conflict = 0
    player3.sandworms_in_conflict = 1
    player3.temp_swords = 0

    assert combat_manager.is_participating_in_combat("player3"), "Should participate with sandworm"

    print("✓ Participation requirements correct")


# ==================== RANKING TESTS ====================

def test_ranking_single_winner():
    """Test ranking with single winner."""
    print("\n=== Test: Single Winner Ranking ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1: 4 troops (8 strength)
    player1.troops_in_conflict = 4

    # Player 2: 2 troops (4 strength)
    player2.troops_in_conflict = 2

    # Player 3: 1 troop (2 strength)
    player3.troops_in_conflict = 1

    strengths = combat_manager._calculate_all_combat_strengths()
    rankings = combat_manager._determine_rankings(strengths)

    assert 1 in rankings and rankings[1] == ["player1"], "Player 1 should be 1st"
    assert 2 in rankings and rankings[2] == ["player2"], "Player 2 should be 2nd"
    assert 3 in rankings and rankings[3] == ["player3"], "Player 3 should be 3rd"

    print("✓ Single winner ranking correct")


def test_ranking_tied_first():
    """Test ranking when two players tie for first."""
    print("\n=== Test: Tied First Place ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1 and 2: 3 troops each (6 strength)
    player1.troops_in_conflict = 3
    player2.troops_in_conflict = 3

    # Player 3: 1 troop (2 strength)
    player3.troops_in_conflict = 1

    strengths = combat_manager._calculate_all_combat_strengths()
    rankings = combat_manager._determine_rankings(strengths)

    # Tied first → both get 2nd place reward
    assert 2 in rankings, "Should have rank 2"
    assert set(rankings[2]) == {"player1", "player2"}, "Player 1 and 2 should share 2nd place"

    # Third player gets 3rd place reward
    assert 3 in rankings and rankings[3] == ["player3"], "Player 3 should get 3rd place"

    print("✓ Tied first place handled correctly")


def test_ranking_tied_second():
    """Test ranking when two players tie for second."""
    print("\n=== Test: Tied Second Place ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1: 4 troops (8 strength)
    player1.troops_in_conflict = 4

    # Player 2 and 3: 2 troops each (4 strength)
    player2.troops_in_conflict = 2
    player3.troops_in_conflict = 2

    strengths = combat_manager._calculate_all_combat_strengths()
    rankings = combat_manager._determine_rankings(strengths)

    # Player 1 wins
    assert 1 in rankings and rankings[1] == ["player1"], "Player 1 should be 1st"

    # Tied second → both get 3rd place reward
    assert 3 in rankings, "Should have rank 3"
    assert set(rankings[3]) == {"player2", "player3"}, "Player 2 and 3 should share 3rd place"

    print("✓ Tied second place handled correctly")


def test_ranking_tied_third():
    """Test ranking when two players tie for third."""
    print("\n=== Test: Tied Third Place ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Add a 4th player
    leader4 = LeaderCard(id="leader4", name="Leader 4", type="Leader", card_type=CardType.LEADER)
    player4 = Player(
        player_id="player4",
        name="Player 4",
        leader=leader4,
        color="yellow",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )
    game.players.append(player4)

    # Player 1: 4 troops (8 strength)
    player1.troops_in_conflict = 4

    # Player 2: 2 troops (4 strength)
    player2.troops_in_conflict = 2

    # Player 3 and 4: 1 troop each (2 strength)
    player3.troops_in_conflict = 1
    player4.troops_in_conflict = 1

    strengths = combat_manager._calculate_all_combat_strengths()
    rankings = combat_manager._determine_rankings(strengths)

    # Player 1 wins
    assert 1 in rankings and rankings[1] == ["player1"], "Player 1 should be 1st"

    # Player 2 second
    assert 2 in rankings and rankings[2] == ["player2"], "Player 2 should be 2nd"

    # Tied third → they get nothing (rank 3 should not exist)
    assert 3 not in rankings, "Tied 3rd place should not get rewards (rank 3 should not exist)"

    print("✓ Tied third place handled correctly")


# ==================== REWARD DISTRIBUTION TESTS ====================

def test_reward_distribution():
    """Test that rewards are distributed correctly."""
    print("\n=== Test: Reward Distribution ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Setup strengths
    player1.troops_in_conflict = 4  # 8 strength
    player2.troops_in_conflict = 2  # 4 strength
    player3.troops_in_conflict = 1  # 2 strength

    # Resolve conflict
    result = combat_manager.resolve_conflict()

    assert result["success"] == True, "Conflict resolution should succeed"

    # Check 1st place rewards
    assert player1.victory_points == 2, f"Player 1 should have 2 VP, got {player1.victory_points}"
    assert player1.solari == 8, f"Player 1 should have 8 solari (5+3), got {player1.solari}"

    # Check 2nd place rewards
    assert player2.victory_points == 1, f"Player 2 should have 1 VP, got {player2.victory_points}"

    # Check 3rd place rewards
    assert player3.spice == 2, f"Player 3 should have 2 spice (1+1), got {player3.spice}"

    print("✓ Rewards distributed correctly")


def test_winner_gets_conflict_card():
    """Test that winner receives the conflict card."""
    print("\n=== Test: Winner Gets Conflict Card ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1 wins
    player1.troops_in_conflict = 5

    # Player 2 and 3 have less
    player2.troops_in_conflict = 2
    player3.troops_in_conflict = 1

    result = combat_manager.resolve_conflict()

    assert len(player1.conflict_cards_won) == 1, "Player 1 should have won conflict card"
    assert player1.conflict_cards_won[0].id == "test_conflict", "Should be the test conflict"

    print("✓ Winner gets conflict card")


def test_tied_winners_both_get_conflict_card():
    """Test that tied winners both get the conflict card."""
    print("\n=== Test: Tied Winners Get Conflict Card ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Player 1 and 2 tie for first
    player1.troops_in_conflict = 3
    player2.troops_in_conflict = 3

    # Player 3 has less
    player3.troops_in_conflict = 1

    result = combat_manager.resolve_conflict()

    # Both tied winners get the card
    assert len(player1.conflict_cards_won) == 1, "Player 1 should have won conflict card"
    assert len(player2.conflict_cards_won) == 1, "Player 2 should have won conflict card"

    print("✓ Tied winners both get conflict card")


# ==================== CLEANUP TESTS ====================

def test_troops_return_to_reserve():
    """Test that troops return to reserve after combat."""
    print("\n=== Test: Troops Return to Reserve ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # Set initial states
    player1.troops_in_conflict = 3
    player1.troops_in_reserve = 7

    player2.troops_in_conflict = 2
    player2.troops_in_reserve = 10

    # Resolve conflict
    result = combat_manager.resolve_conflict()

    # Check troops returned to reserve
    assert player1.troops_in_conflict == 0, "Player 1 should have 0 troops in conflict"
    assert player1.troops_in_reserve == 10, f"Player 1 should have 10 troops in reserve, got {player1.troops_in_reserve}"

    assert player2.troops_in_conflict == 0, "Player 2 should have 0 troops in conflict"
    assert player2.troops_in_reserve == 12, f"Player 2 should have 12 troops in reserve, got {player2.troops_in_reserve}"

    print("✓ Troops returned to reserve")


def test_conflict_marked_as_resolved():
    """Test that conflict is marked as resolved."""
    print("\n=== Test: Conflict Marked as Resolved ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    player1.troops_in_conflict = 3

    # Resolve conflict
    result = combat_manager.resolve_conflict()

    # Check conflict is resolved
    assert game.board.current_conflict is None, "Current conflict should be None"
    assert len(game.board.resolved_conflicts) == 1, "Should have 1 resolved conflict"
    assert game.board.resolved_conflicts[0].id == "test_conflict", "Should be the test conflict"

    print("✓ Conflict marked as resolved")


def test_no_participants():
    """Test combat when no one participates."""
    print("\n=== Test: No Participants ===")

    game, player1, player2, player3, conflict = setup_test_game()
    combat_manager = CombatManager(game)

    # No one has troops or sandworms
    player1.troops_in_conflict = 0
    player2.troops_in_conflict = 0
    player3.troops_in_conflict = 0

    # Only swords (doesn't count)
    player1.temp_swords = 5

    strengths = combat_manager._calculate_all_combat_strengths()
    rankings = combat_manager._determine_rankings(strengths)

    # No one should be ranked
    assert len(rankings) == 0, "Should have no rankings when no one participates"

    print("✓ No participants handled correctly")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all combat manager tests."""
    print("\n" + "="*70)
    print("COMBAT MANAGER UNIT TESTS")
    print("="*70)

    # Strength calculation
    test_calculate_combat_strength()
    test_participation_requires_troops_or_sandworms()

    # Ranking
    test_ranking_single_winner()
    test_ranking_tied_first()
    test_ranking_tied_second()
    test_ranking_tied_third()

    # Reward distribution
    test_reward_distribution()
    test_winner_gets_conflict_card()
    test_tied_winners_both_get_conflict_card()

    # Cleanup
    test_troops_return_to_reserve()
    test_conflict_marked_as_resolved()
    test_no_participants()

    print("\n" + "="*70)
    print("✅ ALL COMBAT MANAGER TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
