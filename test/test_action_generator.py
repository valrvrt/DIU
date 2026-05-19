#!/usr/bin/env python3
"""
Test script for ActionGenerator - demonstrates the "available actions first" pattern.

This shows how the game determines what a player can do at any moment.
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.board import Board
from src.models.deck import Deck
from src.engine.action_generator import ActionGenerator
from src.loaders.card_loader import load_starter_deck, load_leaders
from src.loaders.board_loader import load_board_spaces, load_observation_posts


def create_test_game():
    """Create a minimal game for testing"""
    print("🎮 Creating test game...")

    # Create players
    leaders = load_leaders()
    paul = leaders[0]  # Paul Atreides

    starter_cards = load_starter_deck()

    player1 = Player(
        player_id="player1",
        name="Alice",
        leader=paul,
        color="blue",
        deck=Deck(cards=[], seed=42),
        hand=Deck(cards=starter_cards[:5], seed=42),  # First 5 cards in hand
        discard_pile=Deck(cards=[], seed=42),
        water=1,
        solari=0,
        spice=0,
        victory_points=0,
        troops_in_reserve=9,
        troops_in_garrison=3,
        troops_in_conflict=0,
        agents_available=2,
        spies_available=3
    )

    # Create board
    board = Board(
        spaces=load_board_spaces(),
        observation_posts=load_observation_posts(),
        conflict_deck=[],
        current_conflict=None,
        imperium_deck=[],
        imperium_row=[],
        imperium_discard=[],
        reserve_prepare_the_way=[],
        reserve_spice_must_flow=[],
        intrigue_deck=[],
        intrigue_discard=[],
        contract_deck=[],
        contract_row=[],
        shield_active=True
    )

    # Create game
    game = Game(
        players=[player1],
        current_player_index=0,
        first_player_index=0,
        board=board,
        current_phase=GamePhase.PLAYER_TURNS,
        current_round=1,
        player_count=1,
        use_choam_module=False,
        seed=42
    )

    print(f"✓ Game created with {len(game.players)} player(s)")
    print(f"✓ Board has {len(board.spaces)} spaces")
    print(f"✓ Player has {len(player1.hand.cards)} cards in hand")
    print()

    return game


def test_playable_cards():
    """Test: Which cards can be played?"""
    print("=" * 70)
    print("TEST 1: Which cards in hand can be played?")
    print("=" * 70)

    game = create_test_game()
    generator = ActionGenerator(game)
    player = game.players[0]

    print(f"Player '{player.name}' hand:")
    for i, card in enumerate(player.hand.cards, 1):
        icons = ", ".join(card.agent_icons) if card.agent_icons else "None"
        print(f"  {i}. {card.name}")
        print(f"     Agent Icons: [{icons}]")

    print(f"\nPlayer has {player.agents_available} agents available")
    print()

    # Get playable cards
    playable = generator.get_playable_imperium_cards("player1")

    print(f"🎴 PLAYABLE CARDS: {len(playable)}/{len(player.hand.cards)}")
    for card in playable:
        print(f"  ✅ {card.name}")

    # Show unplayable cards
    unplayable = [c for c in player.hand.cards if c not in playable]
    if unplayable:
        print(f"\n❌ UNPLAYABLE CARDS: {len(unplayable)}")
        for card in unplayable:
            print(f"  ❌ {card.name} - No valid locations")

    print()


def test_valid_locations_for_card():
    """Test: Where can a specific card be played?"""
    print("=" * 70)
    print("TEST 2: Valid locations for a specific card")
    print("=" * 70)

    game = create_test_game()
    generator = ActionGenerator(game)
    player = game.players[0]

    # Pick first playable card
    playable = generator.get_playable_imperium_cards("player1")
    if not playable:
        print("⚠️ No playable cards!")
        return

    card = playable[0]
    print(f"Selected card: {card.name}")
    print(f"Agent icons: {card.agent_icons}")
    print()

    # Get valid locations
    valid_locations = generator.get_valid_locations_for_card("player1", card)

    print(f"📍 VALID LOCATIONS: {len(valid_locations)}")
    for location, placement_type in valid_locations:
        cost_str = ""
        if location.cost:
            cost_items = [f"{v} {k}" for k, v in location.cost.items()]
            cost_str = f" (Costs: {', '.join(cost_items)})"

        requirement_str = ""
        if location.required_influence:
            for faction, amount in location.required_influence.items():
                requirement_str = f" (Requires: {amount} {faction} influence)"

        print(f"  ✅ {location.name} [{placement_type}]{cost_str}{requirement_str}")
        print(f"     Effects: {location.effects}")

    print()


def test_troop_deployment():
    """Test: Troop deployment options"""
    print("=" * 70)
    print("TEST 3: Troop Deployment Options")
    print("=" * 70)

    game = create_test_game()
    generator = ActionGenerator(game)
    player = game.players[0]

    print(f"Player troop status:")
    print(f"  - In Reserve: {player.troops_in_reserve}")
    print(f"  - In Garrison: {player.troops_in_garrison}")
    print(f"  - In Conflict: {player.troops_in_conflict}")
    print()

    options = generator.get_troop_deployment_options("player1")

    print(f"🎖️ DEPLOYMENT OPTIONS:")
    print(f"  - Can deploy from garrison: {options['max_from_garrison']} troops (max 2)")
    print(f"  - Total available in garrison: {options['total_available']}")
    print()


def test_can_take_turns():
    """Test: What kind of turns can player take?"""
    print("=" * 70)
    print("TEST 4: Available Turn Types")
    print("=" * 70)

    game = create_test_game()
    generator = ActionGenerator(game)
    player = game.players[0]

    can_agent = generator.can_take_agent_turn("player1")
    can_reveal = generator.can_take_reveal_turn("player1")

    print(f"Turn options for '{player.name}':")
    print(f"  ✅ Can take Agent Turn: {can_agent}")
    print(f"  ✅ Can take Reveal Turn: {can_reveal}")
    print()

    if can_agent:
        print("Agent Turn Requirements Met:")
        print(f"  ✓ Has agents available: {player.agents_available}")
        print(f"  ✓ Hasn't revealed yet: {not player.has_revealed_this_round}")
        playable = generator.get_playable_imperium_cards("player1")
        print(f"  ✓ Has playable cards: {len(playable)}")

    print()


def test_spy_system():
    """Test: Spy network and infiltration"""
    print("=" * 70)
    print("TEST 5: Spy System")
    print("=" * 70)

    game = create_test_game()
    generator = ActionGenerator(game)
    player = game.players[0]

    # Place a spy at a post
    print(f"Player has {player.spies_available} spies available")

    available_posts = generator.get_available_observation_posts("player1")
    print(f"\n📡 AVAILABLE OBSERVATION POSTS: {len(available_posts)}")
    for post in available_posts:
        print(f"  ✅ {post.name}")
        print(f"     Connects to: {len(post.connected_locations)} locations")

    # Simulate placing a spy
    if available_posts:
        post = available_posts[0]
        player.spies_placed.append(post.id)
        player.spies_available -= 1

        print(f"\n🕵️ Placed spy at: {post.name}")
        print(f"Spy now watching {len(post.connected_locations)} locations")

        # Show spy accessible locations
        from src.engine.game_state import GameState
        state = GameState(game)
        accessible = state.get_spy_accessible_locations("player1")
        print(f"\n🎯 SPY ACCESSIBLE LOCATIONS: {len(accessible)}")
        for loc in accessible:
            print(f"  👁️ {loc.name}")

    print()


def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "ACTION GENERATOR TEST SUITE" + " " * 25 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        test_playable_cards()
        test_valid_locations_for_card()
        test_troop_deployment()
        test_can_take_turns()
        test_spy_system()

        print("=" * 70)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 70)
        print()
        print("🎯 KEY TAKEAWAYS:")
        print("  - ActionGenerator determines what player CAN do")
        print("  - UI only shows valid options (no invalid actions)")
        print("  - Two-step selection: card first, then location")
        print("  - Spy system enables special placements")
        print()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
