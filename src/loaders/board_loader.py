"""Board loaders - convert JSON data to Board element objects."""

import json
from pathlib import Path
from typing import List

from ..models.boardspace import BoardSpace, ObservationPost


def _get_data_path(filename: str) -> Path:
    """Get path to test_data file."""
    return Path(__file__).parent.parent.parent / "data" / "test_data" / filename


def load_board_spaces() -> List[BoardSpace]:
    """Load all board spaces."""
    file_path = _get_data_path("board_spaces.json")

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    spaces = []
    for space_data in data['spaces']:
        space = BoardSpace(
            id=space_data['id'],
            name=space_data['name'],
            agent_icon=space_data['agent_icon'],
            faction=space_data.get('faction'),
            cost=space_data.get('cost', {}),
            required_influence=space_data.get('required_influence'),
            effects=space_data.get('effects', {}),
            is_combat_space=space_data.get('is_combat_space', False),
            is_maker_space=space_data.get('is_maker_space', False),
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
    for post_data in data['observation_posts']:
        post = ObservationPost(
            id=post_data['id'],
            name=post_data['name'],
            connected_locations=post_data.get('connected_locations', [])
        )
        posts.append(post)

    return posts
