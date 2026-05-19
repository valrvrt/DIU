"""
Unit tests for EffectResolver.

Tests the universal effect resolution system using real JSON data from:
- conflicts.JSON
- spaces.JSON
- contracts.JSON
- leaders.JSON
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import LeaderCard, CardType
from src.models.deck import Deck
from src.models.board import Board
from src.engine.effect_resolver import EffectResolver
from src.engine.game_state import GameState


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
        water=5,
        solari=10,
        spice=3,
        victory_points=0,
        fremen_influence=1,
        bene_gesserit_influence=0,
        spacing_guild_influence=0,
        emperor_influence=0,
        troops_in_garrison=5,
        agents_available=2,
        total_available_agents=2,
        spies_available=3
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


def load_json_data(filename):
    """Load JSON data from data directory."""
    data_path = Path(__file__).parent.parent / "data" / filename
    with open(data_path, 'r') as f:
        return json.load(f)


# ==================== SIMPLE RESOURCE TESTS ====================

def test_resource_solari():
    """Test basic solari resource effect."""
    print("\n=== Test: Resource - Solari ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_solari = player.solari

    # Test effect from conflicts.JSON - Skirmish (Desert Mouse) - 1st place
    effects = [
        {"type": "resource", "resource": "solari", "amount": 2}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.solari == initial_solari + 2
    assert len(result["effects_applied"]) == 1
    assert result["effects_applied"][0]["resource"] == "solari"
    assert result["effects_applied"][0]["amount"] == 2

    print("✓ Solari resource effect works")


def test_resource_spice():
    """Test spice resource effect."""
    print("\n=== Test: Resource - Spice ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_spice = player.spice

    # Test effect from conflicts.JSON - Skirmish (Crysknife) - 3rd place
    effects = [
        {"type": "resource", "resource": "spice", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.spice == initial_spice + 1

    print("✓ Spice resource effect works")


def test_resource_water():
    """Test water resource effect."""
    print("\n=== Test: Resource - Water ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_water = player.water

    # Test effect from contracts.JSON - Contract ID 2
    effects = [
        {"type": "resource", "resource": "water", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.water == initial_water + 1

    print("✓ Water resource effect works")


def test_resource_troop():
    """Test troop resource effect."""
    print("\n=== Test: Resource - Troop ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_troops = player.troops_in_garrison

    # Test effect from contracts.JSON - Contract ID 3
    effects = [
        {"type": "resource", "resource": "troop", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.troops_in_garrison == initial_troops + 1

    print("✓ Troop resource effect works")


def test_resource_victory_point():
    """Test victory point resource effect."""
    print("\n=== Test: Resource - Victory Point ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_vp = player.victory_points

    # Test effect from conflicts.JSON - Battle for Spice Refinery - 1st place
    effects = [
        {"type": "resource", "resource": "victory_point", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.victory_points == initial_vp + 1

    print("✓ Victory point resource effect works")


# ==================== INFLUENCE TESTS ====================

def test_influence_specific_faction():
    """Test influence gain with specific faction."""
    print("\n=== Test: Influence - Specific Faction ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    initial_influence = player.fremen_influence

    # Test effect from conflicts.JSON - Skirmish (Crysknife) - 1st place
    effects = [
        {"type": "influence", "target": "fremen", "amount": 1, "times": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.fremen_influence == initial_influence + 1
    assert len(result["effects_applied"]) == 1

    print("✓ Specific faction influence works")


def test_influence_with_multiplier():
    """Test influence with 'times' multiplier."""
    print("\n=== Test: Influence - With Multiplier ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Test effect from conflicts.JSON - Propaganda - 1st place
    effects = [
        {"type": "influence", "target": "any", "amount": 1, "times": 2}
    ]

    result = resolver.resolve_effects("player1", effects)

    # Should require choice because target is "any"
    assert result["success"] == True
    assert len(result["choices_required"]) == 1
    assert result["choices_required"][0]["type"] == "choose_influence_faction"
    assert result["choices_required"][0]["amount"] == 2  # 1 * 2

    print("✓ Influence with multiplier requires choice")


def test_influence_any_requires_choice():
    """Test that 'any' influence target requires player choice."""
    print("\n=== Test: Influence - 'Any' Requires Choice ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Test effect with "any" target
    effects = [
        {"type": "influence", "target": "any", "amount": 1, "times": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert len(result["choices_required"]) == 1
    choice = result["choices_required"][0]
    assert choice["type"] == "choose_influence_faction"
    assert choice["amount"] == 1
    assert "fremen" in choice["factions"]
    assert "emperor" in choice["factions"]

    print("✓ 'Any' influence requires faction choice")


# ==================== DRAW TESTS ====================

def test_draw_intrigue():
    """Test drawing intrigue cards."""
    print("\n=== Test: Draw - Intrigue ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Add some cards to intrigue deck
    game.board.intrigue_deck = ["intrigue1", "intrigue2", "intrigue3"]

    initial_count = len(player.intrigue_cards)

    # Test effect from conflicts.JSON - Skirmish (Crysknife) - 2nd place
    effects = [
        {"type": "draw", "deck": "intrigue", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert len(player.intrigue_cards) == initial_count + 1
    assert len(game.board.intrigue_deck) == 2

    print("✓ Draw intrigue works")


def test_accept_contract():
    """Test accepting contracts."""
    print("\n=== Test: Accept - Contract ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Add contracts to deck
    game.board.contract_deck = ["contract1", "contract2"]

    initial_count = len(player.contracts_active)

    # Test effect from contracts.JSON - Contract ID 6
    effects = [
        {"type": "accept", "deck": "contract", "amount": 1}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert len(player.contracts_active) == initial_count + 1

    print("✓ Accept contract works")


# ==================== CONTROL TESTS ====================

def test_control_location():
    """Test taking control of locations."""
    print("\n=== Test: Control - Location ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Test effect from conflicts.JSON - Seize Spice Refinery - 1st place
    effects = [
        {"type": "control", "location": "spice_refinery"}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert "spice_refinery" in player.controlled_locations

    print("✓ Control location works")


# ==================== STATE MODIFICATION TESTS ====================

def test_council_seat():
    """Test granting council seat."""
    print("\n=== Test: Council Seat ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    assert player.has_high_council_sit == False

    # Test effect from spaces.JSON - High Council
    effects = [
        {"type": "council_seat", "value": True}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.has_high_council_sit == True

    print("✓ Council seat works")


def test_maker_hooks():
    """Test granting maker hooks."""
    print("\n=== Test: Maker Hooks ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.has_maker_hooks = False

    # Test effect from spaces.JSON - Sietch Tabr
    effects = [
        {"type": "maker_hooks", "value": True}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert player.has_maker_hooks == True

    print("✓ Maker hooks works")


def test_shieldwall_deactivate():
    """Test deactivating shieldwall."""
    print("\n=== Test: Shieldwall Deactivate ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    game.shieldwall_active = True

    # Test effect from spaces.JSON - Sietch Tabr
    effects = [
        {"type": "shieldwall_deactivate", "value": True}
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert game.shieldwall_active == False

    print("✓ Shieldwall deactivate works")


# ==================== COMPLEX EFFECTS - CONDITIONAL ====================

def test_conditional_can_afford():
    """Test conditional effect when player can afford cost."""
    print("\n=== Test: Conditional - Can Afford ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.spice = 5

    # Test effect from conflicts.JSON - Spice Freights - 1st place
    effects = [
        {
            "type": "conditional",
            "cost": [{"type": "resource", "resource": "spice", "amount": 3}],
            "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
        }
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    # Should require choice (player can afford, so option is presented)
    assert len(result["choices_required"]) == 1
    choice = result["choices_required"][0]
    assert choice["type"] == "conditional"
    assert len(choice["costs"]) == 1
    assert choice["costs"][0]["amount"] == 3

    print("✓ Conditional with affordable cost requires choice")


def test_conditional_cannot_afford():
    """Test conditional effect when player cannot afford cost."""
    print("\n=== Test: Conditional - Cannot Afford ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.spice = 1  # Not enough

    # Test effect from conflicts.JSON - Spice Freights - 1st place
    effects = [
        {
            "type": "conditional",
            "cost": [{"type": "resource", "resource": "spice", "amount": 3}],
            "reward": [{"type": "resource", "resource": "victory_point", "amount": 1}]
        }
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    # Should NOT require choice (player can't afford)
    assert len(result["choices_required"]) == 0
    # Should be marked as declined
    assert len(result["effects_applied"]) == 1
    assert result["effects_applied"][0]["declined"] == True

    print("✓ Conditional with unaffordable cost is auto-declined")


# ==================== COMPLEX EFFECTS - CHOICE ====================

def test_choice_all_available():
    """Test choice effect when all options are available."""
    print("\n=== Test: Choice - All Available ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.spice = 5

    # Test effect from spaces.JSON - Spice Refinery
    effects = [
        {
            "type": "choice",
            "required": True,
            "options": [
                {
                    "id": "option1",
                    "reward": [{"type": "resource", "resource": "solari", "amount": 2}]
                },
                {
                    "id": "option2",
                    "cost": [{"type": "resource", "resource": "spice", "amount": 1}],
                    "reward": [{"type": "resource", "resource": "solari", "amount": 4}]
                }
            ]
        }
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert len(result["choices_required"]) == 1

    choice = result["choices_required"][0]
    assert choice["type"] == "choice"
    assert choice["required"] == True
    assert len(choice["options"]) == 2

    # Both options should be available
    assert choice["options"][0]["available"] == True
    assert choice["options"][1]["available"] == True

    print("✓ Choice with all options available works")


def test_choice_with_gated_option():
    """Test choice effect with option gated by check."""
    print("\n=== Test: Choice - Gated Option ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.has_high_council_sit = False

    # Test effect from spaces.JSON - High Council
    effects = [
        {
            "type": "choice",
            "required": True,
            "options": [
                {
                    "id": "take_seat",
                    "reward": [{"type": "council_seat", "value": True}]
                },
                {
                    "id": "use_seat",
                    "check": [{"type": "council_seat", "value": True}],
                    "reward": [
                        {"type": "resource", "resource": "spice", "amount": 2},
                        {"type": "draw", "deck": "intrigue", "amount": 1},
                        {"type": "resource", "resource": "troop", "amount": 3}
                    ]
                }
            ]
        }
    ]

    result = resolver.resolve_effects("player1", effects)

    assert result["success"] == True
    assert len(result["choices_required"]) == 1

    choice = result["choices_required"][0]
    assert len(choice["options"]) == 2

    # First option should be available
    assert choice["options"][0]["available"] == True

    # Second option should be UNAVAILABLE (requires council seat)
    assert choice["options"][1]["available"] == False
    assert "council seat" in choice["options"][1]["unavailable_reason"].lower()

    print("✓ Choice with gated option correctly marks unavailable")


def test_choice_execution():
    """Test executing a player's choice."""
    print("\n=== Test: Choice - Execution ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    player.solari = 10

    # First, get the choice
    effects = [
        {
            "type": "choice",
            "required": True,
            "options": [
                {
                    "id": "option1",
                    "reward": [{"type": "resource", "resource": "solari", "amount": 2}]
                },
                {
                    "id": "option2",
                    "reward": [{"type": "resource", "resource": "solari", "amount": 5}]
                }
            ]
        }
    ]

    result = resolver.resolve_effects("player1", effects)
    choice_data = result["choices_required"][0]

    # Execute choice: select option2
    initial_solari = player.solari
    choice_result = resolver.execute_choice("player1", choice_data, "option2")

    assert choice_result["success"] == True
    assert player.solari == initial_solari + 5

    print("✓ Choice execution works")


# ==================== REAL WORLD EXAMPLES FROM JSON ====================

def test_conflict_skirmish_rewards():
    """Test complete reward structure from conflicts.JSON - Skirmish (Crysknife)."""
    print("\n=== Test: Real Example - Skirmish Rewards ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load actual data
    conflicts = load_json_data("conflicts.JSON")
    skirmish = conflicts["conflicts"][0]  # ID 1: Skirmish (Crysknife)

    # Test 1st place rewards
    initial_state = {
        "fremen_influence": player.fremen_influence
    }

    result = resolver.resolve_effects("player1", skirmish["rewards"]["1"])

    assert result["success"] == True
    # Should require choice (target is "any")
    assert len(result["choices_required"]) == 1

    print("✓ Real conflict rewards work")


def test_space_deep_desert_choice():
    """Test real example from spaces.JSON - Deep Desert with maker bonus."""
    print("\n=== Test: Real Example - Deep Desert Choice ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load actual data
    spaces = load_json_data("spaces.JSON")
    deep_desert = next(s for s in spaces if s["name"] == "Deep Desert")

    # Test the choice effect
    result = resolver.resolve_effects("player1", deep_desert["reward"])

    assert result["success"] == True
    assert len(result["choices_required"]) == 1

    choice = result["choices_required"][0]
    assert choice["type"] == "choice"
    assert choice["required"] == True
    assert len(choice["options"]) == 2

    # Check option IDs
    option_ids = [opt["id"] for opt in choice["options"]]
    assert "spice" in option_ids
    assert "worms" in option_ids

    print("✓ Real space choice works")


def test_contract_check_resolution():
    """Test real example from contracts.JSON with checks."""
    print("\n=== Test: Real Example - Contract Checks ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load actual data
    contracts = load_json_data("contracts.JSON")
    contract = contracts[1]  # ID 2: agent_on Arrakeen

    # Note: Contracts have checks, not effects, so this tests the check structure
    # The resolver would use _evaluate_checks internally

    # Verify structure
    assert "check" in contract
    assert contract["check"][0]["type"] == "agent_on"
    assert contract["check"][0]["location"] == "Arrakeen"

    # Test reward resolution (assuming check passed)
    result = resolver.resolve_effects("player1", contract["reward"])

    assert result["success"] == True
    assert player.water == 6  # Started with 5, gained 1

    print("✓ Real contract structure works")


def test_leader_signet_ability():
    """Test real example from leaders.JSON - Leader signet ability."""
    print("\n=== Test: Real Example - Leader Signet Ability ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load actual data
    leaders = load_json_data("leaders.JSON")
    lady_jessica = next(l for l in leaders if l["name"] == "Lady Jessica")

    # Test signet ability
    player.temp_persuasion = 0

    result = resolver.resolve_effects("player1", lady_jessica["signet_ability"]["effects"])

    assert result["success"] == True
    assert player.temp_persuasion == 1

    print("✓ Real leader ability works")


def test_multiple_effects_in_sequence():
    """Test resolving multiple effects at once."""
    print("\n=== Test: Multiple Effects Sequence ===")

    game, player = create_test_game()
    resolver = EffectResolver(game)

    # Load real example from conflicts.JSON - Shadow Contest - 2nd place
    conflicts = load_json_data("conflicts.JSON")
    shadow_contest = conflicts["conflicts"][4]  # ID 5

    initial_state = {
        "intrigue": len(player.intrigue_cards),
        "spice": player.spice,
        "troops": player.troops_in_garrison
    }

    # Add intrigue to deck for draw
    game.board.intrigue_deck = ["intrigue1"]

    result = resolver.resolve_effects("player1", shadow_contest["rewards"]["2"])

    assert result["success"] == True
    # Should have 3 effects applied
    assert len(result["effects_applied"]) == 3

    # Verify all effects were applied
    assert len(player.intrigue_cards) == initial_state["intrigue"] + 1
    assert player.spice == initial_state["spice"] + 1
    assert player.troops_in_garrison == initial_state["troops"] + 1

    print("✓ Multiple effects in sequence works")


# ==================== RUN ALL TESTS ====================

def run_all_tests():
    """Run all effect resolver tests."""
    print("\n" + "="*70)
    print("EFFECT RESOLVER TESTS - Using Real JSON Data")
    print("="*70)

    # Simple resource tests
    test_resource_solari()
    test_resource_spice()
    test_resource_water()
    test_resource_troop()
    test_resource_victory_point()

    # Influence tests
    test_influence_specific_faction()
    test_influence_with_multiplier()
    test_influence_any_requires_choice()

    # Draw tests
    test_draw_intrigue()
    test_accept_contract()

    # Control tests
    test_control_location()

    # State modification tests
    test_council_seat()
    test_maker_hooks()
    test_shieldwall_deactivate()

    # Complex effects - Conditional
    test_conditional_can_afford()
    test_conditional_cannot_afford()

    # Complex effects - Choice
    test_choice_all_available()
    test_choice_with_gated_option()
    test_choice_execution()

    # Real world examples
    test_conflict_skirmish_rewards()
    test_space_deep_desert_choice()
    test_contract_check_resolution()
    test_leader_signet_ability()
    test_multiple_effects_in_sequence()

    print("\n" + "="*70)
    print("✅ ALL EFFECT RESOLVER TESTS PASSED")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
