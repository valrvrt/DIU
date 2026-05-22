"""
Demo: Interactive Effect Resolution Order

Shows how the effect ordering system works for human players.

Demonstrates:
1. Agent Phase: Player chooses order for card + board effects
2. Can interleave: Deploy troops, play intrigue
3. Reveal Phase: Player chooses order, can acquire cards mid-resolution
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.engine.actions.effect_ordering import EffectOrderingManager


def demo_agent_phase():
    """Demo effect ordering during agent phase."""
    print("\n" + "="*80)
    print("DEMO: Agent Phase Effect Ordering")
    print("="*80)

    print("\nScenario:")
    print("  You play 'Desert Power' card at 'Sietch Tabr' location")
    print("  Card gives: 2 spice, 1 water")
    print("  Location gives: 1 troop, draw 1 card")
    print("  You're on a combat space")

    # Create effects
    card_effects = [
        {"type": "resource", "resource": "spice", "amount": 2},
        {"type": "resource", "resource": "water", "amount": 1},
    ]

    location_effects = [
        {"type": "resource", "resource": "troop", "amount": 1},
        {"type": "draw", "deck": "deck", "amount": 1},
    ]

    all_effects = card_effects + location_effects

    manager = EffectOrderingManager()

    print("\nAll available effects:")
    for i, eff in enumerate(all_effects, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    print("\nBOT CHOICE (Heuristic):")
    bot_ordered = manager.order_effects_interactive(
        player_id="bot",
        effects=all_effects,
        context={"phase": "agent", "card": "Desert Power", "location": "Sietch Tabr"},
        is_human=False
    )

    print("Bot will resolve in this order:")
    for i, eff in enumerate(bot_ordered, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    print("\n" + "-"*80)
    print("\nHUMAN CHOICE (Interactive):")
    print("Human player might choose:")
    print("  1. Get spice first (currency)")
    print("  2. Deploy 2 troops to conflict")
    print("  3. Get water")
    print("  4. Get troop")
    print("  5. Draw card (might draw something useful)")

    print("\nThis gives strategic flexibility!")


def demo_reveal_phase():
    """Demo effect ordering during reveal phase with acquisitions."""
    print("\n" + "="*80)
    print("DEMO: Reveal Phase with Acquisitions")
    print("="*80)

    print("\nScenario:")
    print("  You reveal 'Arrakis Liaison' (gives 2 persuasion, 1 solari)")
    print("  Imperium row has:")
    print("    - Mentat (cost 2)")
    print("    - Stillsuit (cost 3)")
    print("    - Spice Harvester (cost 5)")

    manager = EffectOrderingManager()

    reveal_effects = [
        {"type": "resource", "resource": "persuasion", "amount": 2},
        {"type": "resource", "resource": "solari", "amount": 1},
    ]

    print("\nReveal effects:")
    for i, eff in enumerate(reveal_effects, 1):
        print(f"  {i}. {manager._describe_effect(eff)}")

    print("\nHuman player flow:")
    print("  1. Resolve: Gain 2 persuasion (now have 2)")
    print("  2. ACQUIRE Mentat (cost 2, triggers on_acquire: draw intrigue)")
    print("     - On-acquire effect resolves immediately")
    print("  3. Resolve: Gain 1 solari")
    print("\nThis lets you get on_acquire effects before finishing reveal!")


def demo_strategic_importance():
    """Show why effect ordering matters strategically."""
    print("\n" + "="*80)
    print("WHY EFFECT ORDERING MATTERS")
    print("="*80)

    print("\nExample 1: Resources before Draw")
    print("  Effects: [Gain 2 solari, Draw 1 card]")
    print("  ✓ GOOD: Solari first, then draw")
    print("    → Might draw a card you can afford to buy")
    print("  ✗ BAD: Draw first, then solari")
    print("    → Drawn card might need resources you don't have yet")

    print("\nExample 2: Troops before Conflict Resolution")
    print("  Effects: [Gain 2 troops, Draw intrigue]")
    print("  ✓ GOOD: Troops first, deploy to conflict, then draw")
    print("    → Can use troops immediately")
    print("  ✗ BAD: Draw first, then troops")
    print("    → Might miss combat opportunities")

    print("\nExample 3: Reveal + Acquire Combo")
    print("  Effects: [Gain 3 persuasion, Gain 1 influence]")
    print("  ✓ GOOD: Persuasion, acquire card (with on_acquire), then influence")
    print("    → On-acquire might give more resources")
    print("  ✗ BAD: All persuasion at once, miss acquisition windows")


if __name__ == "__main__":
    print("="*80)
    print("DUNE: IMPERIUM UPRISING")
    print("Interactive Effect Resolution Order System")
    print("="*80)

    demo_agent_phase()
    demo_reveal_phase()
    demo_strategic_importance()

    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("\nThe effect ordering system allows:")
    print("  ✓ Players choose effect resolution order")
    print("  ✓ Strategic timing of effects")
    print("  ✓ Interleave special actions (troops, intrigue)")
    print("  ✓ Acquire cards mid-resolution (reveal phase)")
    print("  ✓ Bots use heuristic ordering")
    print("\nThis matches real DUNE: Imperium gameplay!")
    print("="*80)
