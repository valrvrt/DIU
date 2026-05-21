"""
Unit tests for PhaseManager.

Tests phase transitions, validation, turn order, and lifecycle hooks.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, CardType, ConflictCard
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.phase_manager import PhaseManager


def setup_test_game():
    """Create a minimal game for testing."""
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
        spice=1,
        agents_available=2,
        total_available_agents=2
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
        spice=1,
        agents_available=2,
        total_available_agents=2
    )

    # Create board
    board = Board()
    board.spaces = [
        BoardSpace(
            id="test_location",
            name="Test Location",
            agent_icon="fremen",
            effects={"water": 1}
        )
    ]

    # Create conflict deck
    conflict1 = ConflictCard(
        id="conflict1",
        name="Conflict 1",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[{"victory_points": 1}]
    )

    board.conflict_deck = [conflict1]
    board.current_conflict = None

    # Create game
    game = Game(
        players=[player1, player2],
        board=board,
        current_player_index=0,
        first_player_index=0,
        current_phase=GamePhase.SETUP,
        current_round=0
    )

    return game, player1, player2


# ==================== PHASE TRANSITION TESTS ====================

def test_phase_progression():
    """Test that phases advance in correct order."""
    print("\n=== Test: Phase Progression ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Setup → BEGIN_ROUND
    game.current_phase = GamePhase.SETUP
    next_phase = phase_manager._get_next_phase(GamePhase.SETUP)
    assert next_phase == GamePhase.BEGIN_ROUND, f"Expected BEGIN_ROUND, got {next_phase}"

    # BEGIN_ROUND → PLAYER_TURNS
    next_phase = phase_manager._get_next_phase(GamePhase.BEGIN_ROUND)
    assert next_phase == GamePhase.PLAYER_TURNS, f"Expected PLAYER_TURNS, got {next_phase}"

    # PLAYER_TURNS → COMBAT
    next_phase = phase_manager._get_next_phase(GamePhase.PLAYER_TURNS)
    assert next_phase == GamePhase.COMBAT, f"Expected COMBAT, got {next_phase}"

    # COMBAT → MAKERS
    next_phase = phase_manager._get_next_phase(GamePhase.COMBAT)
    assert next_phase == GamePhase.MAKERS, f"Expected MAKERS, got {next_phase}"

    # MAKERS → RECALL
    next_phase = phase_manager._get_next_phase(GamePhase.MAKERS)
    assert next_phase == GamePhase.RECALL, f"Expected RECALL, got {next_phase}"

    # RECALL → BEGIN_ROUND (loops)
    next_phase = phase_manager._get_next_phase(GamePhase.RECALL)
    assert next_phase == GamePhase.BEGIN_ROUND, f"Expected BEGIN_ROUND (loop), got {next_phase}"

    print("✓ Phase progression correct")


def test_phase_loops_after_recall():
    """Test that RECALL phase loops back to BEGIN_ROUND."""
    print("\n=== Test: Phase Loops After Recall ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.RECALL

    # Should loop back to BEGIN_ROUND
    result = phase_manager.advance_phase()

    assert game.current_phase == GamePhase.BEGIN_ROUND, f"Expected BEGIN_ROUND, got {game.current_phase}"
    assert result["old_phase"] == "recall"
    assert result["new_phase"] == "begin_round"

    print("✓ Phase loops correctly")


def test_game_over_when_vp_threshold():
    """Test that game ends when player reaches 10 VP at end of RECALL phase."""
    print("\n=== Test: Game Over at VP Threshold ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Give player1 10 VP and set to RECALL phase
    player1.victory_points = 10
    game.current_phase = GamePhase.RECALL

    assert phase_manager._is_game_over() == True, "Game should be over at 10 VP in RECALL phase"

    # Check that next phase is GAME_OVER
    next_phase = phase_manager._get_next_phase(GamePhase.RECALL)
    assert next_phase == GamePhase.GAME_OVER, f"Expected GAME_OVER, got {next_phase}"

    print("✓ Game over at VP threshold")


def test_game_over_when_conflicts_empty():
    """Test that game ends when conflict deck is empty."""
    print("\n=== Test: Game Over When Conflicts Empty ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Empty conflict deck
    game.board.conflict_deck = []
    game.current_phase = GamePhase.RECALL

    assert phase_manager._is_game_over() == True, "Game should be over when conflicts empty"

    print("✓ Game over when conflicts empty")


# ==================== TURN ORDER TESTS ====================

def test_turn_order_in_player_turns_phase():
    """Test that players take turns in correct order."""
    print("\n=== Test: Turn Order ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    game.current_player_index = 0

    # Current player should be player1
    current = phase_manager.get_current_player()
    assert current.player_id == "player1", f"Expected player1, got {current.player_id}"

    # Advance turn
    phase_manager.advance_turn()

    # Should now be player2
    current = phase_manager.get_current_player()
    assert current.player_id == "player2", f"Expected player2, got {current.player_id}"

    print("✓ Turn order correct")


def test_advance_turn_cycles_through_players():
    """Test that turn advances cycle through all players."""
    print("\n=== Test: Turn Cycling ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    game.current_player_index = 1  # Start at player2

    # Advance turn (should wrap to player1)
    phase_manager.advance_turn()

    assert game.current_player_index == 0, f"Expected 0, got {game.current_player_index}"

    print("✓ Turn cycles correctly")


# ==================== PHASE VALIDATION TESTS ====================

def test_cannot_place_agent_after_reveal():
    """Test that player can't place agent after revealing."""
    print("\n=== Test: Cannot Place Agent After Reveal ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    player1.has_revealed_this_round = True
    player1.agents_available = 1

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "place_agent"
    )

    assert can_act == False, "Should not be able to place agent after reveal"
    assert "after revealing" in reason.lower(), f"Expected 'after revealing' in reason, got: {reason}"

    print("✓ Cannot place agent after reveal")


