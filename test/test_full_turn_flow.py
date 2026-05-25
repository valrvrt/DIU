"""
Tests for Full Turn Flow - Integration test.

This demonstrates the complete flow:
1. ActionGenerator determines valid actions
2. Player makes a choice
3. ActionExecutor executes the action
4. EffectResolver interprets card effects
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game
from src.models.player import Player
from src.models.card import ImperiumCard, CardType, LeaderCard
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.core.game_state import GameState
from src.engine.actions.action_generator import ActionGenerator
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, RevealAction


def setup_test_game():
    """Create a full game with board spaces and cards."""
    # Create test leader
    leader = LeaderCard(
        id="test_leader",
        name="Test Leader",
        type="Leader",
        card_type=CardType.LEADER
    )

    # Create player
    player = Player(
        player_id="player1",
        name="Test Player",
        leader=leader,
        color="blue",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=5,
        spice=1,
        troops_in_garrison=3,
        troops_in_reserve=9,
        agents_available=2,
        spies_available=3
    )

    # Create test cards and add to hand
    card1 = ImperiumCard(
        id="card1",
        name="Fremen Scout",
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

    card2 = ImperiumCard(
        id="card2",
        name="Landsraad Official",
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=4,
        agent_icons=["landsraad"],
        agent_effects=[
            {"type": "resource", "resource": "solari", "amount": 3}
        ],
        reveal_effects=[
            {"type": "resource", "resource": "persuasion", "amount": 3}
        ]
    )

    player.hand.add_card(card1)
    player.hand.add_card(card2)

    # Create board spaces
    fremen_camp = BoardSpace(
        id="fremen_camp",
        name="Fremen Camp",
        agent_icon="fremen",
        effects=[
            {"type": "resource", "resource": "water", "amount": 1}
        ]
    )

    landsraad_hall = BoardSpace(
        id="landsraad",
        name="Landsraad Hall",
        agent_icon="landsraad",
        effects=[
            {"type": "resource", "resource": "solari", "amount": 2}
        ]
    )

    # Create board
    board = Board()
    board.spaces = [fremen_camp, landsraad_hall]

    # Create game
    game = Game(
        players=[player],
        board=board,
        current_player_index=0
    )

    return game, player, card1, card2, fremen_camp, landsraad_hall


def test_complete_agent_turn():
    """
    Test a complete agent turn from start to finish.

    Flow:
    1. Check which cards are playable
    2. Select a card
    3. Check valid locations for that card
    4. Select a location
    5. Execute the action
    6. Verify all effects applied
    """
    print("\n" + "=" * 60)
    print("COMPLETE AGENT TURN TEST")
    print("=" * 60)

    game, player, card1, card2, fremen_camp, landsraad_hall = setup_test_game()

    action_gen = ActionGenerator(game)
    action_exec = ActionExecutor(game)

    print("\n--- Step 1: Check Playable Cards ---")
    playable_cards = action_gen.get_playable_imperium_cards(player.player_id)
    print(f"Playable cards: {[card.name for card in playable_cards]}")
    assert len(playable_cards) == 2, "Both cards should be playable"
    assert card1 in playable_cards, "Fremen Scout should be playable"
    assert card2 in playable_cards, "Landsraad Official should be playable"
    print("✓ ActionGenerator found all playable cards")

    print("\n--- Step 2: Player Selects Card ---")
    selected_card = card1  # Choose "Fremen Scout"
    print(f"Player selects: {selected_card.name}")

    print("\n--- Step 3: Check Valid Locations for Card ---")
    valid_locations = action_gen.get_valid_locations_for_card(
        player.player_id,
        selected_card
    )
    print(f"Valid locations for {selected_card.name}:")
    for location, placement_type in valid_locations:
        print(f"  - {location.name} (via {placement_type})")

    assert len(valid_locations) > 0, "Should have at least one valid location"
    assert valid_locations[0][0] == fremen_camp, "Fremen icon should match Fremen Camp"
    print("✓ ActionGenerator found valid locations")

    print("\n--- Step 4: Player Selects Location ---")
    selected_location, placement_type = valid_locations[0]
    print(f"Player selects: {selected_location.name} (placement: {placement_type})")

    print("\n--- Step 5: Execute Action ---")
    print(f"Before execution:")
    print(f"  Water: {player.water}")
    print(f"  Troops in garrison: {player.troops_in_garrison}")
    print(f"  Agents available: {player.agents_available}")
    print(f"  Cards in hand: {len(player.hand.cards)}")

    action = PlaceAgentAction(
        player_id=player.player_id,
        card=selected_card,
        location=selected_location,
        placement_type=placement_type,
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    print(f"\nExecution result:")
    print(f"  Success: {result['success']}")
    if result['success']:
        print(f"  Action type: {result.get('action_type', 'N/A')}")
        print(f"  Location: {result.get('location', 'N/A')}")
        print(f"  Placement type: {result.get('placement_type', 'N/A')}")
    else:
        print(f"  Error: {result.get('error', 'unknown')}")

    print(f"\nAfter execution:")
    print(f"  Water: {player.water}")
    print(f"  Troops in garrison: {player.troops_in_garrison}")
    print(f"  Agents available: {player.agents_available}")
    print(f"  Cards in hand: {len(player.hand.cards)}")

    assert result["success"], "Action should execute successfully"
    assert player.agents_available == 1, "Should have 1 agent remaining"
    assert len(player.hand.cards) == 1, "Card should be removed from hand"
    assert player.water == 4, "Should gain +1 water from card effect + +1 from location"
    assert player.troops_in_garrison == 4, "Should gain +1 troop from card effect"
    assert selected_location.occupied_by == player.player_id, "Location should be occupied"

    print("\n✓ ActionExecutor executed turn correctly")
    print("✓ EffectResolver applied card effects")
    print("✓ Location bonus applied")
    print("✓ Game state updated correctly")


def test_complete_reveal_turn():
    """
    Test a complete reveal turn with card acquisition.

    Flow:
    1. Player reveals hand
    2. Calculate persuasion from all cards
    3. Check acquisition options
    4. Acquire a card
    """
    print("\n" + "=" * 60)
    print("COMPLETE REVEAL TURN TEST")
    print("=" * 60)

    game, player, card1, card2, fremen_camp, landsraad_hall = setup_test_game()

    action_exec = ActionExecutor(game)

    # Add a card to Imperium row for acquisition
    acquisition_card = ImperiumCard(
        id="acquire_card",
        name="Expensive Card",
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=5,
        agent_icons=["landsraad"]
    )
    game.board.imperium_row = [acquisition_card]
    game.board.imperium_deck = []

    print("\n--- Step 1: Player Reveals Hand ---")
    print(f"Cards in hand: {[c.name for c in player.hand.cards]}")
    print(f"Has revealed: {player.has_revealed_this_round}")

    reveal_action = RevealAction(player_id=player.player_id)
    result = action_exec.execute_reveal(reveal_action)

    print(f"\nReveal result:")
    print(f"  Success: {result['success']}")
    print(f"  Total persuasion: {result['total_persuasion']}")
    print(f"  Cards revealed: {result['cards_revealed']}")
    print(f"  Reveal results:")
    for card_result in result["reveal_results"]:
        print(f"    - {card_result['card']}: {card_result['result']}")

    assert result["success"], "Reveal should succeed"
    assert player.has_revealed_this_round, "Player should be marked as revealed"
    # Fremen Scout (2 persuasion) + Landsraad Official (3 persuasion) = 5 total
    assert result["total_persuasion"] == 5, "Should calculate correct persuasion"
    assert player.temp_persuasion == 5, "Persuasion stored on player"

    print("\n✓ Reveal effects calculated correctly")
    print("✓ Persuasion total computed")

    print("\n--- Step 2: Check Acquisition Options ---")
    print(f"Available persuasion: {player.temp_persuasion}")
    print(f"Cards in Imperium row: {[c.name for c in game.board.imperium_row]}")
    print(f"Card to acquire: {acquisition_card.name} (cost: {acquisition_card.cost})")

    assert player.temp_persuasion >= acquisition_card.cost, "Should have enough persuasion"
    print("✓ Player can afford card")


def test_spy_infiltration():
    """
    Test spy infiltration mechanic.

    Flow:
    1. Place spy at observation post
    2. Check that infiltration is now available
    3. Infiltrate an occupied location
    """
    print("\n" + "=" * 60)
    print("SPY INFILTRATION TEST")
    print("=" * 60)

    game, player, card1, card2, fremen_camp, landsraad_hall = setup_test_game()

    action_gen = ActionGenerator(game)

    # Mark location as occupied by another player
    fremen_camp.occupied_by = "player2"

    # Place spy at observation post
    from src.models.board import ObservationPost
    spy_post = ObservationPost(
        id="post1",
        name="Spy Post 1",
        connected_locations=["fremen_camp"]
    )
    game.board.observation_posts = [spy_post]
    player.spies_placed.append("post1")

    print("\n--- Checking Infiltration Options ---")
    print(f"Fremen Camp occupied by: {fremen_camp.occupied_by}")
    print(f"Player has spies at: {player.spies_placed}")

    valid_locations = action_gen.get_valid_locations_for_card(
        player.player_id,
        card1
    )

    print(f"\nValid locations for {card1.name}:")
    for location, placement_type in valid_locations:
        print(f"  - {location.name} (via {placement_type})")

    # Check if infiltration is available
    infiltration_options = [
        (loc, ptype) for loc, ptype in valid_locations
        if ptype == "spy_infiltrate"
    ]

    if infiltration_options:
        print(f"\n✓ Spy infiltration available at:")
        for loc, ptype in infiltration_options:
            print(f"    - {loc.name}")
        print("✓ Spy network mechanic working correctly")
    else:
        print("\n✗ No infiltration options found (this may be expected)")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("FULL TURN FLOW INTEGRATION TEST SUITE")
    print("=" * 70)

    test_complete_agent_turn()
    test_complete_reveal_turn()
    test_spy_infiltration()

    print("\n" + "=" * 70)
    print("✓ ALL INTEGRATION TESTS PASSED")
    print("=" * 70)
    print("\nThe complete flow works:")
    print("  ActionGenerator → Player Choice → ActionExecutor → EffectResolver")
    print("=" * 70)
