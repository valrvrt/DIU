#!/usr/bin/env python3
"""
Detailed test for spy placement during on_acquire_effects.
Tests both the effect resolution AND the game state properly tracking spies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from engine.core.game_setup import GameSetup
from engine.core.game_state import GameState
from engine.effects.effect_resolver import EffectResolver


def test_spy_placement_detailed():
    """Comprehensive test of spy placement on acquire."""
    print("\n" + "="*80)
    print("DETAILED SPY PLACEMENT TEST - ON_ACQUIRE_EFFECTS")
    print("="*80)

    # Create real game with full setup
    game, setup_info = GameSetup.create_game(player_count=2)
    player = game.players[0]
    state = GameState(game)
    resolver = EffectResolver(game)

    print(f"\n1. INITIAL GAME STATE")
    print(f"   Player: {player.name} (ID: {player.player_id})")
    print(f"   Spies available: {player.spies_available}")
    print(f"   Spies placed: {player.spies_placed}")
    print(f"   Observation posts on board: {len(game.board.observation_posts)}")

    if game.board.observation_posts:
        print(f"\n   Observation Posts:")
        for i, post in enumerate(game.board.observation_posts[:5], 1):
            print(f"     {i}. ID={post.id}, Name={post.name}, Controls={post.connected_locations}")

    # Test spy placement effect (as found in Guild Spy, etc.)
    spy_effect = [
        {
            "type": "play",
            "unit": "spy",
            "amount": 1
        }
    ]

    print(f"\n2. RESOLVING SPY PLACEMENT EFFECT")
    print(f"   Effect: {spy_effect}")

    context = {
        "card": "Guild Spy",
        "phase": "acquire",
        "player_id": player.player_id
    }

    result = resolver.resolve_effects(player.player_id, spy_effect, context)

    print(f"\n3. RESOLUTION RESULT")
    print(f"   Success: {result.get('success')}")
    print(f"   Choices required: {result.get('choices_required', False)}")

    if result.get('error'):
        print(f"   ERROR: {result['error']}")

    if result.get('applied_effects'):
        print(f"   Applied effects:")
        for i, effect in enumerate(result['applied_effects'], 1):
            print(f"     {i}. {effect}")

    print(f"\n4. FINAL GAME STATE")
    print(f"   Spies available: {player.spies_available}")
    print(f"   Spies placed: {player.spies_placed}")

    # Verify spy was placed
    print(f"\n5. VERIFICATION")
    if player.spies_available == 2:  # Started with 3, placed 1
        print(f"   ✓ Spy count decreased correctly (3 → 2)")
    else:
        print(f"   ✗ FAIL: Expected 2 spies available, got {player.spies_available}")

    if hasattr(player, 'spies_placed') and len(player.spies_placed) == 1:
        print(f"   ✓ Spy tracked in spies_placed list")
        print(f"   ✓ Spy placed on observation post: {player.spies_placed[0]}")

        # Find which observation post it was
        for post in game.board.observation_posts:
            if str(post.id) == player.spies_placed[0]:
                print(f"   ✓ Post name: {post.name}")
                print(f"   ✓ Controls locations: {post.connected_locations}")
                break
    else:
        print(f"   ✗ FAIL: Spy not tracked in spies_placed")
        print(f"      spies_placed = {getattr(player, 'spies_placed', 'NOT SET')}")

    # Test 5 cards with spy on acquire
    print(f"\n" + "="*80)
    print("TESTING ALL 5 CARDS WITH SPY ON ACQUIRE")
    print("="*80)

    from loaders.card_loader import load_imperium_cards
    imperium_cards = load_imperium_cards()

    spy_cards = [
        card for card in imperium_cards
        if any(
            effect.get('type') == 'play' and effect.get('unit') == 'spy'
            for effect in card.get('on_acquire_effects', [])
        )
    ]

    print(f"\nFound {len(spy_cards)} cards with spy on acquire:")
    for card in spy_cards:
        print(f"  [{card['id']:2d}] {card['name']}")

    # Test each one
    passed = 0
    failed = []

    for card in spy_cards:
        # Create fresh game for each card
        game2, _ = GameSetup.create_game(player_count=2)
        player2 = game2.players[0]
        resolver2 = EffectResolver(game2)

        initial_spies = player2.spies_available

        context2 = {
            "card": card['name'],
            "phase": "acquire",
            "player_id": player2.player_id
        }

        result2 = resolver2.resolve_effects(
            player2.player_id,
            card.get('on_acquire_effects', []),
            context2
        )

        if result2.get('success') and player2.spies_available == initial_spies - 1:
            if len(player2.spies_placed) == 1:
                passed += 1
                print(f"  [{card['id']:2d}] {card['name']:30s} ✓ (spy placed on post {player2.spies_placed[0]})")
            else:
                failed.append((card['id'], card['name'], "Spy count changed but not tracked"))
        else:
            error = result2.get('error', 'Unknown error')
            failed.append((card['id'], card['name'], error))

    print(f"\nResults: {passed}/{len(spy_cards)} passed")

    if failed:
        print(f"\nFailed cards:")
        for card_id, name, error in failed:
            print(f"  [{card_id}] {name}: {error}")

    print("\n" + "="*80)

    if passed == len(spy_cards):
        print("SUCCESS: All spy placement effects work correctly!")
    else:
        print(f"FAILURE: {len(failed)} cards failed")

    print("="*80 + "\n")


if __name__ == "__main__":
    test_spy_placement_detailed()
