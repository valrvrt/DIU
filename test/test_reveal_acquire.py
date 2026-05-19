"""
Tests for Reveal and Acquisition flow.

Tests that players can reveal cards, calculate persuasion, and acquire cards from Imperium row.
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
from src.engine.phase_manager import PhaseManager
from src.engine.deck_manager import DeckManager
from src.engine.action_executor import ActionExecutor, PlaceAgentAction, RevealAction, AcquireCardAction
from src.engine.action_generator import ActionGenerator


def create_test_card(card_id: str, name: str, cost: int = 3, persuasion: int = 1) -> ImperiumCard:
    """Helper to create test cards with reveal persuasion."""
    return ImperiumCard(
        id=card_id,
        name=name,
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=cost,
        agent_icons=["fremen"],
        agent_effects={"base": {"water": 1}},
        reveal_effects={"base": {"persuasion": persuasion}}
    )


def setup_test_game():
    """Create a game for reveal/acquire testing."""
    # Create leader
    leader = LeaderCard(id="leader1", name="Test Leader", type="Leader", card_type=CardType.LEADER)

    # Create deck with 10 cards (2 persuasion each when revealed)
    deck_cards = [create_test_card(f"deck_{i}", f"Deck Card {i}", persuasion=2) for i in range(10)]

    # Create player
    player = Player(
        player_id="player1",
        name="Player 1",
        leader=leader,
        color="blue",
        deck=Deck(cards=deck_cards.copy()),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=10,
        spice=1,
        agents_available=2,
        total_available_agents=2
    )

    # Create board with spaces
    board = Board()
    board.spaces = [
        BoardSpace(
            id="fremen_camp",
            name="Fremen Camp",
            agent_icon="fremen",
            effects={"water": 1}
        )
    ]

    # Create Imperium row (5 cards with different costs)
    board.imperium_row = [
        create_test_card("row_1", "Cheap Card", cost=2),
        create_test_card("row_2", "Affordable Card", cost=5),
        create_test_card("row_3", "Mid Card", cost=7),
        create_test_card("row_4", "Expensive Card", cost=10),
        create_test_card("row_5", "Very Expensive", cost=12)
    ]

    # Create Imperium deck for refill
    board.imperium_deck = [create_test_card(f"deck_{i}", f"Imperium {i}") for i in range(5)]

    # Create reserve piles
    board.reserve_prepare_the_way = [create_test_card("ptw", "Prepare The Way", cost=2)]
    board.reserve_spice_must_flow = [create_test_card("smf", "Spice Must Flow", cost=8)]

    # Create game
    game = Game(
        players=[player],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS
    )

    return game, player


# ==================== REVEAL TESTS ====================

def test_reveal_calculates_persuasion():
    """Test that revealing cards calculates persuasion correctly."""
    print("\n=== Test: Reveal Calculates Persuasion ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Draw 5 cards (each gives 2 persuasion)
    deck_manager.draw_starting_hand("player1")
    assert player.hand.size == 5

    # Place one agent
    card_to_play = player.hand.cards[0]
    location = game.board.spaces[0]
    action = PlaceAgentAction(
        player_id="player1",
        card=card_to_play,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )
    result = action_exec.execute_place_agent(action)
    assert result["success"] == True

    # Reveal (1 played + 4 in hand = 5 cards × 2 persuasion = 10 total)
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)

    assert result["success"] == True
    assert result["total_persuasion"] == 10
    assert player.temp_persuasion == 10
    assert player.has_revealed_this_round == True

    print("✓ Reveal calculates persuasion correctly")


def test_reveal_without_playing_agent():
    """Test revealing without placing any agents."""
    print("\n=== Test: Reveal Without Playing Agent ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Draw 5 cards
    deck_manager.draw_starting_hand("player1")

    # Reveal immediately (all 5 cards in hand)
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)

    assert result["success"] == True
    assert result["total_persuasion"] == 10  # 5 cards × 2 persuasion
    assert player.temp_persuasion == 10

    print("✓ Reveal without playing agent works")


# ==================== ACQUISITION OPTIONS TESTS ====================

def test_get_acquisition_options():
    """Test getting available acquisition options."""
    print("\n=== Test: Get Acquisition Options ===")

    game, player = setup_test_game()

    # Create managers
    action_gen = ActionGenerator(game)

    # Set player's temp_persuasion
    player.temp_persuasion = 8
    player.has_revealed_this_round = True

    # Get options
    options = action_gen.get_acquisition_options("player1")

    assert options["total_persuasion"] == 8
    assert len(options["imperium_row"]) == 5  # All cards in row
    # Should be able to afford cards with cost <= 8
    assert len(options["affordable_from_row"]) == 3  # Costs: 2, 5, 7
    assert options["can_afford_prepare"] == True  # Cost 2
    assert options["can_afford_spice"] == True  # Cost 8

    print("✓ Get acquisition options works")


def test_get_acquisition_options_low_persuasion():
    """Test acquisition options with low persuasion."""
    print("\n=== Test: Acquisition Options with Low Persuasion ===")

    game, player = setup_test_game()
    action_gen = ActionGenerator(game)

    # Set low persuasion
    player.temp_persuasion = 3
    player.has_revealed_this_round = True

    options = action_gen.get_acquisition_options("player1")

    assert options["total_persuasion"] == 3
    # Can only afford cost 2 card
    assert len(options["affordable_from_row"]) == 1
    assert options["can_afford_prepare"] == True  # Cost 2
    assert options["can_afford_spice"] == False  # Cost 8

    print("✓ Low persuasion limits options correctly")


# ==================== ACQUISITION EXECUTION TESTS ====================

def test_acquire_card_from_imperium():
    """Test acquiring a card from Imperium row."""
    print("\n=== Test: Acquire Card from Imperium ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Set up player state (revealed with persuasion)
    player.temp_persuasion = 10
    player.has_revealed_this_round = True

    # Select card to acquire (cost 5)
    card_to_acquire = game.board.imperium_row[1]
    assert card_to_acquire.cost == 5

    initial_row_size = len(game.board.imperium_row)

    # Acquire
    action = AcquireCardAction(
        player_id="player1",
        card=card_to_acquire,
        source="row"
    )
    result = action_exec.execute_acquire_card(action)

    assert result["success"] == True
    assert result["card"] == card_to_acquire.name
    assert result["cost"] == 5
    assert result["remaining_persuasion"] == 5

    # Card should be in discard pile
    assert player.discard_pile.size == 1

    # Acquired cards go directly to discard (not tracked in played_cards_this_turn)
    # played_cards_this_turn is only for cards played during agent turns

    # Imperium row should be refilled
    assert len(game.board.imperium_row) == initial_row_size

    print("✓ Acquire card from Imperium works")


def test_acquire_multiple_cards():
    """Test acquiring multiple cards in sequence."""
    print("\n=== Test: Acquire Multiple Cards ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Set up player with enough persuasion
    player.temp_persuasion = 15
    player.has_revealed_this_round = True

    # Acquire first card (cost 2) - get reference before removing
    card1 = game.board.imperium_row[0]
    card1_cost = card1.cost
    action1 = AcquireCardAction(player_id="player1", card=card1, source="row")
    result1 = action_exec.execute_acquire_card(action1)

    assert result1["success"] == True
    assert result1["remaining_persuasion"] == 13

    # Acquire second card - row has been refilled, so get fresh reference
    # Find a card we can afford
    card2 = None
    for card in game.board.imperium_row:
        if card.cost <= player.temp_persuasion:
            card2 = card
            break

    assert card2 is not None, "Should have at least one affordable card"
    card2_cost = card2.cost

    action2 = AcquireCardAction(player_id="player1", card=card2, source="row")
    result2 = action_exec.execute_acquire_card(action2)

    assert result2["success"] == True
    assert result2["remaining_persuasion"] == 13 - card2_cost

    # Both cards in discard
    assert player.discard_pile.size == 2

    # Acquired cards do NOT go to played_cards_this_turn
    # (they go directly to discard pile)

    print("✓ Acquire multiple cards works")


def test_acquire_without_enough_persuasion():
    """Test that acquisition fails without enough persuasion."""
    print("\n=== Test: Acquire Without Enough Persuasion ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Set up player with low persuasion
    player.temp_persuasion = 3
    player.has_revealed_this_round = True

    # Try to acquire expensive card (cost 10)
    card_to_acquire = game.board.imperium_row[3]
    assert card_to_acquire.cost == 10

    action = AcquireCardAction(player_id="player1", card=card_to_acquire, source="row")
    result = action_exec.execute_acquire_card(action)

    assert result["success"] == False
    assert "Not enough persuasion" in result["error"]
    assert player.discard_pile.size == 0

    print("✓ Acquisition without persuasion blocked")


def test_acquire_before_reveal_blocked():
    """Test that acquisition is blocked before revealing."""
    print("\n=== Test: Acquire Before Reveal Blocked ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Player has NOT revealed
    player.has_revealed_this_round = False
    player.temp_persuasion = 10

    # Try to acquire
    card_to_acquire = game.board.imperium_row[0]
    action = AcquireCardAction(player_id="player1", card=card_to_acquire, source="row")
    result = action_exec.execute_acquire_card(action)

    assert result["success"] == False
    assert "Must reveal" in result["error"]

    print("✓ Acquisition before reveal blocked")


def test_acquire_from_reserve():
    """Test acquiring from reserve pile."""
    print("\n=== Test: Acquire from Reserve ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # Set up player
    player.temp_persuasion = 5
    player.has_revealed_this_round = True

    # Acquire Prepare the Way (cost 2)
    reserve_card = game.board.reserve_prepare_the_way[0]
    action = AcquireCardAction(player_id="player1", card=reserve_card, source="prepare")
    result = action_exec.execute_acquire_card(action)

    assert result["success"] == True
    assert result["remaining_persuasion"] == 3
    assert player.discard_pile.size == 1

    print("✓ Acquire from reserve works")


# ==================== INTEGRATION TESTS ====================

def test_complete_reveal_acquire_flow():
    """Test complete flow: place agent → reveal → acquire → discard."""
    print("\n=== Test: Complete Reveal→Acquire Flow ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)

    # 1. Draw starting hand
    deck_manager.draw_starting_hand("player1")
    assert player.hand.size == 5

    # 2. Place agent
    card_to_play = player.hand.cards[0]
    location = game.board.spaces[0]
    action = PlaceAgentAction(
        player_id="player1",
        card=card_to_play,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )
    result = action_exec.execute_place_agent(action)
    assert result["success"] == True
    assert len(player.played_cards_this_turn) == 1

    # 3. Reveal (5 cards × 2 persuasion = 10)
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)
    assert result["success"] == True
    assert player.temp_persuasion == 10
    assert len(player.played_cards_this_turn) == 5  # All cards now tracked

    # 4. Acquire card (cost 5)
    card_to_acquire = game.board.imperium_row[1]
    acquire_action = AcquireCardAction(player_id="player1", card=card_to_acquire, source="row")
    result = action_exec.execute_acquire_card(acquire_action)
    assert result["success"] == True
    assert player.temp_persuasion == 5

    # Acquired card goes directly to discard (not played_cards_this_turn)
    assert player.discard_pile.size == 1  # Acquired card
    assert len(player.played_cards_this_turn) == 5  # Only the 5 original cards

    # 5. Advance phase (should discard all played cards)
    game.current_phase = GamePhase.PLAYER_TURNS
    phase_manager.advance_phase()

    # All played cards + acquired card should be in discard
    # (5 played cards discarded at phase cleanup + 1 already in discard from acquisition)
    assert player.discard_pile.size == 6  # 5 revealed + 1 acquired
    assert len(player.played_cards_this_turn) == 0  # Cleared

    print("✓ Complete reveal→acquire flow works")


def test_persuasion_updates_after_each_acquisition():
    """Test that persuasion decreases correctly after each acquisition."""
    print("\n=== Test: Persuasion Updates After Each Acquisition ===")

    game, player = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    action_gen = ActionGenerator(game)

    # Set up player
    player.temp_persuasion = 15
    player.has_revealed_this_round = True

    # Check options (should show all cards affordable with 15)
    # Row has cards with costs: 2, 5, 7, 10, 12
    options1 = action_gen.get_acquisition_options("player1")
    assert len(options1["affordable_from_row"]) >= 3  # At least costs 2, 5, 7

    # Acquire first card (cost 5)
    card1 = game.board.imperium_row[1]
    action1 = AcquireCardAction(player_id="player1", card=card1, source="row")
    result1 = action_exec.execute_acquire_card(action1)
    assert result1["success"] == True
    assert player.temp_persuasion == 10

    # Check options again (should have fewer affordable cards)
    options2 = action_gen.get_acquisition_options("player1")
    # After spending 5, we have 10 left - should still have at least 2 affordable cards
    assert len(options2["affordable_from_row"]) >= 2

    print("✓ Persuasion updates correctly after each acquisition")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all reveal/acquire tests."""
    print("\n" + "="*70)
    print("REVEAL AND ACQUISITION TESTS")
    print("="*70)

    # Reveal tests
    test_reveal_calculates_persuasion()
    test_reveal_without_playing_agent()

    # Acquisition options tests
    test_get_acquisition_options()
    test_get_acquisition_options_low_persuasion()

    # Acquisition execution tests
    test_acquire_card_from_imperium()
    test_acquire_multiple_cards()
    test_acquire_without_enough_persuasion()
    test_acquire_before_reveal_blocked()
    test_acquire_from_reserve()

    # Integration tests
    test_complete_reveal_acquire_flow()
    test_persuasion_updates_after_each_acquisition()

    print("\n" + "="*70)
    print("✅ ALL REVEAL AND ACQUISITION TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
