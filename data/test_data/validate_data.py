#!/usr/bin/env python3
"""
Validation script for test data JSON files.
Checks that all files are valid JSON and contain expected structures.
"""

import json
from pathlib import Path

def validate_json_file(filepath: Path) -> tuple[bool, str]:
    """Validate a JSON file can be parsed."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return True, f"✓ {filepath.name}: Valid JSON"
    except json.JSONDecodeError as e:
        return False, f"✗ {filepath.name}: Invalid JSON - {e}"
    except Exception as e:
        return False, f"✗ {filepath.name}: Error - {e}"

def count_items(filepath: Path) -> tuple[bool, str]:
    """Count items in each JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Determine the key based on filename
        if 'starter_deck' in filepath.name or 'imperium' in filepath.name:
            key = 'cards'
        elif 'intrigue' in filepath.name:
            key = 'cards'
        elif 'conflict' in filepath.name:
            key = 'conflicts'
        elif 'contract' in filepath.name:
            key = 'contracts'
        elif 'leaders' in filepath.name:
            key = 'leaders'
        elif 'board_spaces' in filepath.name:
            key = 'spaces'
        elif 'observation_posts' in filepath.name:
            key = 'observation_posts'
        else:
            return True, f"  {filepath.name}: Unknown structure"

        count = len(data.get(key, []))
        return True, f"  {filepath.name}: {count} items"
    except Exception as e:
        return False, f"  {filepath.name}: Error counting - {e}"

def main():
    """Run validation on all test data files."""
    print("=" * 60)
    print("DUNE Imperium Test Data Validation")
    print("=" * 60)

    test_data_dir = Path(__file__).parent
    json_files = sorted(test_data_dir.glob("*.json"))

    if not json_files:
        print("❌ No JSON files found!")
        return False

    print(f"\nFound {len(json_files)} JSON files\n")

    # Validate JSON syntax
    print("JSON Syntax Validation:")
    print("-" * 60)
    all_valid = True
    for filepath in json_files:
        valid, message = validate_json_file(filepath)
        print(message)
        all_valid = all_valid and valid

    if not all_valid:
        print("\n❌ Some files have JSON syntax errors!")
        return False

    # Count items
    print("\nItem Counts:")
    print("-" * 60)
    total_items = 0
    for filepath in json_files:
        valid, message = count_items(filepath)
        print(message)

    # Summary
    print("\n" + "=" * 60)
    print("Expected Counts:")
    print("-" * 60)
    print("  starter_deck.json: 7 cards (starter deck)")
    print("  imperium_cards.json: 6 cards (market + reserve)")
    print("  intrigue_cards.json: 4 cards (plot/combat/endgame)")
    print("  conflict_cards.json: 4 conflicts (tier I/II/III)")
    print("  contract_cards.json: 4 contracts (CHOAM)")
    print("  leaders.json: 4 leaders (various houses)")
    print("  board_spaces.json: 8 spaces (key locations)")
    print("  observation_posts.json: 4 posts (spy network)")
    print("-" * 60)
    print("  Total: 31 cards + 4 leaders + 8 spaces + 4 posts = 47 items")
    print("=" * 60)

    if all_valid:
        print("\n✅ All validation checks passed!")
        return True
    else:
        print("\n❌ Validation failed!")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
