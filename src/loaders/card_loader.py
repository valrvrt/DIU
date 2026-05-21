"""Card loaders - convert JSON data to Card objects."""

import json
from pathlib import Path
from typing import List, Optional

from ..models.card import (
    ImperiumCard, IntrigueCard, ConflictCard,
    ContractCard, LeaderCard, ObjectiveCard, CardType, IntriguePhase
)


def _get_data_path(filename: str) -> Path:
    """Get path to data file."""
    return Path(__file__).parent.parent.parent / "data" / filename


def load_starter_deck() -> List[ImperiumCard]:
    """Load the 10 starter cards every player begins with."""
    file_path = _get_data_path("imperium.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data:
        # Only load cards marked as starting deck
        if not card_data.get('starting_deck', False):
            continue

        # Get the amount (how many copies of this card in starter deck)
        amount = card_data.get('amount')

        for _ in range(amount):
            for i in range(amount):
                card = ImperiumCard(
                    id=str(card_data['id']),
                    name=card_data['name'],
                    card_type=CardType.IMPERIUM,
                    type="Imperium",
                    factions=card_data.get('factions', []),
                    starting_hand=True,
                    cost=0,  # Starter cards are free
                    on_acquire_effects=[],
                    agent_icons=card_data.get('agent_icon', []),
                    agent_effects=card_data.get('agent_effects', []),
                    reveal_effects=card_data.get('reveal_effects', [])
                )
                cards.append(card)

    return cards


def load_imperium_cards() -> List[ImperiumCard]:
    """Load all Imperium cards for the market (excluding starter cards)."""
    file_path = _get_data_path("imperium.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data:
        # Skip starter deck cards
        if card_data.get('starting_deck', False):
            continue

        # Get the quantity (how many copies of this card in the market deck)
        quantity = card_data.get('quantity', card_data.get('amount', 1))

        for _ in range(quantity):
            card = ImperiumCard(
                id=str(card_data['id']),
                name=card_data['name'],
                card_type=CardType.IMPERIUM,
                type=card_data.get('type', 'Imperium'),
                factions=card_data.get('faction', []) if isinstance(card_data.get('faction'), list) else ([card_data.get('faction')] if card_data.get('faction') else []),
                starting_hand=False,
                cost=card_data.get('cost', 0),
                on_acquire_effects=card_data.get('on_acquire_effects', []),
                agent_icons=card_data.get('agent_icon', []) if isinstance(card_data.get('agent_icon'), list) else [card_data.get('agent_icon')] if card_data.get('agent_icon') else [],
                agent_effects=card_data.get('agent_effects', []),
                reveal_effects=card_data.get('reveal_effects', card_data.get('reward', []))
            )
            cards.append(card)

    return cards


def load_intrigue_cards() -> List[IntrigueCard]:
    """Load all Intrigue cards."""
    file_path = _get_data_path("intrigue.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['intrigues']:
        # Extract phases from effects if available
        phases = []
        effects = card_data.get('effects', [])

        # Try to infer phases from effect structure
        for effect in effects if isinstance(effects, list) else []:
            if isinstance(effect, dict):
                phase_str = effect.get('phase', '')
                if phase_str == "plot":
                    phases.append(IntriguePhase.PLOT)
                elif phase_str == "combat":
                    phases.append(IntriguePhase.COMBAT)
                elif phase_str == "endgame" or phase_str == "end_game":
                    phases.append(IntriguePhase.END_GAME)

        card = IntrigueCard(
            id=str(card_data['id']),
            name=card_data['name'],
            card_type=CardType.INTRIGUE,
            type="Intrigue",  # Default type
            phases=phases if phases else [IntriguePhase.PLOT],  # Default to PLOT if no phase found
            cost=[],
            played_gain=card_data.get('effects', []),
            conditional_gain=[]
        )
        cards.append(card)

    return cards


def load_conflict_cards() -> List[ConflictCard]:
    """Load all Conflict cards."""
    file_path = _get_data_path("conflicts.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data['conflicts']:
        card = ConflictCard(
            id=str(card_data['id']),
            name=card_data['name'],
            card_type=CardType.CONFLICT,
            type=card_data.get('type', 'conflict'),  # Default type for conflicts
            level=card_data.get('level', 1),  # Conflict level (1, 2, or 3)
            tag=card_data.get('tag', ''),  # Tag for objectives
            rewards=card_data.get('rewards', {}),  # Dict mapping rank to effects
            location=card_data.get('location'),
            battle_icon=card_data.get('battle_icon'),
            wall=card_data.get('shieldwall', False)  # Fixed: use 'shieldwall' key
        )
        cards.append(card)

    return cards


def load_contract_cards() -> List[ContractCard]:
    """Load all Contract cards (CHOAM module)."""
    file_path = _get_data_path("contracts.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cards = []
    for card_data in data:
        # Extract completion type from check field
        check = card_data.get('check', [{}])[0] if card_data.get('check') else {}
        check_type = check.get('type', 'always')

        # Map check types to completion types
        completion_type_map = {
            'bought': 'acquire_card',
            'agent_on': 'location',
            'harvest': 'harvest',
            'always': 'immediate'
        }

        completion_type = completion_type_map.get(check_type, 'immediate')
        completion_target = check.get('location') or check.get('card')

        card = ContractCard(
            id=str(card_data['id']),
            name=f"Contract #{card_data['id']}",  # Generate name from ID
            card_type=CardType.CONTRACT,
            type="Contract",
            completion_type=completion_type,
            completion_target=completion_target,
            required_spice=check.get('amount', 0) if check_type == 'harvest' else 0,
            rewards=card_data.get('reward', [])
        )
        cards.append(card)

    return cards


def load_leaders() -> List[LeaderCard]:
    """Load all Leader cards."""
    file_path = _get_data_path("leaders.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    leaders = []
    for leader_data in data:
        signet_ability = leader_data.get('signet_ability', {})

        leader = LeaderCard(
            id=str(leader_data['id']),
            name=leader_data['name'],
            card_type=CardType.LEADER,
            type="Leader",
            ring=signet_ability.get('effects', []),
            passive_condition=[],
            passive_gain=[]
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