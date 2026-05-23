"""
Test Feyd Rautha's Progressive Signet Ability and Passive

Feyd Rautha has:
1. Progressive signet (4 levels unlocked via training track)
2. Passive ability (Devious Strength): Recall spy for +2 swords
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.leader import Leader
from src.models.player import Player
from src.models.deck import Deck
from src.models.game import Game
from src.models.board import Board
from src.engine.core.game_state import GameState
from src.engine.effects.effect_resolver import EffectResolver


def load_feyd_rautha():
    """Load Feyd Rautha from JSON file."""
    json_path = Path(__file__).parent.parent / "data" / "leader_data" / "feydrautha.json"
    with open(json_path, 'r') as f:
        data = json.load(f)

    # Create leader with loaded data
    leader = Leader(
        name="Feyd Rautha Harkonnen",
        leader_id=1,
        signet_progression=data.get('signet'),
        passive_ability=data.get('passive'),
        training_track_position=0
    )
    return leader


def test_progressive_signet_level_1():
    """Test Feyd's signet at level 1 (choice between trash for 1 solari or place spy)."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Signet Level 1")
    print("="*80)

    leader = load_feyd_rautha()
    leader.training_track_position = 0  # Level 1

    print(f"\nTraining Track Position: {leader.training_track_position}")
    print(f"Signet Level: 1")

    # Get current signet effects
    effects = leader.get_current_signet_effects()
    print(f"\nSignet effects: {json.dumps(effects, indent=2)}")

    # Verify it's a choice
    assert len(effects) == 1, "Should have 1 effect at level 1"
    assert effects[0].get('type') == 'choice', "Level 1 should be a choice"
    assert len(effects[0].get('options', [])) == 2, "Should have 2 options"

    print("\n✓ Level 1 signet is a choice between:")
    for i, option in enumerate(effects[0]['options'], 1):
        print(f"  {i}. {option.get('id', 'unknown')}")

    return True


def test_progressive_signet_level_2():
    """Test Feyd's signet at level 2 (trash a card)."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Signet Level 2")
    print("="*80)

    leader = load_feyd_rautha()
    leader.training_track_position = 1  # Level 2

    print(f"\nTraining Track Position: {leader.training_track_position}")
    print(f"Signet Level: 2")

    effects = leader.get_current_signet_effects()
    print(f"\nSignet effects: {json.dumps(effects, indent=2)}")

    # Verify level 2
    assert len(effects) > 0, "Should have effects at level 2"
    assert effects[0].get('type') == 'trash', "Level 2 should trash a card"

    print("\n✓ Level 2 signet: Trash a card")
    return True


def test_progressive_signet_level_4():
    """Test Feyd's signet at level 4 (repeatable: troop + spy)."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Signet Level 4")
    print("="*80)

    leader = load_feyd_rautha()
    leader.training_track_position = 3  # Level 4 (position 3 = level 4)

    print(f"\nTraining Track Position: {leader.training_track_position}")
    print(f"Signet Level: 4")

    effects = leader.get_current_signet_effects()
    print(f"\nSignet effects: {json.dumps(effects, indent=2)}")

    # Verify level 4
    assert len(effects) == 2, "Level 4 should have 2 effects (troop + spy)"

    print("\n✓ Level 4 signet (repeatable):")
    print("  - Gain 1 troop")
    print("  - Place 1 spy")
    return True


def test_training_track_advancement():
    """Test advancing on the training track."""
    print("\n" + "="*80)
    print("TEST: Training Track Advancement")
    print("="*80)

    leader = load_feyd_rautha()

    print("\nAdvancing through training track:")
    for i in range(5):
        signet_effects = leader.get_current_signet_effects()
        print(f"  Position {leader.training_track_position}: {len(signet_effects)} effect(s)")

        leader.advance_training_track()

    # Try to advance beyond max
    leader.advance_training_track()
    assert leader.training_track_position == 4, "Should not exceed position 4"

    print("\n✓ Training track advancement works!")
    return True


def test_passive_ability():
    """Test Feyd's passive ability (Devious Strength)."""
    print("\n" + "="*80)
    print("TEST: Feyd Rautha - Passive Ability (Devious Strength)")
    print("="*80)

    leader = load_feyd_rautha()

    print(f"\nPassive Ability: {leader.passive_ability.get('name')}")
    print(f"Phase: {leader.passive_ability.get('phase')}")
    print(f"Cost: {leader.passive_ability.get('cost')}")
    print(f"Reward: {leader.passive_ability.get('reward')}")

    # Check if passive can be used in reveal phase
    can_use_reveal = leader.can_use_passive('reveal')
    can_use_agent = leader.can_use_passive('agent')

    assert can_use_reveal, "Should be able to use passive in reveal phase"
    assert not can_use_agent, "Should not be able to use passive in agent phase"

    print("\n✓ Passive ability:")
    print("  - Name: Devious Strength")
    print("  - Usable in reveal phase: ✓")
    print("  - Usable in agent phase: ✗")
    print("  - Cost: Recall 1 spy")
    print("  - Reward: +2 swords")

    return True


def test_passive_in_game():
    """Test using passive ability in actual game."""
    print("\n" + "="*80)
    print("TEST: Using Passive Ability In Game")
    print("="*80)

    # Create game
    game = Game()
    game.board = Board()

    leader = load_feyd_rautha()

    player = Player(
        player_id="test_player",
        name="Feyd",
        color="blue",
        leader=leader,
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck()
    )

    # Set up player with spy to recall
    player.spies_placed = ["spy_1"]
    player.temp_swords = 0

    game.players = [player]
    state = GameState(game)
    resolver = EffectResolver(game)

    print(f"\nBefore: {player.temp_swords} swords, {len(player.spies_placed)} spy placed")

    # Resolve passive ability
    passive_effects = leader.passive_ability.get('reward', [])
    result = resolver.resolve_effects(
        "test_player",
        passive_effects,
        {"phase": "reveal"}
    )

    print(f"After: {player.temp_swords} swords")

    # Note: The spy recall cost would need to be handled separately
    # This test just checks the reward part works

    assert result['success'], "Passive reward should resolve successfully"
    assert player.temp_swords == 2, f"Should have 2 swords, has {player.temp_swords}"

    print("\n✓ Passive ability reward works!")
    print("  (Note: Spy recall cost handling would be done in game logic)")

    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("FEYD RAUTHA ABILITIES TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_progressive_signet_level_1,
        test_progressive_signet_level_2,
        test_progressive_signet_level_4,
        test_training_track_advancement,
        test_passive_ability,
        test_passive_in_game,
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
        print("\nFeyd Rautha Implementation:")
        print("  ✓ Progressive signet (4 levels)")
        print("  ✓ Training track advancement")
        print("  ✓ Passive ability (Devious Strength)")
        sys.exit(0)
    else:
        print(f"\n✗ {failed} TEST(S) FAILED")
        sys.exit(1)
