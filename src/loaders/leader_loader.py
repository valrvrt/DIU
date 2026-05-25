"""
Leader Loader

Loads leader data from data/leader_data/*.json and creates Leader objects.
"""

import json
from pathlib import Path
from typing import List, Optional
from ..models.leader import (
    Leader, FeydRautha, GurneyHalleck, LadyAmberMetulli, LadyJessica,
    PrincessIrulan, ShadhamCorrinoIV, StabanTuek, LadyMargotFenring, MuadDib
)


# Mapping of leader IDs to custom classes
LEADER_CLASSES = {
    1: FeydRautha,
    2: GurneyHalleck,
    3: LadyAmberMetulli,
    4: LadyJessica,
    5: LadyMargotFenring,
    6: MuadDib,
    7: PrincessIrulan,
    8: ShadhamCorrinoIV,
    9: StabanTuek,
}


def load_leaders(data_dir: Optional[str] = None) -> List[Leader]:
    """
    Load all leaders from individual JSON files in data/leader_data/.

    Args:
        data_dir: Path to leader_data directory (defaults to data/leader_data)

    Returns:
        List of Leader objects
    """
    if data_dir is None:
        # Default path
        current_dir = Path(__file__).parent.parent.parent
        data_dir = current_dir / "data" / "leader_data"
    else:
        data_dir = Path(data_dir)

    leaders = []

    # Find all JSON files in the directory
    json_files = sorted(data_dir.glob("*.json"))

    for json_file in json_files:
        # Skip reverendmother.json - it's only accessed via Lady Jessica's transformation
        if json_file.name == 'reverendmother.json':
            continue

        with open(json_file, 'r') as f:
            data = json.load(f)

        leader_id = data.get('id')
        leader_name = data.get('name')

        if leader_id is None or leader_name is None:
            print(f"Warning: Skipping {json_file.name} - missing id or name field")
            continue

        # Check if we have a custom class for this leader
        if leader_id in LEADER_CLASSES:
            leader_class = LEADER_CLASSES[leader_id]
            leader = leader_class()
        else:
            # Use basic Leader class for leaders without custom implementation
            leader = Leader.from_json(data)

        leaders.append(leader)

    # Sort by leader ID for consistent ordering
    leaders.sort(key=lambda l: l.leader_id)

    return leaders


def get_leader_by_name(name: str, leaders: Optional[List[Leader]] = None) -> Optional[Leader]:
    """
    Get a specific leader by name.

    Args:
        name: Leader name
        leaders: List of leaders (loads from files if None)

    Returns:
        Leader object or None if not found
    """
    if leaders is None:
        leaders = load_leaders()

    for leader in leaders:
        if leader.name.lower() == name.lower():
            return leader

    return None


def get_leader_by_id(leader_id: int, leaders: Optional[List[Leader]] = None) -> Optional[Leader]:
    """
    Get a specific leader by ID.

    Args:
        leader_id: Leader ID
        leaders: List of leaders (loads from files if None)

    Returns:
        Leader object or None if not found
    """
    if leaders is None:
        leaders = load_leaders()

    for leader in leaders:
        if leader.leader_id == leader_id:
            return leader

    return None
