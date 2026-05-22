from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class Leader:
    """
    Leader card with signet ability.

    Signet abilities are triggered when Signet Ring is revealed.
    """
    name: str
    leader_id: int = 0
    signet_ability: Optional[Dict[str, Any]] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'Leader':
        """
        Create Leader from JSON data.

        Args:
            data: Leader dict from leaders.JSON

        Returns:
            Leader instance
        """
        return cls(
            name=data['name'],
            leader_id=data.get('id', 0),
            signet_ability=data.get('signet_ability')
        )


# Specific leader classes (for future expansion)
class FeydRautha(Leader):
    """Feyd Rautha Harkonnen - Combat focused"""
    def __init__(self):
        super().__init__(
            name="Feyd Rautha Harkonnen",
            leader_id=1,
            signet_ability={
                "type": "combat",
                "description": "+1 sword when you reveal",
                "effects": [{"type": "resource", "resource": "sword", "amount": 1}]
            }
        )