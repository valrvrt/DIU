"""
Integration tests for DeckManager with PhaseManager.

Tests that deck operations work correctly within the game flow.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, ImperiumCard, CardType, ConflictCard
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.phase_manager import PhaseManager
from src.engine.managers.deck_manager import DeckManager
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, RevealAction


def create_test_card(card_id: str, name: str, cost: int = 3) -> ImperiumCard:
    """Helper to create test cards."""
    return ImperiumCard(
        id=card_id,
        name=name,
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=cost,
        agent_icons=["fremen"],
        agent_effects=[{"type": "resource", "resource": "water", "amount": 1}],
        reveal_effects=[{"type": "resource", "resource": "persuasion", "amount": 1}]
    )


def setup_test_game():
    """Create a game with deck and phase management."""
    # Create leaders
    leader1 = LeaderCard(id="leader1", name="Leader 1", type="Leader", card_type=CardType.LEADER)
    leader2 = LeaderCard(id="leader2", name="Leader 2", type="Leader", card_type=CardType.LEADER)

    # Create decks for players (10 cards each)
    deck1_cards = [create_test_card(f"p1_deck_{i}", f"P1 Card {i}") for i in range(10)]
    deck2_cards = [create_test_card(f"p2_deck_{i}", f"P2 Card {i}") for i in range(10)]

    # Create players
    player1 = Player(
        player_id="player1",
        name="Player 1",
        leader=leader1,
        color="blue",
        deck=Deck(cards=deck1_cards.copy()),
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
        deck=Deck(cards=deck2_cards.copy()),
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
            id="fremen_camp",
            name="Fremen Camp",
            agent_icon="fremen",
            effects=[{"type": "resource", "resource": "water", "amount": 1}]
        )
    ]

    # Add conflict
    conflict = ConflictCard(
        id="conflict1",
        name="Test Conflict",
        type="Conflict",
        card_type=CardType.CONFLICT,
        rewards=[{"victory_points": 1}]
    )
    board.conflict_deck = [conflict]

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


# ==================== INTEGRATION TESTS ====================

def test_begin_round_draws_cards():
    """Test that BEGIN_ROUND phase draws starting hand."""
    print("\n=== Test: BEGIN_ROUND Draws Cards ===")

    game, player1, player2 = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)

    # Set phase to RECALL (will advance to BEGIN_ROUND)
    game.current_phase = GamePhase.RECALL
    # Set round to 1 so that after increment (→2) card draw is triggered (draw skipped on round 1 setup)
    game.current_round = 1

    # Both players start with empty hands
    assert player1.hand.size == 0
    assert player2.hand.size == 0

    # Advance phase (RECALL → BEGIN_ROUND)
    result = phase_manager.advance_phase()

    # Both players should have 5 cards
    assert player1.hand.size == 5, f"Player 1 should have 5 cards, got {player1.hand.size}"
    assert player2.hand.size == 5, f"Player 2 should have 5 cards, got {player2.hand.size}"

    # Decks should have 5 cards remaining
    assert player1.deck.size == 5
    assert player2.deck.size == 5

    print("✓ BEGIN_ROUND draws starting hand")


def test_played_cards_discarded_after_player_turns():
    """Test that played cards are discarded when leaving PLAYER_TURNS phase."""
    print("\n=== Test: Played Cards Discarded After PLAYER_TURNS ===")

    game, player1, player2 = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)

    # Give players cards in hand
    deck_manager.draw_starting_hand("player1")
    deck_manager.draw_starting_hand("player2")

    # Simulate playing cards
    card1 = player1.hand.cards[0]
    card2 = player1.hand.cards[1]
    player1.played_cards_this_turn = [card1, card2]

    card3 = player2.hand.cards[0]
    player2.played_cards_this_turn = [card3]

    # Initially: 0 in discard
    assert player1.discard_pile.size == 0
    assert player2.discard_pile.size == 0

    # Set phase to PLAYER_TURNS
    game.current_phase = GamePhase.PLAYER_TURNS

    # Mark both as revealed
    player1.has_revealed_this_round = True
    player2.has_revealed_this_round = True

    # Advance phase (PLAYER_TURNS → COMBAT)
    result = phase_manager.advance_phase()

    # Played cards should be in discard
    assert player1.discard_pile.size == 2, f"Player 1 should have 2 in discard, got {player1.discard_pile.size}"
    assert player2.discard_pile.size == 1, f"Player 2 should have 1 in discard, got {player2.discard_pile.size}"

    # Played cards cleared
    assert len(player1.played_cards_this_turn) == 0
    assert len(player2.played_cards_this_turn) == 0

    print("✓ Played cards discarded after PLAYER_TURNS")


def test_hand_discarded_after_recall():
    """Test that remaining hand is discarded during RECALL phase."""
    print("\n=== Test: Hand Discarded After RECALL ===")

    game, player1, player2 = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)

    # Give players cards in hand
    deck_manager.draw_starting_hand("player1")
    deck_manager.draw_starting_hand("player2")

    # Players have 5 cards in hand
    assert player1.hand.size == 5
    assert player2.hand.size == 5

    # Set phase to RECALL, round to 1 so draw triggers after increment to 2
    game.current_phase = GamePhase.RECALL
    game.current_round = 1

    # Advance phase (RECALL → BEGIN_ROUND)
    result = phase_manager.advance_phase()

    # Old hands should be discarded
    assert player1.discard_pile.size == 5, f"Player 1 should have 5 in discard, got {player1.discard_pile.size}"
    assert player2.discard_pile.size == 5, f"Player 2 should have 5 in discard, got {player2.discard_pile.size}"

    # New hands should be drawn (5 cards)
    assert player1.hand.size == 5, f"Player 1 should have new 5 cards, got {player1.hand.size}"
    assert player2.hand.size == 5, f"Player 2 should have new 5 cards, got {player2.hand.size}"

    print("✓ Hand discarded after RECALL")


def test_complete_round_with_deck_management():
    """Test complete round flow with deck operations."""
    print("\n=== Test: Complete Round with Deck Management ===")

    game, player1, player2 = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)
    action_exec = ActionExecutor(game, phase_manager)

    # Start from RECALL, round=1 so draw triggers (round becomes 2, satisfying >1)
    game.current_phase = GamePhase.RECALL
    game.current_round = 1

    # Advance to BEGIN_ROUND (draws starting hands)
    phase_manager.advance_phase()

    assert game.current_phase == GamePhase.BEGIN_ROUND
    assert game.current_round == 2
    assert player1.hand.size == 5
    assert player2.hand.size == 5

    # Advance to PLAYER_TURNS
    phase_manager.advance_phase()
    assert game.current_phase == GamePhase.PLAYER_TURNS

    # Player 1 places agent (plays a card)
    card_to_play = player1.hand.cards[0]
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

    # Card should be in played_cards_this_turn
    assert len(player1.played_cards_this_turn) == 1
    assert player1.played_cards_this_turn[0] == card_to_play

    # Player 1 reveals
    reveal_action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(reveal_action)
    assert result["success"] == True

    # Remaining hand cards should also be tracked
    # (reveal adds them to played_cards_this_turn)
    assert len(player1.played_cards_this_turn) == 5  # 1 played + 4 revealed

    # Player 2 reveals (skips agent placement)
    reveal_action = RevealAction(player_id="player2")
    result = action_exec.execute_reveal(reveal_action)
    assert result["success"] == True

    # Both revealed, advance to COMBAT
    assert phase_manager.should_advance_phase() == True
    phase_manager.advance_phase()
    assert game.current_phase == GamePhase.COMBAT

    # Played cards should be discarded
    assert player1.discard_pile.size == 5
    assert player2.discard_pile.size == 5
    assert len(player1.played_cards_this_turn) == 0
    assert len(player2.played_cards_this_turn) == 0

    print("✓ Complete round with deck management works")


def test_draw_with_shuffle_during_gameplay():
    """Test that shuffle works correctly during multi-round gameplay."""
    print("\n=== Test: Draw with Shuffle During Gameplay ===")

    game, player1, player2 = setup_test_game()

    # Create managers
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)

    # Simulate first round: draw 5, discard 5
    deck_manager.draw_starting_hand("player1")
    assert player1.hand.size == 5
    assert player1.deck.size == 5

    deck_manager.discard_hand("player1")
    assert player1.hand.size == 0
    assert player1.discard_pile.size == 5

    # Simulate second round: draw 5 (should draw from deck)
    deck_manager.draw_starting_hand("player1")
    assert player1.hand.size == 5
    assert player1.deck.size == 0
    assert player1.discard_pile.size == 5

    deck_manager.discard_hand("player1")
    assert player1.discard_pile.size == 10

    # Simulate third round: draw 5 (should shuffle discard into deck)
    deck_manager.draw_starting_hand("player1")
    assert player1.hand.size == 5
    # Discard should be shuffled into deck
    # 10 cards in discard → 5 drawn → 5 in deck, 0 in discard
    assert player1.deck.size == 5
    assert player1.discard_pile.size == 0

    print("✓ Draw with shuffle during gameplay works")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all integration tests."""
    print("\n" + "="*70)
    print("DECK INTEGRATION TESTS")
    print("="*70)

    test_begin_round_draws_cards()
    test_played_cards_discarded_after_player_turns()
    test_hand_discarded_after_recall()
    test_complete_round_with_deck_management()
    test_draw_with_shuffle_during_gameplay()

    print("\n" + "="*70)
    print("✅ ALL DECK INTEGRATION TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
