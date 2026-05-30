"""
Test Signet Ring and Leader Signet Abilities

Tests that Signet Ring correctly triggers leader abilities during reveal.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.leader import Leader
from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.engine.core.game_state import GameState
from src.engine.effects.effect_resolver import EffectResolver
from src.loaders.leader_loader import load_leaders


def test_signet_agent_phase():
    """Signet triggers the leader's ability during the agent phase.

    The Signet Ring card carries the signet effect in its agent_effects, so
    playing it to send an agent must fire the leader's Signet ability.
    """
    print("\n" + "="*80)
    print("TEST: Signet Ring - Agent Phase (Should Trigger Leader Ability)")
    print("="*80)

    # Create game and leader
    game = Game()
    leader = Leader(
        name="Test Leader",
        leader_id=1,
        signet_ability={
            "type": "test",
            "effects": [{"type": "resource", "resource": "solari", "amount": 5}]
        }
    )

    player = Player(
        player_id="test_player",
        name="Test Player",
        color="blue",
        leader=leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    game.players = [player]
    state = GameState(game)
    resolver = EffectResolver(game)

    # Resolve signet effect in agent phase
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "agent"}
    )

    print(f"\nResult: {result}")
    print(f"Player solari: {player.solari} (should be 5)")

    assert result["success"], "Signet should succeed in agent phase"
    assert player.solari == 5, "Signet should trigger leader ability in agent phase"
    print("✓ Signet triggers leader ability in agent phase (correct!)")
    return True


def test_signet_reveal_phase():
    """Test that signet triggers leader ability during reveal."""
    print("\n" + "="*80)
    print("TEST: Signet Ring - Reveal Phase (Should Trigger Leader Ability)")
    print("="*80)

    # Create game and leader with signet ability
    game = Game()
    leader = Leader(
        name="Lady Jessica",
        leader_id=4,
        signet_ability={
            "type": "persuasion",
            "description": "+1 persuasion when you reveal",
            "effects": [{"type": "resource", "resource": "persuasion", "amount": 1}]
        }
    )

    player = Player(
        player_id="test_player",
        name="Test Player",
        color="blue",
        leader=leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    # Initialize temp_persuasion for reveal phase
    player.temp_persuasion = 0

    game.players = [player]
    state = GameState(game)
    resolver = EffectResolver(game)

    print(f"\nLeader: {leader.name}")
    print(f"Signet ability: {leader.signet_ability['description']}")
    print(f"\nBefore reveal: temp_persuasion = {player.temp_persuasion}")

    # Resolve signet effect in reveal phase
    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )

    print(f"\nResult: {result}")
    print(f"After reveal: temp_persuasion = {player.temp_persuasion}")

    assert result["success"], "Signet should succeed in reveal phase"
    assert player.temp_persuasion == 1, f"Should have 1 persuasion, has {player.temp_persuasion}"
    print("✓ Signet triggered leader ability correctly!")
    return True


def test_all_leaders_signet_abilities():
    """Test signet abilities for all leaders from JSON."""
    print("\n" + "="*80)
    print("TEST: All Leader Signet Abilities")
    print("="*80)

    # Load all leaders
    leaders = load_leaders()
    print(f"\nLoaded {len(leaders)} leaders\n")

    for leader in leaders:
        print(f"\n{leader.name}:")
        signet = leader.signet_ability or {}
        print(f"  Signet: {signet.get('description', 'No description')}")

        # Create test game
        game = Game()

        # Set up board with intrigue deck for Lady Margot Fenring
        from src.models.board import Board
        game.board = Board()

        # Add dummy intrigue cards to deck
        for i in range(5):
            intrigue_card = type('IntrigueCard', (), {
                'id': f'intrigue_{i}',
                'name': f'Intrigue {i}'
            })()
            game.board.intrigue_deck.append(intrigue_card)

        player = Player(
            player_id="test_player",
            name="Test Player",
            color="blue",
            leader=leader,
            deck=Deck(),
            hand=Deck(),
            discard_pile=Deck()
        )

        # Initialize resources
        player.temp_persuasion = 0
        player.temp_swords = 0

        game.players = [player]
        state = GameState(game)
        resolver = EffectResolver(game)

        # Test signet in reveal phase
        result = resolver.resolve_effects(
            "test_player",
            [{"type": "signet"}],
            {"phase": "reveal"}
        )

        if result["success"]:
            print(f"  ✓ Signet ability works")
            print(f"    Effects: {result.get('effects_applied', [])}")
        else:
            print(f"  ✗ FAILED: {result.get('error')}")
            return False

    print("\n✓ All leader signet abilities work!")
    return True


def test_combat_leader_signet():
    """Test combat-focused leader (Gurney Halleck)."""
    print("\n" + "="*80)
    print("TEST: Combat Leader - Gurney Halleck (+2 swords)")
    print("="*80)

    game = Game()
    leader = Leader(
        name="Gurney Halleck",
        leader_id=2,
        signet_ability={
            "type": "combat",
            "description": "+2 swords when you reveal",
            "effects": [{"type": "resource", "resource": "sword", "amount": 2}]
        }
    )

    player = Player(
        player_id="test_player",
        name="Test Player",
        color="blue",
        leader=leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    player.temp_swords = 0

    game.players = [player]
    state = GameState(game)
    resolver = EffectResolver(game)

    print(f"\nBefore: {player.temp_swords} swords")

    result = resolver.resolve_effects(
        "test_player",
        [{"type": "signet"}],
        {"phase": "reveal"}
    )

    print(f"After: {player.temp_swords} swords")

    assert result["success"], "Signet should succeed"
    assert player.temp_swords == 2, f"Should have 2 swords, has {player.temp_swords}"
    print("✓ Combat leader signet works!")
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SIGNET RING ABILITIES TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_signet_agent_phase,
        test_signet_reveal_phase,
        test_all_leaders_signet_abilities,
        test_combat_leader_signet,
    ]

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n✗ TEST FAILED: {e}")
            import traceback
            traceback.print_exc()
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
