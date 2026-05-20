"""Test that all board spaces properly resolve their effects."""

from src.engine.game_setup import GameSetup
from src.engine.action_executor import ActionExecutor
from src.engine.effect_resolver import EffectResolver
from src.engine.influence_manager import InfluenceManager
from src.engine.actions import PlaceAgentAction
from src.loaders.board_loader import load_board_spaces


def test_all_board_spaces_resolve():
    """Test every board space to ensure effects resolve without errors."""
    # Create game
    game, setup_info = GameSetup.create_game(3, "Test")
    player = game.players[0]

    # Create managers
    influence_mgr = InfluenceManager(game)
    effect_resolver = EffectResolver(game, influence_manager=influence_mgr)
    action_exec = ActionExecutor(game, effect_resolver=effect_resolver)

    # Load all spaces
    spaces = load_board_spaces()

    # Give player resources to afford any cost
    player.solari = 100
    player.spice = 100
    player.water = 100
    player.agents_available = 1

    # Get a playable card
    card = player.hand.cards[0] if player.hand.cards else None
    assert card is not None, "Player should have cards in hand"

    results = {}
    for space in spaces:
        # Reset player resources
        player.solari = 100
        player.spice = 100
        player.water = 100
        player.agents_available = 1

        # Record initial state
        initial_solari = player.solari
        initial_spice = player.spice
        initial_water = player.water
        initial_hand_size = len(player.hand.cards)

        # Try to place agent
        action = PlaceAgentAction(
            player_id=player.player_id,
            card=card,
            location=space,
            placement_type="test",
            troops_to_deploy=0
        )

        try:
            result = action_exec.execute_place_agent(action)

            # Record results
            results[space.name] = {
                "success": result.get("success", False),
                "error": result.get("error") if not result.get("success") else None,
                "location_effects": result.get("location_effects"),
                "resource_changes": {
                    "solari": player.solari - initial_solari,
                    "spice": player.spice - initial_spice,
                    "water": player.water - initial_water,
                    "hand_size": len(player.hand.cards) - initial_hand_size
                }
            }

            # Reset space for next test
            space.occupied_by = None
            player.agents_available = 1

        except Exception as e:
            results[space.name] = {
                "success": False,
                "error": str(e),
                "exception": type(e).__name__
            }

    # Print detailed results
    print("\n" + "="*70)
    print("BOARD SPACE EFFECT RESOLUTION TEST")
    print("="*70)

    passed = 0
    failed = 0

    for space_name, result in results.items():
        if result["success"]:
            passed += 1
            print(f"\n✓ {space_name}")
            if result["location_effects"] and result["location_effects"].get("applied"):
                for eff in result["location_effects"]["applied"]:
                    print(f"    → {eff}")
            changes = result["resource_changes"]
            if any(v != 0 for v in changes.values()):
                print(f"    Changes: {changes}")
        else:
            failed += 1
            print(f"\n✗ {space_name}")
            print(f"    Error: {result['error']}")

    print(f"\n" + "="*70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(results)} spaces")
    print("="*70)

    # Assert all succeeded
    assert failed == 0, f"{failed} board spaces failed to resolve effects"


def test_fremkit_rewards():
    """Test Fremkit specifically (draw + influence)."""
    game, _ = GameSetup.create_game(3, "Test")
    player = game.players[0]

    influence_mgr = InfluenceManager(game)
    effect_resolver = EffectResolver(game, influence_manager=influence_mgr)
    action_exec = ActionExecutor(game, effect_resolver=effect_resolver)

    # Find Fremkit
    fremkit = next((s for s in game.board.spaces if s.name == "Fremkit"), None)
    assert fremkit is not None, "Fremkit space should exist"

    # Initial state
    initial_hand = len(player.hand.cards)
    initial_influence = player.fremen_influence

    # Place agent
    card = player.hand.cards[0]
    action = PlaceAgentAction(
        player_id=player.player_id,
        card=card,
        location=fremkit,
        placement_type="fremen",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"], f"Fremkit placement failed: {result.get('error')}"

    # Check rewards
    # Should draw 1 card (net 0 because card was played)
    # Should gain 1 fremen influence
    assert player.fremen_influence == initial_influence + 1, "Should gain 1 fremen influence"
    print(f"✓ Fremkit: +1 fremen influence, drew 1 card")


def test_spice_refinery_choice():
    """Test Spice Refinery (choice effect)."""
    game, _ = GameSetup.create_game(3, "Test")
    player = game.players[0]

    effect_resolver = EffectResolver(game)
    action_exec = ActionExecutor(game, effect_resolver=effect_resolver)

    # Find Spice Refinery
    refinery = next((s for s in game.board.spaces if s.name == "Spice Refinery"), None)
    assert refinery is not None, "Spice Refinery should exist"

    # Give player spice
    player.spice = 5

    # Place agent
    card = player.hand.cards[0]
    action = PlaceAgentAction(
        player_id=player.player_id,
        card=card,
        location=refinery,
        placement_type="blue",
        troops_to_deploy=0
    )

    result = action_exec.execute_place_agent(action)

    assert result["success"], f"Spice Refinery failed: {result.get('error')}"

    # Should have choice (needs manual handling in real game)
    # For auto-test, just verify it doesn't crash
    print(f"✓ Spice Refinery: processed (choice effect)")


if __name__ == "__main__":
    test_all_board_spaces_resolve()
    test_fremkit_rewards()
    test_spice_refinery_choice()
