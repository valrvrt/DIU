"""
Unit tests for DeckManager.

Tests draw, discard, shuffle, acquire, and trash operations.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, ImperiumCard, CardType
from src.models.deck import Deck
from src.models.board import Board
from src.engine.deck_manager import DeckManager


def create_test_card(card_id: str, name: str, cost: int = 3) -> ImperiumCard:
    """Helper to create test cards."""
    return ImperiumCard(
        id=card_id,
        name=name,
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=cost,
        agent_icons=["fremen"],
        agent_effects={"base": {"water": 1}},
        reveal_effects={"base": {"persuasion": 1}}
    )


def setup_test_game():
    """Create a minimal game for deck testing."""
    # Create leader
    leader = LeaderCard(
        id="leader1",
        name="Test Leader",
        type="Leader",
        card_type=CardType.LEADER
    )

    # Create 10 test cards for deck (starting deck)
    deck_cards = [create_test_card(f"deck_card_{i}", f"Deck Card {i}") for i in range(10)]

    # Create player with deck
    deck = Deck()
    deck.cards = deck_cards.copy()

    hand = Deck()
    discard_pile = Deck()

    player = Player(
        player_id="player1",
        name="Player 1",
        leader=leader,
        color="blue",
        deck=deck,
        hand=hand,
        discard_pile=discard_pile,
        water=2,
        solari=5,
        spice=1
    )

    # Create board with Imperium row
    board = Board()
    board.imperium_row = [
        create_test_card("row_1", "Row Card 1", cost=2),
        create_test_card("row_2", "Row Card 2", cost=3),
        create_test_card("row_3", "Row Card 3", cost=5)
    ]
    board.imperium_deck = [create_test_card(f"deck_{i}", f"Deck Card {i}") for i in range(5)]

    # Create reserve piles
    board.reserve_prepare_the_way = [create_test_card("ptw_1", "Prepare The Way", cost=2)]
    board.reserve_spice_must_flow = [create_test_card("smf_1", "Spice Must Flow", cost=8)]

    # Create game
    game = Game(
        players=[player],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS
    )

    return game, player


# ==================== DRAW TESTS ====================

def test_draw_cards_from_deck():
    """Test drawing cards from deck into hand."""
    print("\n=== Test: Draw Cards from Deck ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Initially: 10 in deck, 0 in hand
    assert player.deck.size == 10
    assert player.hand.size == 0

    # Draw 5 cards
    result = deck_manager.draw_cards("player1", 5)

    assert result["success"] == True
    assert result["cards_drawn"] == 5
    assert player.hand.size == 5
    assert player.deck.size == 5

    print("✓ Draw cards from deck works")


def test_draw_starting_hand():
    """Test drawing starting hand (5 cards)."""
    print("\n=== Test: Draw Starting Hand ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    result = deck_manager.draw_starting_hand("player1")

    assert result["success"] == True
    assert result["cards_drawn"] == 5
    assert player.hand.size == 5

    print("✓ Draw starting hand works")


def test_draw_with_auto_shuffle():
    """Test that drawing auto-shuffles discard when deck empty."""
    print("\n=== Test: Auto-Shuffle on Draw ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Put 8 cards in discard
    for _ in range(8):
        card = player.deck.draw()
        player.discard_pile.add_card(card)

    # Deck now has 2 cards
    assert player.deck.size == 2
    assert player.discard_pile.size == 8

    # Draw 5 cards (should auto-shuffle discard)
    result = deck_manager.draw_cards("player1", 5)

    assert result["success"] == True
    assert result["cards_drawn"] == 5
    assert player.hand.size == 5
    # Discard should be empty (shuffled into deck)
    assert player.discard_pile.size == 0

    print("✓ Auto-shuffle on draw works")


def test_draw_when_empty():
    """Test drawing when both deck and discard are empty."""
    print("\n=== Test: Draw When Empty ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Empty the deck
    while not player.deck.is_empty:
        player.deck.draw()

    # Try to draw
    result = deck_manager.draw_cards("player1", 5)

    assert result["success"] == True
    assert result["cards_drawn"] == 0  # No cards available
    assert player.hand.size == 0

    print("✓ Draw when empty handled correctly")


# ==================== DISCARD TESTS ====================

def test_discard_played_cards():
    """Test discarding played cards at end of turn."""
    print("\n=== Test: Discard Played Cards ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Simulate playing 3 cards
    played_cards = [create_test_card(f"played_{i}", f"Played {i}") for i in range(3)]
    player.played_cards_this_turn = played_cards.copy()

    # Initially: 0 in discard
    assert player.discard_pile.size == 0

    # Discard played cards
    result = deck_manager.discard_played_cards("player1")

    assert result["success"] == True
    assert result["cards_discarded"] == 3
    assert player.discard_pile.size == 3
    assert len(player.played_cards_this_turn) == 0  # Cleared

    print("✓ Discard played cards works")


def test_discard_hand():
    """Test discarding entire hand."""
    print("\n=== Test: Discard Hand ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Draw 5 cards into hand
    deck_manager.draw_cards("player1", 5)

    assert player.hand.size == 5
    assert player.discard_pile.size == 0

    # Discard entire hand
    result = deck_manager.discard_hand("player1")

    assert result["success"] == True
    assert result["cards_discarded"] == 5
    assert player.hand.size == 0
    assert player.discard_pile.size == 5

    print("✓ Discard hand works")


# ==================== ACQUIRE TESTS ====================

def test_acquire_card_from_imperium():
    """Test acquiring a card from Imperium row."""
    print("\n=== Test: Acquire from Imperium ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Give player persuasion
    player.temp_persuasion = 5

    # Get card from row
    card_to_acquire = game.board.imperium_row[1]  # Cost 3
    assert card_to_acquire.cost == 3

    # Acquire
    result = deck_manager.acquire_card_from_imperium(
        "player1",
        card_to_acquire,
        persuasion_cost=3
    )

    assert result["success"] == True
    assert result["card_acquired"] == card_to_acquire.name
    assert result["persuasion_spent"] == 3
    assert result["persuasion_remaining"] == 2
    assert player.discard_pile.size == 1  # Card added to discard
    # Row should be refilled (3 cards remain, refilled to 5)
    assert len(game.board.imperium_row) >= 3  # At least 3 cards

    print("✓ Acquire from Imperium works")


def test_acquire_without_enough_persuasion():
    """Test that acquisition fails without enough persuasion."""
    print("\n=== Test: Acquire Without Persuasion ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Give player only 2 persuasion
    player.temp_persuasion = 2

    # Try to acquire 3-cost card
    card_to_acquire = game.board.imperium_row[1]  # Cost 3

    result = deck_manager.acquire_card_from_imperium(
        "player1",
        card_to_acquire,
        persuasion_cost=3
    )

    assert result["success"] == False
    assert "Not enough persuasion" in result["error"]

    print("✓ Acquire without persuasion blocked")


def test_acquire_reserve_prepare_the_way():
    """Test acquiring from reserve pile."""
    print("\n=== Test: Acquire from Reserve ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Give player persuasion
    player.temp_persuasion = 5

    # Acquire from reserve
    result = deck_manager.acquire_reserve_card(
        "player1",
        card_type="prepare_the_way",
        persuasion_cost=2
    )

    assert result["success"] == True
    assert result["persuasion_spent"] == 2
    assert result["persuasion_remaining"] == 3
    assert player.discard_pile.size == 1

    print("✓ Acquire from reserve works")


# ==================== TRASH TESTS ====================

def test_trash_card_from_hand():
    """Test trashing a card from hand."""
    print("\n=== Test: Trash from Hand ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Draw cards into hand
    deck_manager.draw_cards("player1", 3)
    card_to_trash = player.hand.cards[0]

    initial_hand_size = player.hand.size

    # Trash
    result = deck_manager.trash_card(
        "player1",
        card_to_trash,
        source="hand"
    )

    assert result["success"] == True
    assert result["card_trashed"] == card_to_trash.name
    assert player.hand.size == initial_hand_size - 1
    # Card not in discard (removed from game)
    assert player.discard_pile.size == 0

    print("✓ Trash from hand works")


def test_trash_card_from_played():
    """Test trashing a card from played cards this turn."""
    print("\n=== Test: Trash from Played ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Simulate playing cards
    played_cards = [create_test_card(f"played_{i}", f"Played {i}") for i in range(3)]
    player.played_cards_this_turn = played_cards.copy()

    card_to_trash = played_cards[1]

    # Trash
    result = deck_manager.trash_card(
        "player1",
        card_to_trash,
        source="played"
    )

    assert result["success"] == True
    assert len(player.played_cards_this_turn) == 2
    assert card_to_trash not in player.played_cards_this_turn

    print("✓ Trash from played works")


def test_trash_card_from_discard():
    """Test trashing a card from discard pile."""
    print("\n=== Test: Trash from Discard ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Put cards in discard
    discard_cards = [create_test_card(f"discard_{i}", f"Discard {i}") for i in range(3)]
    for card in discard_cards:
        player.discard_pile.add_card(card)

    card_to_trash = discard_cards[1]

    # Trash
    result = deck_manager.trash_card(
        "player1",
        card_to_trash,
        source="discard"
    )

    assert result["success"] == True
    assert player.discard_pile.size == 2

    print("✓ Trash from discard works")


# ==================== QUERY TESTS ====================

def test_get_deck_state():
    """Test getting deck state."""
    print("\n=== Test: Get Deck State ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Setup state
    deck_manager.draw_cards("player1", 5)
    player.played_cards_this_turn = [create_test_card("test", "Test")]

    result = deck_manager.get_deck_state("player1")

    assert result["success"] == True
    assert result["hand_size"] == 5
    assert result["deck_size"] == 5
    assert result["discard_size"] == 0
    assert result["played_this_turn"] == 1

    print("✓ Get deck state works")


def test_get_acquirable_cards():
    """Test getting list of acquirable cards."""
    print("\n=== Test: Get Acquirable Cards ===")

    game, player = setup_test_game()
    deck_manager = DeckManager(game)

    # Give player persuasion
    player.temp_persuasion = 4

    result = deck_manager.get_acquirable_cards("player1")

    assert result["success"] == True
    assert result["persuasion"] == 4
    # Should include cards with cost <= 4 (cards with cost 2 and 3)
    assert len(result["imperium_cards"]) == 2
    # Should include prepare_the_way (cost 2)
    assert len(result["reserve_cards"]) == 1

    print("✓ Get acquirable cards works")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all deck manager tests."""
    print("\n" + "="*70)
    print("DECK MANAGER UNIT TESTS")
    print("="*70)

    # Draw tests
    test_draw_cards_from_deck()
    test_draw_starting_hand()
    test_draw_with_auto_shuffle()
    test_draw_when_empty()

    # Discard tests
    test_discard_played_cards()
    test_discard_hand()

    # Acquire tests
    test_acquire_card_from_imperium()
    test_acquire_without_enough_persuasion()
    test_acquire_reserve_prepare_the_way()

    # Trash tests
    test_trash_card_from_hand()
    test_trash_card_from_played()
    test_trash_card_from_discard()

    # Query tests
    test_get_deck_state()
    test_get_acquirable_cards()

    print("\n" + "="*70)
    print("✅ ALL DECK MANAGER TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
