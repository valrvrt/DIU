from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

@dataclass
class Leader:
    """
    Leader card with signet ability and passive ability.

    Signet abilities are triggered when Signet Ring is revealed.
    Some leaders have progressive signet abilities that unlock as they advance on the training track.
    Some leaders have passive abilities that can be activated during specific phases.
    """
    name: str
    leader_id: int = 0
    signet_ability: Optional[Dict[str, Any]] = None  # Simple signet (old format)
    signet_progression: Optional[List[Dict[str, Any]]] = None  # Progressive signet (new format)
    passive_ability: Optional[Dict[str, Any]] = None
    training_track_position: int = 0  # Current position on training track (0-4)

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> 'Leader':
        """
        Create Leader from JSON data.

        Args:
            data: Leader dict from leaders.JSON (old format)
                  OR from leader_data/*.json (new format)

        Returns:
            Leader instance
        """
        return cls(
            name=data.get('name', 'Unknown'),
            leader_id=data.get('id', 0),
            signet_ability=data.get('signet_ability'),
            signet_progression=data.get('signet'),  # New format
            passive_ability=data.get('passive'),
            training_track_position=0
        )

    def get_current_signet_effects(self) -> List[Dict[str, Any]]:
        """
        Get the current signet ability effects based on training track position.

        Returns:
            List of effects for current signet level
        """
        # Old format (simple signet_ability)
        if self.signet_ability and 'effects' in self.signet_ability:
            return self.signet_ability['effects']

        # New format (progressive signet)
        if self.signet_progression:
            # Find the highest unlocked level based on training track position
            available_levels = [
                level for level in self.signet_progression
                if level.get('id', 0) <= self.training_track_position + 1  # +1 because track starts at 0 but levels start at 1
            ]

            if available_levels:
                # Use the highest available level
                current_level = max(available_levels, key=lambda x: x.get('id', 0))

                # If it's a choice, return the choice structure
                if current_level.get('type') == 'choice':
                    return [current_level]

                # If it has a reward field, use that
                if 'reward' in current_level:
                    return current_level['reward']

                # Otherwise, the level itself IS the effect (like level 2: {"id": 2, "type": "trash", ...})
                # Return it as a single-element list
                return [current_level]

        return []

    def can_use_passive(self, phase: str) -> bool:
        """
        Check if passive ability can be used in this phase.

        Args:
            phase: Current game phase

        Returns:
            True if passive can be used
        """
        if not self.passive_ability:
            return False

        passive_phase = self.passive_ability.get('phase', '')
        return passive_phase == phase

    def advance_training_track(self):
        """Move forward one space on the training track."""
        if self.training_track_position < 4:
            self.training_track_position += 1


# Specific leader classes with custom signet implementations
class FeydRautha(Leader):
    """
    Feyd Rautha Harkonnen - Devious Combat Leader

    Progressive Signet Ability (unlocks with training track):
    - Level 1 (pos 0): Choice - Pay 1 solari to trash OR place spy
    - Level 2 (pos 1): Trash a card
    - Level 3 (pos 2): Choice - Trash (go to level 4) OR place spy (go to level 3.1)
    - Level 3.1 (pos 3, only if spy chosen): Gain 2 spice
    - Level 4 (pos 4 or pos 3 if trash chosen): (Repeatable) Gain 1 troop + place spy

    Passive Ability (Devious Strength):
    - Phase: Reveal
    - Cost: Recall 1 spy
    - Reward: +2 swords
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "feydrautha.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Feyd Rautha Harkonnen",
            leader_id=1,
            signet_progression=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track which path was taken at level 3 choice
        # None = not yet reached level 3
        # "trash" = took trash option (skip level 3.1, go straight to level 4)
        # "spy" = took spy option (go through level 3.1 first)
        self.level_3_choice = None

    def get_current_signet_effects(self) -> List[Dict[str, Any]]:
        """
        Get current signet effects for Feyd Rautha, handling branching progression.

        Progression:
        - Position 0: Level 1 (choice: trash for 1 solari OR spy)
        - Position 1: Level 2 (trash)
        - Position 2: Level 3 (choice: trash → skip to level 4, OR spy → level 3.1)
        - Position 3: Level 3.1 (gain 2 spice) if spy was chosen, OR Level 4 if trash was chosen
        - Position 4: Level 4 (repeatable: troop + spy)
        """
        if not self.signet_progression:
            return []

        level = None

        # Position 0 → Level 1
        if self.training_track_position == 0:
            level = next((l for l in self.signet_progression if l.get('id') == 1), None)

        # Position 1 → Level 2
        elif self.training_track_position == 1:
            level = next((l for l in self.signet_progression if l.get('id') == 2), None)

        # Position 2 → Level 3 (choice)
        elif self.training_track_position == 2:
            level = next((l for l in self.signet_progression if l.get('id') == 3), None)

        # Position 3 → Depends on level 3 choice
        elif self.training_track_position == 3:
            if self.level_3_choice == "trash":
                # Trash option → go straight to level 4
                level = next((l for l in self.signet_progression if l.get('id') == 4), None)
            else:
                # Spy option (or not yet chosen) → level 3.1
                level = next((l for l in self.signet_progression if l.get('id') == 3.1), None)

        # Position 4 → Level 4 (repeatable)
        elif self.training_track_position >= 4:
            level = next((l for l in self.signet_progression if l.get('id') == 4), None)

        if not level:
            return []

        # Extract effects from level (following base class pattern)
        # If it's a choice, return the choice structure
        if level.get('type') == 'choice':
            return [level]

        # If it has a reward field, return the rewards
        if 'reward' in level:
            return level['reward']

        # Otherwise, the level itself IS the effect
        return [level]

    def signet_ring(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute Feyd Rautha's signet ring ability.

        This method is called when Signet Ring is revealed.
        Uses JSON data for progressive abilities based on training track position.

        Args:
            game_state: Current game state
            player_id: Player using signet
            context: Resolution context

        Returns:
            Result dict with effects to resolve
        """
        # Get current level effects from JSON
        effects = self.get_current_signet_effects()

        if not effects:
            return {
                "success": True,
                "effects": [],
                "message": f"No signet ability unlocked at training position {self.training_track_position}"
            }

        # Return effects to be resolved by effect resolver
        return {
            "success": True,
            "effects": effects,
            "message": f"Feyd Rautha signet (Level {self.training_track_position + 1})"
        }

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Attempt to use Devious Strength passive ability.

        Cost: Recall 1 spy
        Reward: +2 swords

        Args:
            game_state: Current game state
            player_id: Player using passive
            context: Resolution context

        Returns:
            Result dict
        """
        if not self.can_use_passive(context.get('phase', '')):
            return {
                "success": False,
                "error": "Passive can only be used during reveal phase"
            }

        player = game_state.get_player_by_id(player_id)

        # Check if player has a spy to recall
        if not hasattr(player, 'spies_placed') or not player.spies_placed:
            return {
                "success": False,
                "error": "No spies to recall"
            }

        # Cost is handled separately (player must choose to pay it)
        # This just returns the passive effects
        return {
            "success": True,
            "cost": self.passive_ability.get('cost', []),
            "effects": self.passive_ability.get('reward', []),
            "message": "Devious Strength: Recall spy for +2 swords"
        }