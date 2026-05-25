"""
Integration tests for PhaseManager with ActionExecutor and ActionGenerator.

Tests that phase management works correctly with the full game flow.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, ImperiumCard, CardType
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.phase_manager import PhaseManager
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, RevealAction
from src.engine.actions.action_generator import ActionGenerator


def setup_test_game():
    """Create a game with PhaseManager integration."""
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

    # Create test card
    card1 = ImperiumCard(
        id="card1",
        name="Test Card",
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=3,
        agent_icons=["fremen"],
        agent_effects=[
            {"type": "resource", "resource": "water", "amount": 1},
            {"type": "resource", "resource": "troop", "amount": 1}
        ],
        reveal_effects=[
            {"type": "resource", "resource": "persuasion", "amount": 2}
        ]
    )

    player1.hand.add_card(card1)

    # Create board
    board = Board()
    board.spaces = [
        BoardSpace(
            id="fremen_camp",
            name="Fremen Camp",
            agent_icon="fremen",
            effects=[{"type": "resource", "resource": "water", "amount": 1}]
        )
    ]

    # Create game
    game = Game(
        players=[player1, player2],
        board=board,
        current_player_index=0,
        first_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS,
        current_round=1
    )

    return game, player1, player2, card1


# ==================== INTEGRATION TESTS ====================

def test_phase_manager_blocks_invalid_actions():
    """Test that PhaseManager prevents actions in wrong phase."""
    print("\n=== Test: PhaseManager Blocks Invalid Actions ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionExecutor with PhaseManager
    action_exec = ActionExecutor(game, phase_manager)

    # Set phase to MAKERS (automatic phase)
    game.current_phase = GamePhase.MAKERS

    # Try to place agent (should fail)
    location = game.board.spaces[0]
    action = PlaceAgentAction(
        player_id="player1",
        card=card1,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"] == False, "Should not allow agent placement in MAKERS phase"
    assert "Cannot place agent" in result["error"], f"Expected phase error, got: {result['error']}"

    print("✓ PhaseManager blocks invalid actions")


def test_action_generator_respects_phase():
    """Test that ActionGenerator returns no actions when phase doesn't allow."""
    print("\n=== Test: ActionGenerator Respects Phase ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionGenerator with PhaseManager
    action_gen = ActionGenerator(game, phase_manager)

    # In PLAYER_TURNS phase, should have playable cards
    game.current_phase = GamePhase.PLAYER_TURNS
    player1.has_revealed_this_round = False

    playable = action_gen.get_playable_imperium_cards("player1")
    assert len(playable) == 1, f"Should have 1 playable card, got {len(playable)}"

    # In COMBAT phase, should have no playable cards
    game.current_phase = GamePhase.COMBAT

    playable = action_gen.get_playable_imperium_cards("player1")
    assert len(playable) == 0, f"Should have 0 playable cards in COMBAT, got {len(playable)}"

    print("✓ ActionGenerator respects phase")


def test_action_generator_blocks_after_reveal():
    """Test that ActionGenerator blocks agent placement after reveal."""
    print("\n=== Test: ActionGenerator Blocks After Reveal ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionGenerator with PhaseManager
    action_gen = ActionGenerator(game, phase_manager)

    game.current_phase = GamePhase.PLAYER_TURNS

    # Before reveal - should have cards
    player1.has_revealed_this_round = False
    playable = action_gen.get_playable_imperium_cards("player1")
    assert len(playable) == 1, "Should have playable cards before reveal"

    # After reveal - should have no cards
    player1.has_revealed_this_round = True
    playable = action_gen.get_playable_imperium_cards("player1")
    assert len(playable) == 0, "Should have no playable cards after reveal"

    print("✓ ActionGenerator blocks after reveal")


def test_phase_manager_tracks_player_actions():
    """Test that PhaseManager tracks completed actions."""
    print("\n=== Test: PhaseManager Tracks Actions ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionExecutor with PhaseManager
    action_exec = ActionExecutor(game, phase_manager)

    game.current_phase = GamePhase.PLAYER_TURNS

    # Place agent
    location = game.board.spaces[0]
    action = PlaceAgentAction(
        player_id="player1",
        card=card1,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)
    assert result["success"] == True, f"Agent placement should succeed: {result.get('error', '')}"

    # Check that PhaseManager tracked the action
    assert "player1" in phase_manager.players_who_acted, "Should track player action"

    print("✓ PhaseManager tracks actions")


def test_reveal_marks_player_in_phase_manager():
    """Test that reveal action updates PhaseManager tracking."""
    print("\n=== Test: Reveal Marks Player ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionExecutor with PhaseManager
    action_exec = ActionExecutor(game, phase_manager)

    game.current_phase = GamePhase.PLAYER_TURNS

    # Reveal
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)

    assert result["success"] == True, "Reveal should succeed"

    # Check PhaseManager tracking
    assert "player1" in phase_manager.players_who_revealed, "Should track reveal"
    assert player1.has_revealed_this_round == True, "Should mark player as revealed"

    print("✓ Reveal marks player in PhaseManager")


def test_complete_turn_flow_with_phase_manager():
    """Test a complete turn flow: place agent → reveal → check phase completion."""
    print("\n=== Test: Complete Turn Flow ===")

    game, player1, player2, card1 = setup_test_game()

    # Add a card to player2's hand
    card2 = ImperiumCard(
        id="card2",
        name="Test Card 2",
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=2,
        agent_icons=["fremen"],
        agent_effects=[{"type": "resource", "resource": "water", "amount": 1}],
        reveal_effects=[{"type": "resource", "resource": "persuasion", "amount": 1}]
    )
    player2.hand.add_card(card2)

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    # Create ActionExecutor and ActionGenerator
    action_exec = ActionExecutor(game, phase_manager)
    action_gen = ActionGenerator(game, phase_manager)

    game.current_phase = GamePhase.PLAYER_TURNS

    # === Player 1 Turn ===

    # 1. Place agent
    playable = action_gen.get_playable_imperium_cards("player1")
    assert len(playable) == 1, "Player 1 should have 1 playable card"

    location = game.board.spaces[0]
    action = PlaceAgentAction(
        player_id="player1",
        card=card1,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)
    assert result["success"] == True, "Player 1 agent placement should succeed"

    # 2. Reveal
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)
    assert result["success"] == True, "Player 1 reveal should succeed"

    # 3. Check phase not complete (player 2 hasn't revealed)
    assert phase_manager.should_advance_phase() == False, "Phase should not advance yet"

    # === Player 2 Turn ===

    # 4. Player 2 reveals (skips agent placement)
    reveal_action = RevealAction(player_id="player2")
    result = action_exec.execute_reveal(reveal_action)
    assert result["success"] == True, "Player 2 reveal should succeed"

    # 5. Check phase IS complete (both revealed)
    assert phase_manager.should_advance_phase() == True, "Phase should advance after both revealed"

    # 6. Advance phase
    result = phase_manager.advance_phase()
    assert game.current_phase == GamePhase.COMBAT, f"Should advance to COMBAT, got {game.current_phase}"

    print("✓ Complete turn flow works")


def test_phase_cleanup_between_phases():
    """Test that phase cleanup works when advancing phases."""
    print("\n=== Test: Phase Cleanup ===")

    game, player1, player2, card1 = setup_test_game()

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.PLAYER_TURNS

    # Set temp resources
    player1.temp_persuasion = 10
    player1.temp_swords = 3
    player1.has_revealed_this_round = True

    player2.temp_persuasion = 5
    player2.has_revealed_this_round = True

    # Advance phase (should cleanup)
    result = phase_manager.advance_phase()

    # Check cleanup happened
    assert player1.temp_persuasion == 0, "Should cleanup temp persuasion"
    # temp_swords are intentionally kept through COMBAT phase (used for combat resolution)
    assert player1.temp_swords == 3, "Should preserve temp swords for combat"
    assert player1.has_revealed_this_round == False, "Should reset reveal status"

    assert player2.temp_persuasion == 0, "Should cleanup player 2 persuasion"

    print("✓ Phase cleanup works")


def test_phase_initialize_when_advancing():
    """Test that phase initialization works when advancing phases."""
    print("\n=== Test: Phase Initialize ===")

    game, player1, player2, card1 = setup_test_game()

    # Add conflict to deck so game doesn't end
    from src.models.card import ConflictCard
    conflict = ConflictCard(
        id="conflict1",
        name="Test Conflict",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[]
    )
    game.board.conflict_deck = [conflict]

    # Create PhaseManager
    phase_manager = PhaseManager(game)

    game.current_phase = GamePhase.RECALL
    game.current_round = 1

    # Advance phase (RECALL → BEGIN_ROUND)
    result = phase_manager.advance_phase()

    # Check initialization happened
    assert game.current_phase == GamePhase.BEGIN_ROUND, f"Should advance to BEGIN_ROUND, got {game.current_phase}"
    assert game.current_round == 2, f"Should increment round, got {game.current_round}"

    print("✓ Phase initialize works")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("PHASE MANAGER INTEGRATION TESTS")
    print("="*70)

    test_phase_manager_blocks_invalid_actions()
    test_action_generator_respects_phase()
    test_action_generator_blocks_after_reveal()
    test_phase_manager_tracks_player_actions()
    test_reveal_marks_player_in_phase_manager()
    test_complete_turn_flow_with_phase_manager()
    test_phase_cleanup_between_phases()
    test_phase_initialize_when_advancing()

    print("\n" + "="*70)
    print("✅ ALL INTEGRATION TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
