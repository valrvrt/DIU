#!/usr/bin/env python3
"""Quick test script to verify all loaders work correctly."""

import sys
from pathlib import Path

# Add parent directory to path so we can import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loaders.card_loader import (
    load_starter_deck, load_imperium_cards, load_intrigue_cards,
    load_conflict_cards, load_contract_cards, load_leaders, get_reserve_cards
)
from src.loaders.board_loader import load_board_spaces, load_observation_posts

def test_loaders():
    print("=" * 60)
    print("TESTING DATA LOADERS")
    print("=" * 60)

    # Test starter deck
    print("\n📦 Loading Starter Deck...")
    starter = load_starter_deck()
    print(f"   ✓ Loaded {len(starter)} cards")
    assert len(starter) == 7, f"Expected 7, got {len(starter)}"
    print(f"   Sample: {starter[0].name} - Agent icons: {starter[0].agent_icons}")

    # Test Imperium cards
    print("\n📦 Loading Imperium Cards...")
    imperium = load_imperium_cards()
    print(f"   ✓ Loaded {len(imperium)} cards")
    assert len(imperium) == 6, f"Expected 6, got {len(imperium)}"

    # Test Reserve separation
    print("\n📦 Separating Reserve Cards...")
    reserve = get_reserve_cards()
    print(f"   ✓ Prepare the Way: {len(reserve['prepare_the_way'])} cards")
    print(f"   ✓ Spice Must Flow: {len(reserve['spice_must_flow'])} cards")

    # Test Intrigue cards
    print("\n📦 Loading Intrigue Cards...")
    intrigue = load_intrigue_cards()
    print(f"   ✓ Loaded {len(intrigue)} cards")
    assert len(intrigue) == 4, f"Expected 4, got {len(intrigue)}"
    print(f"   Sample: {intrigue[0].name} - Phases: {intrigue[0].phases}")

    # Test Conflict cards
    print("\n📦 Loading Conflict Cards...")
    conflicts = load_conflict_cards()
    print(f"   ✓ Loaded {len(conflicts)} cards")
    assert len(conflicts) == 4, f"Expected 4, got {len(conflicts)}"
    print(f"   Sample: {conflicts[0].name} - Location: {conflicts[0].location}")

    # Test Contract cards
    print("\n📦 Loading Contract Cards...")
    contracts = load_contract_cards()
    print(f"   ✓ Loaded {len(contracts)} cards")
    assert len(contracts) == 4, f"Expected 4, got {len(contracts)}"
    print(f"   Sample: {contracts[0].name} - Type: {contracts[0].completion_type}")

    # Test Leaders
    print("\n📦 Loading Leaders...")
    leaders = load_leaders()
    print(f"   ✓ Loaded {len(leaders)} leaders")
    assert len(leaders) == 4, f"Expected 4, got {len(leaders)}"
    print(f"   Sample: {leaders[0].name} - Ring effects: {leaders[0].ring}")

    # Test Board Spaces
    print("\n📦 Loading Board Spaces...")
    spaces = load_board_spaces()
    print(f"   ✓ Loaded {len(spaces)} spaces")
    assert len(spaces) == 8, f"Expected 8, got {len(spaces)}"
    print(f"   Sample: {spaces[0].name} - Icon: {spaces[0].agent_icon}")

    # Test Observation Posts
    print("\n📦 Loading Observation Posts...")
    posts = load_observation_posts()
    print(f"   ✓ Loaded {len(posts)} posts")
    assert len(posts) == 4, f"Expected 4, got {len(posts)}"
    print(f"   Sample: {posts[0].name} - Connects to {len(posts[0].connected_locations)} locations")

    # Summary
    print("\n" + "=" * 60)
    print("✅ ALL LOADERS PASSED!")
    print("=" * 60)
    print(f"Total items loaded: {len(starter) + len(imperium) + len(intrigue) + len(conflicts) + len(contracts) + len(leaders) + len(spaces) + len(posts)}")
    print()

if __name__ == "__main__":
    try:
        test_loaders()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
