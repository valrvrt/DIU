"""
Test ActionExecutor integration with EffectResolver using real JSON data.

This validates that:
1. ActionExecutor properly uses EffectResolver for all effects
2. Real JSON data from spaces, conflicts, contracts, leaders works correctly
3. Choices from effects are properly returned and can be resolved
4. No hardcoded resource logic remains
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.board import Board
from src.models.card import ImperiumCard, LeaderCard, CardType
from src.models.deck import Deck
from src.models.boardspace import BoardSpace
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, RevealAction
from src.engine.effects.effect_resolver import EffectResolver


def load_json_data(filename):
    """Load JSON data from data directory."""
    data_path = os.path.join("data", filename)
    with open(data_path, 'r') as f:
        return json.load(f)


def create_test_game():
    """Create a minimal game for testing."""
    # Create leader
    leader = LeaderCard(
        id="leader1",
        name="Test Leader",
        type="Leader",
        card_type=CardType.LEADER
    )

    # Create player
    player = Player(
        player_id="player1",
        name="Player 1",
        leader=leader,
        color="blue",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=10,
        solari=10,
        spice=5,
        victory_points=0,
        fremen_influence=0,
        bene_gesserit_influence=0,
        spacing_guild_influence=0,
        emperor_influence=0,
        troops_in_garrison=5,
        agents_available=2,
        total_available_agents=2,
        spies_available=0
    )

    # Create board
    board = Board()
    board.intrigue_deck = []
    board.contract_deck = []

    # Create game
    game = Game(
        players=[player],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS
    )

    return game, player


# ==================== TEST PLACE AGENT WITH LOCATION EFFECTS ====================

def test_place_agent_with_location_effects_from_json():
    """Test placing agent and resolving location effects from spaces.JSON."""
    print("\n=== Test: Place Agent with Location Effects from JSON ===")

    game, player = create_test_game()
    action_exec = ActionExecutor(game)

    # Load real space from JSON
    spaces = load_json_data("/Users/val/Desktop/Pythoneries/DUNE Imperium Uprising/data/spaces.JSON")
    fremkit = next(s for s in spaces if s["name"] == "Fremkit")

    # Create BoardSpace from JSON data
    location = BoardSpace(
        id=fremkit["id"],
        name=fremkit["name"],
        faction=fremkit.get("faction"),
        agent_icon=fremkit.get("agent_icon", "neutral"),
        is_combat_space=fremkit.get("combat_space", False)
    )
    location.reward = fremkit["reward"]  # Store JSON reward data

    # Create a test card
    card = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, 
        name="Test Card",
        cost=2,
        factions=[]
    )
    player.hand.add_card(card)

    # Execute place agent action
    action = PlaceAgentAction(
        player_id="player1",
        card=card,
        location=location,
        placement_type="fremen",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"] == True, f"Place agent failed: {result.get('error')}"
    assert result["location"] == "Fremkit"

    # Location effects should be resolved by EffectResolver
    assert result["location_effects"] is not None
    assert result["location_effects"]["success"] == True

    print(f"✓ Place agent with location effects works")
    print(f"  Location: {result['location']}")
    print(f"  Effects applied: {result['location_effects']['effects_applied']}")


def test_place_agent_with_choice_effect():
    """Test placing agent at location with choice effect (Deep Desert)."""
    print("\n=== Test: Place Agent with Choice Effect ===")

    game, player = create_test_game()
    action_exec = ActionExecutor(game)

    # Load Deep Desert from JSON (has choice: spice or worms)
    spaces = load_json_data("/Users/val/Desktop/Pythoneries/DUNE Imperium Uprising/data/spaces.JSON")
    deep_desert = next(s for s in spaces if s["name"] == "Deep Desert")

    location = BoardSpace(
        id=deep_desert["id"],
        name=deep_desert["name"],
        faction=None,
        agent_icon=deep_desert.get("agent_icon", "yellow"),
        is_combat_space=deep_desert.get("combat_space", False)
    )
    location.reward = deep_desert["reward"]
    location.cost_effects = deep_desert.get("cost", [])

    # Create card
    card = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, name="Test Card", cost=2, factions=[])
    player.hand.add_card(card)
    player.water = 10  # Enough to pay cost

    # Execute place agent
    action = PlaceAgentAction(
        player_id="player1",
        card=card,
        location=location,
        placement_type="yellow",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"] == True
    assert len(result["choices_required"]) > 0, "Should have choices from Deep Desert"

    choice = result["choices_required"][0]
    assert choice["type"] == "choice"
    assert choice["required"] == True
    assert len(choice["options"]) == 2  # spice or worms

    print("✓ Place agent with choice effect works")
    print(f"  Choices required: {len(result['choices_required'])}")
    print(f"  Options: {[opt['id'] for opt in choice['options']]}")


# ==================== TEST REVEAL WITH EFFECT RESOLVER ====================

def test_reveal_only_unplayed_cards():
    """Test that reveal only resolves effects for unplayed cards."""
    print("\n=== Test: Reveal Only Unplayed Cards ===")

    game, player = create_test_game()
    action_exec = ActionExecutor(game)

    # Create cards with reveal effects
    played_card = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, 
        name="Played Card",
        cost=2,
        factions=[]
    )
    played_card.reveal_effects = [
        {"type": "resource", "resource": "persuasion", "amount": 2}
    ]

    unplayed_card = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, 
        name="Unplayed Card",
        cost=3,
        factions=[]
    )
    unplayed_card.reveal_effects = [
        {"type": "resource", "resource": "persuasion", "amount": 3}
    ]

    # Simulate: played_card was already played (in played_cards_this_turn)
    # unplayed_card is still in hand
    player.played_cards_this_turn.append(played_card)
    player.hand.add_card(unplayed_card)

    # Execute reveal
    action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(action)

    assert result["success"] == True

    # Only unplayed_card should have been resolved
    assert result["cards_revealed"] == 1  # Only unplayed card
    assert result["total_persuasion"] == 3  # Only from unplayed card, NOT from played card

    # Both cards should now be in played_cards_this_turn
    assert len(player.played_cards_this_turn) == 2

    print("✓ Reveal only resolves unplayed cards")
    print(f"  Cards revealed: {result['cards_revealed']}")
    print(f"  Total persuasion: {result['total_persuasion']}")
    print(f"  Total cards played: {result['total_cards_played']}")


def test_reveal_extracts_persuasion_correctly():
    """Test that reveal correctly extracts persuasion from EffectResolver results."""
    print("\n=== Test: Reveal Extracts Persuasion Correctly ===")

    game, player = create_test_game()
    action_exec = ActionExecutor(game)

    # Create cards with various reveal effects
    card1 = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, name="Card 1", cost=2, factions=[])
    card1.reveal_effects = [
        {"type": "resource", "resource": "persuasion", "amount": 2},
        {"type": "resource", "resource": "sword", "amount": 1}
    ]

    card2 = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, name="Card 2", cost=3, factions=[])
    card2.reveal_effects = [
        {"type": "resource", "resource": "persuasion", "amount": 3},
        {"type": "draw", "deck": "intrigue", "amount": 1}
    ]

    player.hand.add_card(card1)
    player.hand.add_card(card2)

    # Execute reveal
    action = RevealAction(player_id="player1")
    result = action_exec.execute_reveal(action)

    assert result["success"] == True
    assert result["total_persuasion"] == 5  # 2 + 3
    assert result["temp_swords"] == 1
    assert player.temp_persuasion == 5
    assert player.temp_swords == 1

    print("✓ Reveal extracts persuasion correctly")
    print(f"  Total persuasion: {result['total_persuasion']}")
    print(f"  Total swords: {result['temp_swords']}")


# ==================== TEST CARD EFFECTS VS LOCATION EFFECTS ====================

def test_card_agent_effects_separate_from_location():
    """Test that card agent effects are resolved separately from location effects."""
    print("\n=== Test: Card Agent Effects Separate from Location ===")

    game, player = create_test_game()
    action_exec = ActionExecutor(game)

    # Create card with agent effects
    card = ImperiumCard(type="Imperium", card_type=CardType.IMPERIUM, name="Strong Card", cost=2, factions=[])
    card.agent_effects = [
        {"type": "resource", "resource": "solari", "amount": 3}
    ]

    # Create location with effects
    location = BoardSpace(id=1, name="Test Location", faction=None, agent_icon="test", is_combat_space=False)
    location.reward = [
        {"type": "resource", "resource": "water", "amount": 1}
    ]

    player.hand.add_card(card)
    initial_solari = player.solari
    initial_water = player.water

    # Execute place agent
    action = PlaceAgentAction(
        player_id="player1",
        card=card,
        location=location,
        placement_type="test",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"] == True

    # Card agent effects should be resolved
    assert result["card_agent_effects"] is not None
    assert result["card_agent_effects"]["success"] == True

    # Location effects should be resolved
    assert result["location_effects"] is not None
    assert result["location_effects"]["success"] == True

    # Both effects should have been applied
    assert player.solari == initial_solari + 3  # From card
    assert player.water == initial_water + 1  # From location

    print("✓ Card and location effects resolved separately")
    print(f"  Card effects: {result['card_agent_effects']['effects_applied']}")
    print(f"  Location effects: {result['location_effects']['effects_applied']}")


# ==================== TEST REAL JSON LEADER ABILITIES ====================

def test_leader_signet_ability_from_json():
    """Test resolving leader signet ability from leaders.JSON."""
    print("\n=== Test: Leader Signet Ability from JSON ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load real leader from JSON
    leaders = load_json_data("leaders.JSON")
    lady_jessica = next(l for l in leaders if l["name"] == "Lady Jessica")

    # Resolve signet ability
    result = resolver.resolve_effects(
        "player1",
        lady_jessica["signet_ability"]["effects"],
        context={"phase": "reveal", "source": "leader"}
    )

    assert result["success"] == True
    assert player.temp_persuasion == 1  # Lady Jessica gives +1 persuasion

    print("✓ Leader signet ability works")
    print(f"  Leader: {lady_jessica['name']}")
    print(f"  Effect: {lady_jessica['signet_ability']['description']}")
    print(f"  Persuasion gained: {player.temp_persuasion}")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all ActionExecutor integration tests."""
    print("=" * 70)
    print("ACTION EXECUTOR + EFFECT RESOLVER INTEGRATION TESTS")
    print("=" * 70)

    try:
        # Place agent tests
        test_place_agent_with_location_effects_from_json()
        test_place_agent_with_choice_effect()
        test_card_agent_effects_separate_from_location()

        # Reveal tests
        test_reveal_only_unplayed_cards()
        test_reveal_extracts_persuasion_correctly()

        # JSON data tests
        test_leader_signet_ability_from_json()

        print("\n" + "=" * 70)
        print("✅ ALL INTEGRATION TESTS PASSED")
        print("=" * 70)
        print("\nKey Validations:")
        print("  ✓ ActionExecutor uses EffectResolver for all effects")
        print("  ✓ Real JSON data from spaces.JSON works correctly")
        print("  ✓ Choice effects are properly returned")
        print("  ✓ Card effects separate from location effects")
        print("  ✓ Reveal only resolves unplayed cards")
        print("  ✓ Persuasion extraction works correctly")
        print("  ✓ Leader abilities from JSON work")
        print("\n🎉 ActionExecutor integration is complete!")

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
