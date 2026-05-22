"""
Test effect ordering system.

Tests both:
- Heuristic ordering for bots
- Interactive ordering for human players (simulated)
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.actions.effect_ordering import EffectOrderingManager


def test_heuristic_ordering():
    """Test that bot heuristic orders effects correctly."""
    print("\n" + "="*80)
    print("TEST: Heuristic Effect Ordering (Bots)")
    print("="*80)

    manager = EffectOrderingManager()

    # Create mixed effects
    effects = [
        {"type": "influence", "target": "fremen", "amount": 1},
        {"type": "resource", "resource": "solari", "amount": 2},
        {"type": "draw", "deck": "deck", "amount": 1},
        {"type": "resource", "resource": "spice", "amount": 1},
        {"type": "trash", "deck": "hand", "amount": 1},
    ]

    print("\nOriginal order:")
    for i, eff in enumerate(effects, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    ordered = manager.order_effects_interactive(
        player_id="bot1",
        effects=effects,
        context={"phase": "agent"},
        is_human=False
    )

    print("\nHeuristic-ordered:")
    for i, eff in enumerate(ordered, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    # Verify priority order
    # Should be: solari, spice, draw, influence, trash
    assert ordered[0]["resource"] == "solari", "Solari should be first"
    assert ordered[1]["resource"] == "spice", "Spice should be second"
    assert ordered[2]["type"] == "draw", "Draw should be third"
    assert ordered[3]["type"] == "influence", "Influence should be fourth"
    assert ordered[4]["type"] == "trash", "Trash should be last"

    print("\n✓ Heuristic ordering correct!")
    print("  Priority: Resources → Draw → Influence → Other")
    return True


def test_interactive_ordering_simulated():
    """Test interactive ordering with simulated human input."""
    print("\n" + "="*80)
    print("TEST: Interactive Effect Ordering (Human - Simulated)")
    print("="*80)

    # Simulate human player choosing order: 2, 1, 3
    # (Choose draw first, then solari, then influence)
    choices = iter(['2', '1', '3'])  # Player choices

    def mock_input(prompt):
        choice = next(choices)
        print(f"{prompt}{choice}")
        return choice

    manager = EffectOrderingManager(get_player_input_fn=mock_input)

    effects = [
        {"type": "resource", "resource": "solari", "amount": 2},
        {"type": "draw", "deck": "deck", "amount": 1},
        {"type": "influence", "target": "fremen", "amount": 1},
    ]

    print("\nAvailable effects:")
    for i, eff in enumerate(effects, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    print("\nPlayer chooses order: 2, 1, 3")

    ordered = manager.order_effects_interactive(
        player_id="human1",
        effects=effects,
        context={
            "phase": "agent",
            "card": "Test Card",
            "location": "Test Location"
        },
        is_human=True
    )

    print("\nPlayer-ordered:")
    for i, eff in enumerate(ordered, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    # Verify player's choice was respected
    assert ordered[0]["type"] == "draw", "Draw should be first (player chose 2)"
    assert ordered[1]["resource"] == "solari", "Solari should be second (player chose 1)"
    assert ordered[2]["type"] == "influence", "Influence should be last (player chose 3)"

    print("\n✓ Interactive ordering works!")
    print("  Player's choices were respected")
    return True


def test_effect_descriptions():
    """Test that effect descriptions are human-readable."""
    print("\n" + "="*80)
    print("TEST: Effect Descriptions")
    print("="*80)

    manager = EffectOrderingManager()

    test_effects = [
        ({"type": "resource", "resource": "solari", "amount": 3}, "Gain 3 solari"),
        ({"type": "draw", "deck": "intrigue", "amount": 2}, "Draw 2 card(s) from intrigue"),
        ({"type": "influence", "target": "emperor", "amount": 1}, "Gain 1 emperor influence"),
        ({"type": "trash", "deck": "hand", "amount": 1}, "Trash 1 card(s) from hand"),
        ({"type": "play", "unit": "spy"}, "Play spy"),
        ({"type": "conditional"}, "Conditional effect (if condition met)"),
    ]

    print("\nEffect descriptions:")
    for effect, expected in test_effects:
        desc = manager._describe_effect(effect)
        print(f"  {effect} → \"{desc}\"")
        if expected in desc or desc in expected:
            print(f"    ✓ Correct")
        else:
            print(f"    ✗ Expected something like: {expected}")
            return False

    print("\n✓ All descriptions are readable!")
    return True


def test_special_actions_in_ordering():
    """Test that special actions (D, I, A) can be inserted."""
    print("\n" + "="*80)
    print("TEST: Special Actions During Ordering")
    print("="*80)

    # Simulate: resolve effect 1, deploy troops, resolve effect 1 (only 1 effect left)
    choices = iter(['1', 'D', '1'])

    def mock_input(prompt):
        choice = next(choices, 'done')
        if choice != 'done':
            print(f"{prompt}{choice}")
        return choice

    manager = EffectOrderingManager(get_player_input_fn=mock_input)

    effects = [
        {"type": "resource", "resource": "solari", "amount": 2},
        {"type": "draw", "deck": "deck", "amount": 1},
    ]

    print("\nPlayer actions: 1 (solari), D (deploy troops), 2 (draw)")

    ordered = manager.order_effects_interactive(
        player_id="human1",
        effects=effects,
        context={"phase": "agent", "card": "Test", "location": "Combat Space"},
        is_human=True
    )

    print("\nOrdered actions:")
    for i, eff in enumerate(ordered, 1):
        if eff.get("type") == "_deploy_troops_action":
            print(f"  {i}. [DEPLOY TROOPS]")
        else:
            print(f"  {i}. {manager._describe_effect(eff)}")

    # Verify special action was inserted
    assert ordered[0]["resource"] == "solari", "Solari should be first"
    assert ordered[1]["type"] == "_deploy_troops_action", "Deploy troops should be second"
    assert ordered[2]["type"] == "draw", "Draw should be last"

    print("\n✓ Special actions can be interleaved!")
    print("  Player can deploy troops/play intrigue at any point")
    return True


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EFFECT ORDERING TEST SUITE")
    print("="*80)

    passed = 0
    failed = 0

    tests = [
        test_heuristic_ordering,
        test_interactive_ordering_simulated,
        test_effect_descriptions,
        test_special_actions_in_ordering,
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
