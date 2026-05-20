"""
Unify ALL JSON files to match the exact format of conflict_cards.json and contract_cards.json.

Rules from the template files:
1. Empty effects MUST be [] (empty arrays), NEVER {}
2. Draw effects: {"type": "draw", "deck": "deck"|"intrigue"|"contract", "amount": N}
3. Influence effects: {"type": "influence", "target": "faction"|"any", "amount": N, "times": N}
4. Resource effects: {"type": "resource", "resource": "name", "amount": N}
5. All effect lists are arrays, even if empty
"""

import json
from pathlib import Path
from typing import Any, Dict, List


def fix_empty_effects(obj: Any) -> Any:
    """Recursively convert empty objects {} to empty arrays [] for effect fields."""
    if isinstance(obj, dict):
        fixed = {}
        for key, value in obj.items():
            # Effect fields that should always be arrays
            if key in ["agent_effects", "reveal_effects", "on_acquire_effects", "rewards", "reward", "cost", "check"]:
                if value == {} or value is None:
                    fixed[key] = []
                elif isinstance(value, dict) and not any(k in ["1", "2", "3", "base"] for k in value.keys()):
                    # Dict but not a ranking dict or base dict - convert to array
                    fixed[key] = []
                else:
                    fixed[key] = fix_empty_effects(value)
            else:
                fixed[key] = fix_empty_effects(value)
        return fixed
    elif isinstance(obj, list):
        return [fix_empty_effects(item) for item in obj]
    else:
        return obj


def process_json_file(file_path: Path) -> bool:
    """Process a JSON file and fix all formatting issues."""
    print(f"\n📄 Processing: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"  ❌ JSON error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

    # Fix empty effects
    fixed_data = fix_empty_effects(data)

    # Check if anything changed
    if json.dumps(data, sort_keys=True) == json.dumps(fixed_data, sort_keys=True):
        print(f"  ✓ Already correct")
        return False

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(fixed_data, f, indent=2, ensure_ascii=False)

    print(f"  💾 Fixed and saved")
    return True


def main():
    """Fix all JSON files in data/ directory."""
    print("="*70)
    print("UNIFY ALL JSON FORMATS")
    print("="*70)
    print("\nFixing all JSON files to match conflict_cards.json template:")
    print("  - Empty effects: [] (not {})")
    print("  - Consistent effect formats throughout")
    print()

    data_dir = Path("data")

    # Find all JSON files
    json_files = list(data_dir.rglob("*.json")) + list(data_dir.rglob("*.JSON"))

    # Skip objectives and faction_bonus (empty file)
    json_files = [
        f for f in json_files
        if "objectives" not in f.name.lower() and "faction_bonus" not in f.name.lower()
    ]

    print(f"Found {len(json_files)} JSON files to process\n")

    total_fixed = 0

    for json_file in sorted(json_files):
        if process_json_file(json_file):
            total_fixed += 1

    print("\n" + "="*70)
    print(f"SUMMARY: {total_fixed} files fixed")
    print("="*70)


if __name__ == "__main__":
    main()
