"""
Leader Loader

Loads leader data from leaders.JSON and creates Leader objects.
"""

import json
from pathlib import Path
from typing import List, Optional
from ..models.leader import Leader


def load_leaders(json_path: Optional[str] = None) -> List[Leader]:
    """
    Load all leaders from JSON file.

    Args:
        json_path: Path to leaders.JSON (defaults to data/leaders.JSON)

    Returns:
        List of Leader objects
    """
    if json_path is None:
        # Default path
        current_dir = Path(__file__).parent.parent.parent
        json_path = current_dir / "data" / "leaders.JSON"

    with open(json_path, 'r') as f:
        leaders_data = json.load(f)

    leaders = []
    for data in leaders_data:
        leader = Leader.from_json(data)
        leaders.append(leader)

    return leaders


def get_leader_by_name(name: str, leaders: Optional[List[Leader]] = None) -> Optional[Leader]:
    """
    Get a specific leader by name.

    Args:
        name: Leader name
        leaders: List of leaders (loads from file if None)

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
        leaders: List of leaders (loads from file if None)

    Returns:
        Leader object or None if not found
    """
    if leaders is None:
        leaders = load_leaders()

    for leader in leaders:
        if leader.leader_id == leader_id:
            return leader

    return None
