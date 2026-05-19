"""Card loaders - convert JSON data to Card objects."""

import json
from pathlib import Path
from typing import List, Optional

from ..models.card import (
    ImperiumCard, IntrigueCard, ConflictCard,
    ContractCard, LeaderCard, ObjectiveCard, CardType, IntriguePhase
)


def _get_data_path(filename: str) -> Path:
    """Get path to test_data file."""
    return Path(__file__).parent.parent.parent / "data" / "test_data" / filename


def load_starter_deck() -> List[ImperiumCard]:
    """Load the 7 starter cards every player begins with."""
    file_path = _get_data_path("starter_deck.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['cards']:
        card = ImperiumCard(
            id=card_data['id'],
            name=card_data['name'],
            card_type=CardType.IMPERIUM,
            type=card_data['type'],
            factions=card_data.get('factions', []),
            starting_hand=card_data.get('starting_hand', False),
            cost=card_data['cost'],
            on_acquire_effects=card_data.get('on_acquire_effects', {}),
            agent_icons=card_data.get('agent_icons', []),
            agent_effects=card_data.get('agent_effects', {}),
            reveal_effects=card_data.get('reveal_effects', {})
        )
        cards.append(card)

    return cards


def load_imperium_cards() -> List[ImperiumCard]:
    """Load all Imperium cards for the market."""
    file_path = _get_data_path("imperium_cards.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['cards']:
        card = ImperiumCard(
            id=card_data['id'],
            name=card_data['name'],
            card_type=CardType.IMPERIUM,
            type=card_data['type'],
            factions=card_data.get('factions', []),
            starting_hand=card_data.get('starting_hand', False),
            cost=card_data['cost'],
            on_acquire_effects=card_data.get('on_acquire_effects', {}),
            agent_icons=card_data.get('agent_icons', []),
            agent_effects=card_data.get('agent_effects', {}),
            reveal_effects=card_data.get('reveal_effects', {})
        )
        cards.append(card)

    return cards


def load_intrigue_cards() -> List[IntrigueCard]:
    """Load all Intrigue cards."""
    file_path = _get_data_path("intrigue_cards.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['cards']:
        # Convert phase strings to IntriguePhase enum values
        phases = []
        for phase_str in card_data.get('phases', []):
            if phase_str == "Plot":
                phases.append(IntriguePhase.PLOT)
            elif phase_str == "Combat":
                phases.append(IntriguePhase.COMBAT)
            elif phase_str == "End_Game":
                phases.append(IntriguePhase.END_GAME)

        card = IntrigueCard(
            id=card_data['id'],
            name=card_data['name'],
            card_type=CardType.INTRIGUE,
            type=card_data['type'],
            phases=phases,
            cost=card_data.get('cost', {}),
            played_gain=card_data.get('effects', {}),
            conditional_gain=card_data.get('conditions', {})
        )
        cards.append(card)

    return cards


def load_conflict_cards() -> List[ConflictCard]:
    """Load all Conflict cards."""
    file_path = _get_data_path("conflict_cards.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['conflicts']:
        card = ConflictCard(
            id=card_data['id'],
            name=card_data['name'],
            card_type=CardType.CONFLICT,
            type=card_data['type'],
            level=card_data.get('level', 1),  # Conflict level (1, 2, or 3)
            tag=card_data.get('tag', ''),  # Tag for objectives
            rewards=card_data.get('rewards', []),
            location=card_data.get('location'),
            battle_icon=card_data.get('battle_icon'),
            wall=card_data.get('has_shield', False)
        )
        cards.append(card)

    return cards


def load_contract_cards() -> List[ContractCard]:
    """Load all Contract cards (CHOAM module)."""
    file_path = _get_data_path("contract_cards.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['contracts']:
        card = ContractCard(
            id=card_data['id'],
            name=card_data['name'],
            card_type=CardType.CONTRACT,
            type=card_data['type'],
            completion_type=card_data['completion_type'],
            completion_target=card_data.get('completion_target'),
            required_spice=card_data.get('required_spice', 0),
            rewards=card_data.get('rewards', {})
        )
        cards.append(card)

    return cards


def load_leaders() -> List[LeaderCard]:
    """Load all Leader cards."""
    file_path = _get_data_path("leaders.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    leaders = []
    for leader_data in data['leaders']:
        leader = LeaderCard(
            id=leader_data['id'],
            name=leader_data['name'],
            card_type=CardType.LEADER,
            type=leader_data['type'],
            ring=leader_data.get('signet_ring_ability', {}).get('effects', {}),
            passive_condition=leader_data.get('passive_ability', {}).get('condition', {}),
            passive_gain=leader_data.get('passive_ability', {}).get('effects', {})
        )
        leaders.append(leader)

    return leaders


def get_leader_by_id(leader_id: str) -> Optional[LeaderCard]:
    """Get a specific leader by ID."""
    leaders = load_leaders()
    for leader in leaders:
        if leader.id == leader_id:
            return leader
    return None


def get_reserve_cards() -> dict[str, List[ImperiumCard]]:
    """
    Separate Reserve cards from regular Imperium cards.

    Returns:
        Dict with 'prepare_the_way' and 'spice_must_flow' lists
    """
    imperium_cards = load_imperium_cards()

    reserve = {
        'prepare_the_way': [],
        'spice_must_flow': []
    }

    for card in imperium_cards:
        if 'prepare' in card.id.lower():
            reserve['prepare_the_way'].append(card)
        elif 'spice_must_flow' in card.id.lower():
            reserve['spice_must_flow'].append(card)

    return reserve


def load_objectives() -> List[ObjectiveCard]:
    """Load objective cards from objectives.JSON."""
    # Objectives are in data/ not data/test_data/
    objectives_path = Path(__file__).parent.parent.parent / "data" / "objectives.JSON"

    with open(objectives_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    objectives = []
    for obj_data in data:
        objective = ObjectiveCard(
            id=obj_data["id"],
            name=obj_data["name"],
            tag=obj_data["tag"],
            n_players=obj_data["n_players"]
        )
        objectives.append(objective)

    return objectives


def get_objectives_for_player_count(player_count: int) -> List[ObjectiveCard]:
    """
    Get objectives valid for given player count.

    Args:
        player_count: Number of players in game (2, 3, or 4)

    Returns:
        List of objective cards valid for this player count
    """
    objectives = load_objectives()
    valid = [obj for obj in objectives if player_count in obj.n_players]
    return valid