def test_can_reveal_with_agents_remaining():
    """Test that player can reveal even with agents remaining (pass early)."""
    print("\n=== Test: Can Reveal With Agents ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    player1.agents_available = 1  # Still has agents
    player1.has_revealed_this_round = False

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "reveal"
    )

    assert can_act == True, f"Should be able to reveal (pass early), but got: {reason}"

    print("✓ Can reveal with agents remaining (pass)")


def test_cannot_reveal_twice():
    """Test that player can't reveal twice."""
    print("\n=== Test: Cannot Reveal Twice ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    player1.has_revealed_this_round = True

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "reveal"
    )

    assert can_act == False, "Should not be able to reveal twice"
    assert "already revealed" in reason.lower(), f"Expected 'already revealed' in reason, got: {reason}"

    print("✓ Cannot reveal twice")


def test_cannot_acquire_before_reveal():
    """Test that player can't acquire cards before revealing."""
    print("\n=== Test: Cannot Acquire Before Reveal ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    player1.has_revealed_this_round = False

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "acquire_card"
    )

    assert can_act == False, "Should not be able to acquire before reveal"
    assert "reveal" in reason.lower(), f"Expected 'reveal' in reason, got: {reason}"

    print("✓ Cannot acquire before reveal")


def test_can_acquire_after_reveal():
    """Test that player can acquire after revealing."""
    print("\n=== Test: Can Acquire After Reveal ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS
    player1.has_revealed_this_round = True
    player1.temp_persuasion = 5

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "acquire_card"
    )

    assert can_act == True, f"Should be able to acquire after reveal, but got: {reason}"

    print("✓ Can acquire after reveal")


