"""
Standardize all JSON files to use consistent effect format.

Converts simplified formats like {"persuasion": 2} to proper effect lists with correct types:
- {"draw": 1} → [{"type": "draw", "deck": "deck", "amount": 1}]
- {"influence_choice": 1} → [{"type": "influence", "target": "any", "amount": 1}]
- {"persuasion": 2} → [{"type": "resource", "resource": "persuasion", "amount": 2}]
"""

import json
from pathlib import Path
from typing import Any, Dict, List


# Special effect types that are NOT resources
SPECIAL_EFFECT_MAPPINGS = {
    # Draw effects
    "draw": {"type": "draw", "deck": "deck"},
    "draw_intrigue": {"type": "draw", "deck": "intrigue"},
    "draw_contract": {"type": "accept", "deck": "contract"},

    # Influence effects
    "influence_choice": {"type": "influence", "target": "any", "times": 1},
    "influence_any": {"type": "influence", "target": "any", "times": 1},
    "influence": {"type": "influence", "target": "any", "times": 1},

    # Trash effects
    "trash": {"type": "trash", "deck": ["hand", "played"]},

    # Special abilities
    "signet_ring_ability": {"type": "resource", "resource": "signet_ring_ability"},
    "place_spy": {"type": "resource", "resource": "place_spy"},
    "recruit_troops": {"type": "resource", "resource": "recruit_troops"},
    "council_seat": {"type": "council_seat"},
    "maker_hooks": {"type": "maker_hooks"},
    "shieldwall_deactivate": {"type": "shieldwall_deactivate"},
}


def convert_simplified_to_standard(effects: Any) -> List[Dict[str, Any]]:
    """
    Convert simplified effect format to standard format with correct types.

    Input formats handled:
    1. Already standard: [{"type": "resource", "resource": "solari", "amount": 2}]
    2. Simplified dict: {"solari": 2, "water": 1, "draw": 1}
    3. Nested base: {"base": {"solari": 2}}
    4. Empty: {} or []

    Output: Standard list format with correct type discrimination
    """
    # Already a list (standard format)
    if isinstance(effects, list):
        return effects

    # Empty dict
    if not effects or effects == {}:
        return []

    # Dict format - could be simplified or nested
    if isinstance(effects, dict):
        # Check for "base" key (nested format)
        if "base" in effects:
            base_effects = effects["base"]
            return convert_simplified_to_standard(base_effects)

        # Simplified format: {"persuasion": 2, "draw": 1, "influence_choice": 1}
        # Convert to standard list with type discrimination
        standard_effects = []
        for key, value in effects.items():
            if isinstance(value, int) or isinstance(value, bool):
                # Check if this is a special effect type
                if key in SPECIAL_EFFECT_MAPPINGS:
                    effect = SPECIAL_EFFECT_MAPPINGS[key].copy()
                    effect["amount"] = value
                    standard_effects.append(effect)
                else:
                    # Regular resource
                    standard_effects.append({
                        "type": "resource",
                        "resource": key,
                        "amount": value
                    })
            elif isinstance(value, dict):
                # Complex effect (already has type)
                standard_effects.append(value)

        return standard_effects

    return []


def process_card_file(file_path: Path) -> bool:
    """
    Process a card JSON file and standardize effect formats.

    Returns:
        True if file was modified, False otherwise
    """
    print(f"\n📄 Processing: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    modified = False

    # Handle different top-level structures
    cards_key = None
    if "cards" in data:
        cards_key = "cards"
    elif "conflicts" in data:
        cards_key = "conflicts"
    elif "contracts" in data:
        cards_key = "contracts"
    elif "leaders" in data:
        cards_key = "leaders"
    elif isinstance(data, list):
        # Direct list of cards
        cards = data
        cards_key = None
    else:
        print(f"  ⚠️  Unknown structure, skipping")
        return False

    cards = data[cards_key] if cards_key else data

    for i, card in enumerate(cards):
        card_name = card.get("name", card.get("id", f"card_{i}"))

        # Fields that might contain effects
        effect_fields = [
            "agent_effects",
            "reveal_effects",
            "on_acquire_effects",
            "reward",
            "rewards",
            "ring",
            "passive_gain"
        ]

        for field in effect_fields:
            if field in card and card[field]:
                old_value = card[field]
                new_value = convert_simplified_to_standard(old_value)

                # Only update if different
                if old_value != new_value:
                    card[field] = new_value
                    modified = True
                    print(f"  ✓ Standardized {field} in '{card_name}'")

    if modified:
        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"  💾 File saved with standardized format")
    else:
        print(f"  ✓ Already in standard format")

    return modified


def main():
    """Standardize all JSON files in data/ directory."""
    print("="*70)
    print("JSON STANDARDIZATION TOOL")
    print("="*70)
    print("\nConverting all effect formats to standard list format:")
    print("  Resources: [{'type': 'resource', 'resource': 'X', 'amount': N}]")
    print("  Draw: [{'type': 'draw', 'deck': 'deck', 'amount': N}]")
    print("  Influence: [{'type': 'influence', 'target': 'any', 'amount': N}]")
    print()

    data_dir = Path("data")

    # Find all JSON files
    json_files = list(data_dir.rglob("*.json")) + list(data_dir.rglob("*.JSON"))

    # Exclude objectives.JSON (no effects)
    json_files = [f for f in json_files if "objectives" not in f.name.lower()]

    print(f"Found {len(json_files)} JSON files to process\n")

    total_modified = 0

    for json_file in sorted(json_files):
        try:
            if process_card_file(json_file):
                total_modified += 1
        except Exception as e:
            print(f"  ❌ Error processing {json_file}: {e}")

    print("\n" + "="*70)
    print(f"SUMMARY: {total_modified} files modified")
    print("="*70)


if __name__ == "__main__":
    main()
