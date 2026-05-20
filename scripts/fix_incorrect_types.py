"""
Fix incorrectly converted effect types from previous standardization run.

Changes:
- {"type": "resource", "resource": "draw", "amount": 1}
  → {"type": "draw", "deck": "deck", "amount": 1}

- {"type": "resource", "resource": "influence_choice", "amount": 1}
  → {"type": "influence", "target": "any", "amount": 1, "times": 1}
"""

import json
from pathlib import Path


def fix_effects_in_list(effects):
    """Recursively fix effect types in a list."""
    if not isinstance(effects, list):
        return effects

    fixed_effects = []
    for effect in effects:
        if not isinstance(effect, dict):
            fixed_effects.append(effect)
            continue

        # Fix draw effects
        if effect.get("type") == "resource" and effect.get("resource") == "draw":
            fixed_effects.append({
                "type": "draw",
                "deck": "deck",
                "amount": effect.get("amount", 1)
            })

        # Fix influence_choice effects
        elif effect.get("type") == "resource" and effect.get("resource") == "influence_choice":
            fixed_effects.append({
                "type": "influence",
                "target": "any",
                "amount": effect.get("amount", 1),
                "times": 1
            })

        # Fix other special resources that should have different types
        elif effect.get("type") == "resource" and effect.get("resource") in [
            "intrigue_card", "place_spy", "recruit_troops", "signet_ring_ability"
        ]:
            # These are actually fine as resources for now
            fixed_effects.append(effect)

        else:
            # Keep as-is
            fixed_effects.append(effect)

    return fixed_effects


def fix_card_file(file_path: Path) -> bool:
    """Fix effect types in a JSON file."""
    print(f"\n📄 Processing: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    # Handle different structures
    if "cards" in data:
        cards = data["cards"]
    elif "contracts" in data:
        cards = data["contracts"]
    elif isinstance(data, list):
        cards = data
    else:
        print(f"  ⚠️  Unknown structure")
        return False

    for card in cards:
        card_name = card.get("name", card.get("id", "?"))

        # Check all effect fields
        for field in ["agent_effects", "reveal_effects", "on_acquire_effects", "rewards", "reward"]:
            if field in card and isinstance(card[field], list):
                old_effects = card[field]
                new_effects = fix_effects_in_list(old_effects)

                if old_effects != new_effects:
                    card[field] = new_effects
                    modified = True
                    print(f"  ✓ Fixed {field} in '{card_name}'")

    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 Saved")
    else:
        print(f"  ✓ No fixes needed")

    return modified


def main():
    """Fix all incorrectly converted files."""
    print("="*70)
    print("FIX INCORRECT EFFECT TYPES")
    print("="*70)

    # Files that need fixing (identified by grep)
    files_to_fix = [
        "data/test_data/imperium_cards.json",
        "data/test_data/contract_cards.json",
        "data/test_data/starter_deck.json",
    ]

    total_fixed = 0
    for file_path in files_to_fix:
        path = Path(file_path)
        if path.exists():
            if fix_card_file(path):
                total_fixed += 1

    print("\n" + "="*70)
    print(f"SUMMARY: {total_fixed} files fixed")
    print("="*70)


if __name__ == "__main__":
    main()