def test_cannot_do_player_actions_in_makers_phase():
    """Test that player actions blocked in MAKERS phase."""
    print("\n=== Test: Cannot Act in MAKERS Phase ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.MAKERS

    can_act, reason = phase_manager.can_player_take_action(
        "player1",
        "place_agent"
    )

    assert can_act == False, "Should not be able to act in MAKERS phase"
    assert "automatic" in reason.lower(), f"Expected 'automatic' in reason, got: {reason}"

    print("✓ Cannot act in MAKERS phase")


# ==================== PHASE COMPLETION TESTS ====================

def test_player_turns_complete_when_all_revealed():
    """Test that PLAYER_TURNS phase ends when all players revealed."""
    print("\n=== Test: Player Turns Complete ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS

    # Not complete if not all revealed
    player1.has_revealed_this_round = True
    player2.has_revealed_this_round = False

    assert phase_manager.should_advance_phase() == False, "Should not advance with unrevealed players"

    # Complete when all revealed
    player2.has_revealed_this_round = True

    assert phase_manager.should_advance_phase() == True, "Should advance when all revealed"

    print("✓ Player turns completion check works")


def test_combat_complete_when_all_conflicts_resolved():
    """Test that COMBAT phase ends when conflicts are resolved."""
    print("\n=== Test: Combat Complete ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.COMBAT

    # Not complete with unresolved conflict
    game.board.current_conflict = ConflictCard(
        id="conflict1",
        name="Conflict 1",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[]
    )

    assert phase_manager.should_advance_phase() == False, "Should not advance with unresolved conflict"

    # Complete when resolved
    game.board.current_conflict = None

    assert phase_manager.should_advance_phase() == True, "Should advance when conflict resolved"

    print("✓ Combat completion check works")


# ==================== PHASE CLEANUP/INITIALIZE TESTS ====================

def test_cleanup_temp_resources_after_player_turns():
    """Test that persuasion and swords are cleared after PLAYER_TURNS."""
    print("\n=== Test: Cleanup Temp Resources ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Set temp resources
    player1.temp_persuasion = 10
    player1.temp_swords = 3
    player1.has_revealed_this_round = True

    player2.temp_persuasion = 5
    player2.temp_swords = 2
    player2.has_revealed_this_round = True

    # Cleanup PLAYER_TURNS phase
    phase_manager._cleanup_phase(GamePhase.PLAYER_TURNS)

    # Check cleanup
    assert player1.temp_persuasion == 0, f"Expected 0 persuasion, got {player1.temp_persuasion}"
    assert player1.temp_swords == 0, f"Expected 0 swords, got {player1.temp_swords}"
    assert player1.has_revealed_this_round == False, "Should reset reveal status"

    assert player2.temp_persuasion == 0, f"Expected 0 persuasion, got {player2.temp_persuasion}"
    assert player2.temp_swords == 0, f"Expected 0 swords, got {player2.temp_swords}"

    print("✓ Temp resources cleaned up")


def test_cleanup_sandworms_after_combat():
    """Test that sandworms die after COMBAT phase."""
    print("\n=== Test: Cleanup Sandworms ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Deploy sandworms
    player1.sandworms_in_conflict = 1
    player2.sandworms_in_conflict = 2

    # Cleanup COMBAT phase
    phase_manager._cleanup_phase(GamePhase.COMBAT)

    # Sandworms should be gone
    assert player1.sandworms_in_conflict == 0, "Sandworms should die after combat"
    assert player2.sandworms_in_conflict == 0, "Sandworms should die after combat"

    print("✓ Sandworms cleaned up")


def test_reset_agents_in_recall_phase():
    """Test that agents_available is reset in RECALL."""
    print("\n=== Test: Reset Agents in RECALL ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Use up agents
    player1.agents_available = 0
    player1.total_available_agents = 2

    player2.agents_available = 1
    player2.total_available_agents = 3

    # Cleanup RECALL phase (resets agents)
    phase_manager._cleanup_phase(GamePhase.RECALL)

    # Agents should be restored
    assert player1.agents_available == 2, f"Expected 2 agents, got {player1.agents_available}"
    assert player2.agents_available == 3, f"Expected 3 agents, got {player2.agents_available}"

    print("✓ Agents reset in RECALL")


def test_increment_round_in_begin_round():
    """Test that round counter increments in BEGIN_ROUND phase."""
    print("\n=== Test: Increment Round ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    game.current_round = 1

    # Initialize BEGIN_ROUND phase
    phase_manager._initialize_phase(GamePhase.BEGIN_ROUND)

    # Round should increment
    assert game.current_round == 2, f"Expected round 2, got {game.current_round}"

    print("✓ Round increments in BEGIN_ROUND")


def test_flip_conflict_in_begin_round():
    """Test that new conflict is flipped in BEGIN_ROUND phase."""
    print("\n=== Test: Flip Conflict ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    conflict1 = ConflictCard(
        id="conflict1",
        name="Conflict 1",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[]
    )

    game.board.conflict_deck = [conflict1]
    game.board.current_conflict = None

    # Initialize BEGIN_ROUND phase
    phase_manager._initialize_phase(GamePhase.BEGIN_ROUND)

    # Conflict should be flipped
    assert game.board.current_conflict is not None, "Should have a conflict"
    assert game.board.current_conflict.id == "conflict1", "Should be conflict1"

    print("✓ Conflict flipped in BEGIN_ROUND")


# ==================== MARK PLAYER ACTION TESTS ====================

def test_mark_player_action_complete():
    """Test marking player actions as complete."""
    print("\n=== Test: Mark Player Action Complete ===")

    game, player1, player2 = setup_test_game()
    phase_manager = PhaseManager(game)

    # Mark agent placement
    phase_manager.mark_player_action_complete("player1", "place_agent")

    assert "player1" in phase_manager.players_who_acted, "Should track agent placement"

    # Mark reveal
    phase_manager.mark_player_action_complete("player2", "reveal")

    assert "player2" in phase_manager.players_who_revealed, "Should track reveal"
    assert player2.has_revealed_this_round == True, "Should set reveal flag on player"

    print("✓ Player actions marked correctly")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all phase manager tests."""
    print("\n" + "="*70)
    print("PHASE MANAGER UNIT TESTS")
    print("="*70)

    # Phase transitions
    test_phase_progression()
    test_phase_loops_after_recall()
    test_game_over_when_vp_threshold()
    test_game_over_when_conflicts_empty()

    # Turn order
    test_turn_order_in_player_turns_phase()
    test_advance_turn_cycles_through_players()

    # Phase validation
    test_cannot_place_agent_after_reveal()
    test_can_reveal_with_agents_remaining()
    test_cannot_reveal_twice()
    test_cannot_acquire_before_reveal()
    test_can_acquire_after_reveal()
    test_cannot_do_player_actions_in_makers_phase()

    # Phase completion
    test_player_turns_complete_when_all_revealed()
    test_combat_complete_when_all_conflicts_resolved()

    # Lifecycle hooks
    test_cleanup_temp_resources_after_player_turns()
    test_cleanup_sandworms_after_combat()
    test_reset_agents_in_recall_phase()
    test_increment_round_in_begin_round()
    test_flip_conflict_in_begin_round()

    # Action tracking
    test_mark_player_action_complete()

    print("\n" + "="*70)
    print("✅ ALL PHASE MANAGER TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
