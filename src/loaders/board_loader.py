"""Board loaders - convert JSON data to Board element objects."""

import json
from pathlib import Path
from typing import List

from ..models.boardspace import BoardSpace, ObservationPost


def _get_data_path(filename: str) -> Path:
    """Get path to data file."""
    return Path(__file__).parent.parent.parent / "data" / filename


def load_board_spaces() -> List[BoardSpace]:
    """Load all board spaces."""
    file_path = _get_data_path("spaces.JSON")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle both formats: array at root or dict with 'spaces' key
    if isinstance(data, list):
        space_list = data
    else:
        space_list = data.get('spaces', data)

    spaces = []
    for space_data in space_list:
        # Handle both old and new format
        space = BoardSpace(
            id=space_data['id'],
            name=space_data['name'],
            agent_icon=space_data['agent_icon'],
            faction=space_data.get('faction'),
            cost=space_data.get('cost', {}),
            required_influence=space_data.get('required_influence'),
            check=space_data.get('check'),  # New JSON format for requirements
            # 'reward' in new format, 'effects' in old format
            effects=space_data.get('reward', space_data.get('effects', {})),
            # 'combat_space' in new format, 'is_combat_space' in old format
            is_combat_space=space_data.get('combat_space', space_data.get('is_combat_space', False)),
            # 'maker' in new format, 'is_maker_space' in old format
            is_maker_space=space_data.get('maker', space_data.get('is_maker_space', False)),
            spice_bonus=space_data.get('spice_bonus', 0),
            is_critical_location=space_data.get('is_critical_location', False),
            control_bonus=space_data.get('control_bonus', {})
        )
        spaces.append(space)

    return spaces


def load_observation_posts() -> List[ObservationPost]:
    """Load all observation posts for spy network."""
    file_path = _get_data_path("observation_posts.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = []
    for post_data in data:
        post = ObservationPost(
            id=str(post_data['id']),
            name=post_data['name'],
            connected_locations=post_data.get('controlled_spaces', post_data.get('connected_locations', []))
        )
        posts.append(post)

    return posts
