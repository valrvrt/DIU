"""Quick test to verify all loaders work with new JSON paths."""

from src.loaders.card_loader import (
    load_starter_deck,
    load_imperium_cards,
    load_intrigue_cards,
    load_conflict_cards,
    load_contract_cards,
    load_leaders,
    load_objectives
)
from src.loaders.board_loader import load_board_spaces, load_observation_posts

def test_all_loaders():
    """Test that all loaders can successfully load their JSON files."""

    print("="*70)
    print("TESTING ALL LOADERS")
    print("="*70)

    try:
        print("\n📦 Loading starter deck...")
        starter = load_starter_deck()
        print(f"   ✓ Loaded {len(starter)} starter cards")
        if starter:
            print(f"   First card: {starter[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading imperium cards...")
        imperium = load_imperium_cards()
        print(f"   ✓ Loaded {len(imperium)} imperium cards")
        if imperium:
            print(f"   First card: {imperium[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading intrigue cards...")
        intrigue = load_intrigue_cards()
        print(f"   ✓ Loaded {len(intrigue)} intrigue cards")
        if intrigue:
            print(f"   First card: {intrigue[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading conflict cards...")
        conflicts = load_conflict_cards()
        print(f"   ✓ Loaded {len(conflicts)} conflict cards")
        if conflicts:
            print(f"   First card: {conflicts[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading contract cards...")
        contracts = load_contract_cards()
        print(f"   ✓ Loaded {len(contracts)} contract cards")
        if contracts:
            print(f"   First card: {contracts[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading leaders...")
        leaders = load_leaders()
        print(f"   ✓ Loaded {len(leaders)} leaders")
        if leaders:
            print(f"   First leader: {leaders[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading objectives...")
        objectives = load_objectives()
        print(f"   ✓ Loaded {len(objectives)} objectives")
        if objectives:
            print(f"   First objective: {objectives[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading board spaces...")
        spaces = load_board_spaces()
        print(f"   ✓ Loaded {len(spaces)} board spaces")
        if spaces:
            print(f"   First space: {spaces[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    try:
        print("\n📦 Loading observation posts...")
        posts = load_observation_posts()
        print(f"   ✓ Loaded {len(posts)} observation posts")
        if posts:
            print(f"   First post: {posts[0].name}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "="*70)
    print("LOADER TESTS COMPLETE")
    print("="*70)


if __name__ == "__main__":
    test_all_loaders()
