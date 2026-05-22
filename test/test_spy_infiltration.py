"""
Test spy infiltration mechanic.

Spy infiltration rules:
- Can place a spy on an already occupied location
- Original agent stays (occupied_by doesn't change)
- BOTH players get the location effects
- Spy is tracked via infiltrated_by field
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction
from src.models.player import Player
from src.models.card import ImperiumCard, CardType
from src.models.deck import Deck
from src.models.boardspace import BoardSpace
from src.models.game import Game
from src.models.board import Board
from src.engine.core.game_state import GameState
from src.engine.effects.effect_resolver import EffectResolver


def create_test_card(card_id, name, agent_effects=None):
    """Create a test imperium card."""
    return ImperiumCard(
        name=name,
        type="imperium",
        card_type=CardType.IMPERIUM,
        id=str(card_id),
        cost=0,
        factions=[],
        starting_hand=False,
        agent_effects=agent_effects or []
    )


def test_spy_infiltration():
    """Test that spy infiltration works correctly."""
    print("\n" + "="*80)
    print("TEST: Spy Infiltration Mechanic")
    print("="*80)

    # Create game
    game = Game()
    game.board = Board()

    # Create a board space with effects
    space = BoardSpace(
        id="test_space",
        name="Test Location",
        agent_icon="any",
        effects=[
            {"type": "resource", "resource": "solari", "amount": 2},
            {"type": "resource", "resource": "spice", "amount": 1}
        ]
    )
    game.board.spaces = [space]

    # Create mock leader
    mock_leader = type('Leader', (), {'name': 'Test Leader'})()

    # Create Player 1 (will occupy the space first)
    player1 = Player(
        player_id="player1",
        name="Player One",
        color="blue",
        leader=mock_leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )
    player1.solari = 0
    player1.spice = 0
    player1.agents_available = 2
    player1.spies_available = 2

    # Create Player 2 (will infiltrate with spy)
    player2 = Player(
        player_id="player2",
        name="Player Two",
        color="red",
        leader=mock_leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )
    player2.solari = 0
    player2.spice = 0
    player2.agents_available = 2
    player2.spies_available = 2

    game.players = [player1, player2]
    state = GameState(game)

    # Create action executor
    executor = ActionExecutor(game)

    # Create cards for both players
    card1 = create_test_card(1, "Player 1 Card")
    card2 = create_test_card(2, "Player 2 Card")

    player1.hand.cards.append(card1)
    player2.hand.cards.append(card2)

    print("\n1. Player 1 places agent on location (normal placement)")
    print(f"   Before: Player 1 has {player1.solari} solari, {player1.spice} spice")

    # Player 1 places agent normally
    action1 = PlaceAgentAction(
        player_id="player1",
        card=card1,
        location=space,
        placement_type="any"  # Normal placement
    )

    result1 = executor.execute_place_agent(action1)

    if not result1["success"]:
        print(f"   ✗ FAILED: {result1.get('error')}")
        return False

    print(f"   After: Player 1 has {player1.solari} solari, {player1.spice} spice")
    print(f"   Location occupied_by: {space.occupied_by}")
    print(f"   Location infiltrated_by: {space.infiltrated_by}")

    # Verify Player 1 got the effects
    assert player1.solari == 2, f"Player 1 should have 2 solari, has {player1.solari}"
    assert player1.spice == 1, f"Player 1 should have 1 spice, has {player1.spice}"
    assert space.occupied_by == "player1", "Location should be occupied by player1"
    assert space.infiltrated_by is None, "Location should not be infiltrated yet"
    print("   ✓ Player 1 successfully occupied location and received effects")

    print("\n2. Player 2 infiltrates with spy")
    print(f"   Before: Player 2 has {player2.solari} solari, {player2.spice} spice")
    print(f"   Player 2 spies available: {player2.spies_available}")

    # Player 2 infiltrates with spy
    action2 = PlaceAgentAction(
        player_id="player2",
        card=card2,
        location=space,
        placement_type="spy_infiltrate"  # Spy infiltration
    )

    result2 = executor.execute_place_agent(action2)

    if not result2["success"]:
        print(f"   ✗ FAILED: {result2.get('error')}")
        return False

    print(f"   After: Player 2 has {player2.solari} solari, {player2.spice} spice")
    print(f"   Location occupied_by: {space.occupied_by}")
    print(f"   Location infiltrated_by: {space.infiltrated_by}")
    print(f"   Player 2 spies available: {player2.spies_available}")

    # Verify spy infiltration worked correctly
    print("\n3. Verifying spy infiltration rules...")

    # Rule 1: Original occupant stays
    if space.occupied_by == "player1":
        print("   ✓ Original occupant (player1) still owns the location")
    else:
        print(f"   ✗ FAILED: occupied_by should be player1, is {space.occupied_by}")
        return False

    # Rule 2: Spy is tracked
    if space.infiltrated_by == "player2":
        print("   ✓ Spy infiltration tracked (infiltrated_by = player2)")
    else:
        print(f"   ✗ FAILED: infiltrated_by should be player2, is {space.infiltrated_by}")
        return False

    # Rule 3: Spy was used (not agent)
    if player2.spies_available == 1:
        print("   ✓ Spy was consumed (spies_available went from 2 to 1)")
    else:
        print(f"   ✗ FAILED: spies_available should be 1, is {player2.spies_available}")
        return False

    # Rule 4: BOTH players got effects
    # Player 1 got effects when they placed (2 solari, 1 spice)
    # Then Player 1 should get effects AGAIN when spy infiltrated (total: 4 solari, 2 spice)
    if player1.solari == 4 and player1.spice == 2:
        print(f"   ✓ Player 1 (original) got effects twice: {player1.solari} solari, {player1.spice} spice")
    else:
        print(f"   ✗ Player 1 should have 4 solari and 2 spice (got effects twice), has {player1.solari} solari and {player1.spice} spice")
        # This might not be implemented yet - let's check
        if player1.solari == 2 and player1.spice == 1:
            print(f"   ⚠ WARNING: Player 1 only got effects once (original placement)")
            print(f"   ⚠ Spy infiltration may not be giving effects to original occupant")
        return False

    if player2.solari == 2 and player2.spice == 1:
        print(f"   ✓ Player 2 (spy) has effects: {player2.solari} solari, {player2.spice} spice")
    else:
        print(f"   ✗ FAILED: Player 2 should have 2 solari and 1 spice, has {player2.solari} solari and {player2.spice} spice")
        return False

    # Rule 5: Check result includes infiltration info
    if result2.get("spy_infiltration"):
        print("   ✓ Result indicates spy infiltration occurred")
    else:
        print("   ✗ FAILED: Result should indicate spy infiltration")
        return False

    if result2.get("original_occupant_effects"):
        print("   ✓ Original occupant effects were resolved")
    else:
        print("   ✗ FAILED: Original occupant effects should be in result")
        return False

    print("\n" + "="*80)
    print("✓ ALL SPY INFILTRATION TESTS PASSED!")
    print("="*80)
    return True


def test_cannot_infiltrate_unoccupied():
    """Test that you cannot infiltrate an unoccupied location."""
    print("\n" + "="*80)
    print("TEST: Cannot Infiltrate Unoccupied Location")
    print("="*80)

    # Create game
    game = Game()
    game.board = Board()

    # Create unoccupied space
    space = BoardSpace(
        id="test_space",
        name="Unoccupied Location",
        agent_icon="any",
        effects=[]
    )
    game.board.spaces = [space]

    # Create mock leader
    mock_leader = type('Leader', (), {'name': 'Test Leader'})()

    # Create player
    player = Player(
        player_id="player1",
        name="Test Player",
        color="blue",
        leader=mock_leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )
    player.spies_available = 2

    game.players = [player]

    # Create action executor
    executor = ActionExecutor(game)

    # Create card
    card = create_test_card(1, "Test Card")
    player.hand.cards.append(card)

    print("\n Attempting to infiltrate unoccupied location...")

    # Try to infiltrate unoccupied location (should fail)
    action = PlaceAgentAction(
        player_id="player1",
        card=card,
        location=space,
        placement_type="spy_infiltrate"
    )

    result = executor.execute_place_agent(action)

    if result["success"]:
        print("   ✗ FAILED: Should not be able to infiltrate unoccupied location")
        return False

    if "unoccupied" in result.get("error", "").lower():
        print(f"   ✓ Correctly rejected: {result['error']}")
        print("\n✓ TEST PASSED: Cannot infiltrate unoccupied location")
        return True
    else:
        print(f"   ✗ FAILED: Wrong error message: {result.get('error')}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SPY INFILTRATION TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    if test_spy_infiltration():
        passed += 1
    else:
        failed += 1

    if test_cannot_infiltrate_unoccupied():
        passed += 1
    else:
        failed += 1

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")

    if failed == 0:
        print("\n✓ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        sys.exit(1)
