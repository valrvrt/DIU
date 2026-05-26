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

        The signet field in JSON can take 3 shapes:
        1. A dict — single effect (Gurney bare reward, Princess Irulan choice)
        2. A list of dicts WITH `id` fields — progressive signet (Feyd-Rautha)
        3. A list of dicts WITHOUT `id` fields — flat list, all entries fire together
           (Lady Jessica, Lady Amber Metulli, Mu'ad'Dib, Shaddam, Staban Tuek,
           Lady Margot Fenring)

        Returns:
            List of effects for current signet level
        """
        # Old format (simple signet_ability with 'effects' field)
        if self.signet_ability and isinstance(self.signet_ability, dict) and 'effects' in self.signet_ability:
            return self.signet_ability['effects']

        # Use signet_progression if set, otherwise fall back to signet_ability
        # (some custom leader subclasses store the JSON dict in signet_ability)
        sp = self.signet_progression if self.signet_progression else self.signet_ability
        if not sp:
            return []

        # Shape 1: dict
        if isinstance(sp, dict):
            # If it's a bare reward wrapper (Gurney: {"reward": [...]}), return rewards
            if 'reward' in sp and 'type' not in sp:
                return sp['reward']
            # Otherwise the dict itself is the effect (Princess Irulan's choice)
            return [sp]

        # Shape 2/3: list
        if isinstance(sp, list):
            has_progression_ids = any(
                isinstance(e, dict) and 'id' in e and not isinstance(e.get('id'), str)
                for e in sp
            )

            if not has_progression_ids:
                # Flat list — fire all entries together
                return sp

            # Progressive — pick highest unlocked level
            available_levels = [
                level for level in sp
                if level.get('id', 0) <= self.training_track_position + 1
            ]

            if available_levels:
                current_level = max(available_levels, key=lambda x: x.get('id', 0))

                if current_level.get('type') == 'choice':
                    return [current_level]

                if 'reward' in current_level:
                    return current_level['reward']

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


class GurneyHalleck(Leader):
    """
    Gurney Halleck - Combat Master

    Signet Ability:
    - +1 troop when you reveal

    Passive Ability (Always Smiling):
    - During reveal phase
    - If you have 6+ strength (swords)
    - Gain +1 persuasion
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "gurneyhalleck.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Gurney Halleck",
            leader_id=2,
            signet_ability={
                "type": "combat",
                "description": "+1 troop",
                "effects": data.get('signet', {}).get('reward', [])
            },
            passive_ability=data.get('passive'),
            training_track_position=0
        )

    def check_passive_condition(self, game_state, player_id: str) -> bool:
        """
        Check if passive ability condition is met (6+ strength).

        Args:
            game_state: Current game state
            player_id: Player ID

        Returns:
            True if condition met
        """
        player = game_state.get_player_by_id(player_id)
        if not player:
            return False

        # Check strength (swords)
        swords = getattr(player, 'temp_swords', 0)
        return swords >= 6

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Always Smiling passive ability.

        Automatically triggered if 6+ strength during reveal.
        Reward: +1 persuasion

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

        if not self.check_passive_condition(game_state, player_id):
            return {
                "success": False,
                "error": "Need 6+ strength to use Always Smiling"
            }

        return {
            "success": True,
            "effects": self.passive_ability.get('reward', []),
            "message": "Always Smiling: +1 persuasion (6+ strength)"
        }


class LadyAmberMetulli(Leader):
    """
    Lady Amber Metulli - Tactical Commander

    Progressive Signet Ability:
    - Level 1: +1 solari when you reveal
    - Level 2: +1 spice when you reveal

    Passive Ability (Desert Scouts):
    - During reveal phase
    - If you have 6+ strength (swords)
    - Optional: Recall 1 troop from conflict
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "ladyambermetulli.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Lady Amber Metulli",
            leader_id=3,
            signet_progression=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

    def check_passive_condition(self, game_state, player_id: str) -> bool:
        """
        Check if passive ability condition is met (6+ strength).

        Args:
            game_state: Current game state
            player_id: Player ID

        Returns:
            True if condition met
        """
        player = game_state.get_player_by_id(player_id)
        if not player:
            return False

        # Check strength (swords)
        swords = getattr(player, 'temp_swords', 0)
        return swords >= 6

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Desert Scouts passive ability.

        Optional (can decline): Recall 1 troop from conflict (if 6+ strength).

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

        if not self.check_passive_condition(game_state, player_id):
            return {
                "success": False,
                "error": "Need 6+ strength to use Desert Scouts"
            }

        player = game_state.get_player_by_id(player_id)

        # Check if player has troops in conflict
        if player.troops_in_conflict == 0:
            return {
                "success": False,
                "error": "No troops in conflict to recall"
            }

        return {
            "success": True,
            "effects": self.passive_ability.get('reward', []),
            "message": "Desert Scouts: Recall 1 troop (6+ strength)",
            "optional": self.passive_ability.get('required', True) == False
        }


class LadyJessica(Leader):
    """
    Lady Jessica - Bene Gesserit Reverend Mother

    Signet Ability (2 effects):
    1. Optional: Pay 1 spice → draw 1 intrigue card
    2. Always: Gain 1 memory

    Passive Ability (Other Memories):
    - Triggered when placing agent on Bene Gesserit board space (Espionnage or Secrets)
    - Draw 1 card per memory you have
    - Transform into Reverend Mother (flipped side)
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "ladyjessica.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Lady Jessica",
            leader_id=4,
            signet_progression=data.get('signet'),  # Use progression format for multiple effects
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track transformation state
        self.is_transformed = False  # False = Lady Jessica, True = Reverend Mother

    def can_use_passive(self, phase: str) -> bool:
        """
        Check if passive ability can be used.

        - Only usable before transformation
        - During agent phase (on Bene Gesserit placement)

        Args:
            phase: Current game phase

        Returns:
            True if passive can be used
        """
        if self.is_transformed:
            return False

        if not self.passive_ability:
            return False

        passive_phase = self.passive_ability.get('phase', '')
        return passive_phase == phase

    def check_bene_gesserit_trigger(self, location) -> bool:
        """
        Check if passive should trigger (Bene Gesserit space).

        Args:
            location: BoardSpace where agent was placed

        Returns:
            True if location has Bene Gesserit icon
        """
        if self.is_transformed:
            return False

        if hasattr(location, 'agent_icon'):
            icons = location.agent_icon if isinstance(location.agent_icon, list) else [location.agent_icon]
            return "bene_gesserit" in icons
        return False

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Other Memories passive ability.

        - Draw 1 card per memory
        - Transform into Reverend Mother

        Args:
            game_state: Current game state
            player_id: Player using passive
            context: Resolution context

        Returns:
            Result dict
        """
        if self.is_transformed:
            return {
                "success": False,
                "error": "Already transformed into Reverend Mother"
            }

        if not self.can_use_passive(context.get('phase', '')):
            return {
                "success": False,
                "error": "Other Memories can only be used during agent phase"
            }

        player = game_state.get_player_by_id(player_id)

        # Count memories (stored as resource)
        memory_count = getattr(player, 'memories', 0)

        if memory_count == 0:
            return {
                "success": False,
                "error": "No memories to return"
            }

        # Create effects: draw cards equal to memory count
        effects = [
            {"type": "draw", "deck": "deck", "amount": memory_count}
        ]

        # Mark for transformation after resolution
        self.is_transformed = True

        return {
            "success": True,
            "effects": effects,
            "message": f"Other Memories: Draw {memory_count} cards, transform to Reverend Mother",
            "optional": True,
            "memory_count": memory_count
        }


class PrincessIrulan(Leader):
    """
    Princess Irulan - Emperor's Daughter

    Signet Ability (choice):
    - Option 1: Acquire a card from Imperium row that costs 1 or less
    - Option 2: Trash a card from hand. If it cost at least 1 persuasion, gain 2 spice

    Passive Ability (Imperial Privilege):
    - Triggered when you reach 2 influence with Emperor
    - Draw 1 intrigue card
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "princessirulan.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Princess Irulan",
            leader_id=7,
            signet_ability=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track if passive has been triggered
        self.passive_triggered = False

    def can_use_passive(self, phase: str) -> bool:
        """
        Check if passive ability can be used.

        Triggered when reaching 2 Emperor influence (any phase).

        Args:
            phase: Current game phase

        Returns:
            True if passive can be used
        """
        if self.passive_triggered:
            return False

        return True

    def check_influence_trigger(self, player) -> bool:
        """
        Check if passive should trigger (2+ Emperor influence).

        Args:
            player: Player object

        Returns:
            True if player has 2+ Emperor influence
        """
        if self.passive_triggered:
            return False

        return player.emperor_influence >= 2

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Imperial Privilege passive ability.

        - Draw 1 intrigue card when reaching 2 Emperor influence

        Args:
            game_state: Current game state
            player_id: Player using passive
            context: Resolution context

        Returns:
            Result dict
        """
        if self.passive_triggered:
            return {
                "success": False,
                "error": "Imperial Privilege already triggered"
            }

        player = game_state.get_player_by_id(player_id)

        if player.emperor_influence < 2:
            return {
                "success": False,
                "error": "Need 2 Emperor influence to trigger Imperial Privilege"
            }

        # Mark as triggered (one-time ability)
        self.passive_triggered = True

        return {
            "success": True,
            "effects": self.passive_ability.get('reward', []),
            "message": "Imperial Privilege: Draw 1 intrigue (reached 2 Emperor influence)"
        }


class ReverendMother(Leader):
    """
    Reverend Mother - Lady Jessica (Transformed)

    Signet Ability:
    - Optional: Pay 1 spice to gain 1 water

    Passive Ability (Prescience):
    - When you send a spy to a Fremen or Bene Gesserit board space
    - Optional: Pay 1 water to retrigger the board space effect
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "reverendmother.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Reverend Mother",
            leader_id=4,  # Same ID as Lady Jessica (transformed form)
            signet_ability=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

    def can_use_passive(self, phase: str) -> bool:
        """
        Check if passive ability can be used.

        - During agent phase (when spy is placed)

        Args:
            phase: Current game phase

        Returns:
            True if passive can be used
        """
        if not self.passive_ability:
            return False

        passive_phase = self.passive_ability.get('phase', '')
        return passive_phase == phase or passive_phase == 'any'

    def check_spy_placement_trigger(self, location) -> bool:
        """
        Check if passive should trigger (spy on Fremen or Bene Gesserit space).

        Args:
            location: BoardSpace where spy was placed

        Returns:
            True if location has Fremen or Bene Gesserit icon
        """
        if hasattr(location, 'agent_icon'):
            icons = location.agent_icon if isinstance(location.agent_icon, list) else [location.agent_icon]
            return any(faction in icons for faction in ["fremen", "bene_gesserit"])
        return False

    def use_passive(self, game_state, player_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use Prescience passive ability.

        - Pay 1 water to retrigger board space effect

        Args:
            game_state: Current game state
            player_id: Player using passive
            context: Resolution context (must include 'location')

        Returns:
            Result dict
        """
        if not self.can_use_passive(context.get('phase', '')):
            return {
                "success": False,
                "error": "Prescience can only be used during agent phase"
            }

        player = game_state.get_player_by_id(player_id)

        # Check if player has water
        if player.water < 1:
            return {
                "success": False,
                "error": "Need 1 water to use Prescience"
            }

        # Check if location is provided
        location = context.get('location')
        if not location:
            return {
                "success": False,
                "error": "No location provided for Prescience"
            }

        # Verify it's a Fremen or Bene Gesserit space
        if not self.check_spy_placement_trigger(location):
            return {
                "success": False,
                "error": "Prescience only works on Fremen or Bene Gesserit spaces"
            }

        return {
            "success": True,
            "cost": self.passive_ability.get('cost', []),
            "effects": self.passive_ability.get('reward', []),
            "message": "Prescience: Pay 1 water to retrigger board space",
            "optional": True,
            "location": location
        }


class ShadhamCorrinoIV(Leader):
    """
    Shaddam Corrino IV - Emperor

    Signet Ability (2 effects):
    1. Restriction: Cannot deploy troops to conflict this turn
    2. Choice (required):
       - Option A: Gain 1 troop and 1 solari
       - Option B: Pay 3 solari to gain 1 influence anywhere

    Passive Ability (Sardaukar Reserves):
    - Setup phase: Set aside two Sardaukar contracts
    - Only you can accept these contracts
    - When accepting a contract, choose from board OR Sardaukar reserves
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "shaddamcorrinoiv.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Shaddam Corrino IV",
            leader_id=8,
            signet_progression=data.get('signet'),  # Use progression format for multiple effects
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track Sardaukar contract state
        self.sardaukar_contracts = []  # Will hold the two exclusive contracts
        self.troop_deployment_restricted = False  # Set when signet is used

    def apply_signet(self, game_state, player):
        """
        Apply Shaddam's signet ability:
        1. Restrict troop deployment this turn
        2. Player chooses: (troop + solari) OR (pay 3 solari for influence)
        """
        # First effect: Apply restriction
        self.troop_deployment_restricted = True
        player.restrictions = getattr(player, 'restrictions', [])
        player.restrictions.append('no_troop_deployment_this_turn')

        # Second effect: Return choice options
        return {
            "type": "choice",
            "required": True,
            "message": "Shaddam Corrino IV Signet: Choose your reward",
            "options": [
                {
                    "id": "troop_and_solari",
                    "description": "Gain 1 troop and 1 solari",
                    "effects": self.signet_progression[1]['options'][0]['reward']
                },
                {
                    "id": "pay_for_influence",
                    "description": "Pay 3 solari to gain 1 influence anywhere",
                    "cost": self.signet_progression[1]['options'][1]['cost'],
                    "effects": self.signet_progression[1]['options'][1]['reward']
                }
            ]
        }

    def setup_sardaukar_reserves(self, game_state):
        """
        Called during game setup to set aside Sardaukar contracts.
        """
        # Find and remove Sardaukar contracts from the contract deck
        contract_deck = game_state.contract_deck
        sardaukar_1 = None
        sardaukar_2 = None

        for contract in contract_deck.cards[:]:
            if hasattr(contract, 'id'):
                if contract.id == 'sardaukar_1':
                    sardaukar_1 = contract
                    contract_deck.cards.remove(contract)
                elif contract.id == 'sardaukar_2':
                    sardaukar_2 = contract
                    contract_deck.cards.remove(contract)

        # Store them in Shaddam's exclusive reserve
        if sardaukar_1:
            self.sardaukar_contracts.append(sardaukar_1)
        if sardaukar_2:
            self.sardaukar_contracts.append(sardaukar_2)

        return {
            "success": True,
            "message": f"Sardaukar Reserves: {len(self.sardaukar_contracts)} contracts set aside for Shaddam Corrino IV",
            "contracts": self.sardaukar_contracts
        }

    def get_available_contracts(self, board_contracts):
        """
        Get all contracts available to Shaddam (board + Sardaukar reserves).

        Args:
            board_contracts: The 2 contracts currently on the board

        Returns:
            Combined list of board contracts + Sardaukar contracts
        """
        return board_contracts + self.sardaukar_contracts

    def check_passive_trigger(self, game_state, trigger_type, **kwargs):
        """
        Check if passive ability should trigger.
        For Shaddam, this is handled during setup.
        """
        if trigger_type == "game_start":
            return self.setup_sardaukar_reserves(game_state)

        return {"success": False}

    def reset_turn_restrictions(self):
        """
        Called at end of turn to reset troop deployment restriction.
        """
        self.troop_deployment_restricted = False


class StabanTuek(Leader):
    """
    Staban Tuek - Smuggler

    Starting Deck Modification:
    - Does NOT start with a Diplomacy card (9 cards instead of 10)

    Signet Ability:
    - Play a spy anywhere
    - Then, based on where the agent was placed:
      - If on green space: Optional - Pay 1 spice to get 3 solari
      - If on faction space: Optional - Pay 2 solari to draw 1 intrigue
    - Both options can be available if the space qualifies for both

    Passive Ability (Smuggler's Trade):
    - Whenever ANY player goes to a Maker spot, you get 1 spice
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "stabantuek.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Staban Tuek",
            leader_id=9,
            signet_progression=data.get('signet'),  # Use progression format for multiple effects
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track starting deck modification
        self.starting_deck_modification = data.get('starting_deck_modification')

    def apply_signet(self, game_state, player, placement_location=None):
        """
        Apply Staban's signet ability:
        1. Play a spy anywhere
        2. Then offer conditional bonuses based on where the agent was placed

        Args:
            game_state: Current game state
            player: Player using the signet
            placement_location: The board space where the agent was placed

        Returns:
            Multi-part effect: spy placement + conditional bonuses
        """
        if not placement_location:
            return {
                "success": False,
                "error": "Placement location required for Staban Tuek signet"
            }

        # First effect: Play a spy
        spy_effect = {
            "type": "play_spy",
            "message": "Staban Tuek Signet: Play a spy anywhere"
        }

        # Second effect: Conditional bonuses based on placement
        # Check if it's a green space
        is_green_space = self.check_green_space(placement_location)
        # Check if it's a faction space
        is_faction_space = self.check_faction_space(placement_location)

        available_options = []

        if is_green_space:
            available_options.append({
                "id": "green_space_bonus",
                "description": "Pay 1 spice to get 3 solari",
                "cost": [{"type": "resource", "resource": "spice", "amount": 1}],
                "effects": [{"type": "resource", "resource": "solari", "amount": 3}],
                "optional": True
            })

        if is_faction_space:
            available_options.append({
                "id": "faction_space_bonus",
                "description": "Pay 2 solari to draw 1 intrigue",
                "cost": [{"type": "resource", "resource": "solari", "amount": 2}],
                "effects": [{"type": "draw", "deck": "intrigue", "amount": 1}],
                "optional": True
            })

        # Return both effects
        return {
            "type": "multi_effect",
            "effects": [
                spy_effect,
                {
                    "type": "conditional_bonuses",
                    "message": "Staban Tuek Signet: Optional bonuses",
                    "options": available_options if available_options else []
                }
            ]
        }

    def check_green_space(self, location):
        """
        Check if a board space is a green (neutral) space.
        """
        if hasattr(location, 'space_type'):
            return location.space_type == 'green'
        elif hasattr(location, 'factions'):
            # Green spaces have no faction affiliation
            return len(location.factions) == 0
        return False

    def check_faction_space(self, location):
        """
        Check if a board space is a faction space.
        """
        if hasattr(location, 'space_type'):
            return location.space_type == 'faction'
        elif hasattr(location, 'factions'):
            # Faction spaces have at least one faction
            return len(location.factions) > 0
        return False

    def check_passive_trigger(self, game_state, trigger_type, **kwargs):
        """
        Check if passive ability should trigger.
        Triggers when ANY player places an agent on a Maker spot.

        Args:
            trigger_type: Type of trigger event
            **kwargs: Additional context (e.g., player, location)

        Returns:
            Dict with success status and reward
        """
        if trigger_type == "agent_placement":
            location = kwargs.get('location')
            if location and self.is_maker_space(location):
                return {
                    "success": True,
                    "message": "Smuggler's Trade: Staban Tuek gains 1 spice",
                    "reward": [{"type": "resource", "resource": "spice", "amount": 1}]
                }

        return {"success": False}

    def is_maker_space(self, location):
        """
        Check if a board space is a Maker space.
        """
        if hasattr(location, 'name'):
            # Maker spaces typically have "Maker" in their name
            return 'maker' in location.name.lower()
        if hasattr(location, 'id'):
            return 'maker' in location.id.lower()
        return False

    def modify_starting_deck(self, starting_cards):
        """
        Remove Diplomacy card from starting deck.

        Args:
            starting_cards: List of starting cards

        Returns:
            Modified list with Diplomacy card removed
        """
        modified_cards = []
        diplomacy_removed = False

        for card in starting_cards:
            # Skip the first Diplomacy card we encounter
            if not diplomacy_removed and hasattr(card, 'name') and card.name.lower() == 'diplomacy':
                diplomacy_removed = True
                continue
            modified_cards.append(card)

        return modified_cards


class LadyMargotFenring(Leader):
    """
    Lady Margot Fenring - Bene Gesserit Adept

    Signet Ability:
    - Play a spy on a blue (Bene Gesserit) space

    Passive Ability:
    - When you reach 2 influence with Bene Gesserit, gain 2 spice
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "ladymargotfenring.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Lady Margot Fenring",
            leader_id=5,
            signet_progression=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

        # Track if passive has been triggered
        self.passive_triggered = False

    def apply_signet(self, game_state, player):
        """
        Apply Lady Margot's signet ability: Play a spy on a blue (Bene Gesserit) space.

        Returns:
            Effect to play a spy on a blue space
        """
        return {
            "type": "play_spy",
            "target": "blue",
            "message": "Lady Margot Fenring Signet: Play a spy on a Bene Gesserit (blue) space"
        }

    def check_passive_trigger(self, game_state, trigger_type, **kwargs):
        """
        Check if passive ability should trigger.
        Triggers when reaching 2 influence with Bene Gesserit (one-time).

        Args:
            trigger_type: Type of trigger event
            **kwargs: Additional context (e.g., faction, amount)

        Returns:
            Dict with success status and reward
        """
        if trigger_type == "influence_gained" and not self.passive_triggered:
            faction = kwargs.get('faction')
            player = kwargs.get('player')

            if faction == 'bene_gesserit' and player:
                # Check if player has reached 2 influence
                current_influence = getattr(player, 'bene_gesserit_influence', 0)
                if current_influence >= 2:
                    self.passive_triggered = True
                    return {
                        "success": True,
                        "message": "Lady Margot Fenring: Reached 2 Bene Gesserit influence, gain 2 spice",
                        "reward": [{"type": "resource", "resource": "spice", "amount": 2}]
                    }

        return {"success": False}


class MuadDib(Leader):
    """
    Muad'Dib - Paul Atreides (Fremen Leader)

    Signet Ability:
    - Draw 1 card from your deck

    Passive Ability:
    - When there is a sandworm in the conflict, draw 1 intrigue card
    """

    def __init__(self):
        # Load JSON data
        import json
        from pathlib import Path

        json_path = Path(__file__).parent.parent.parent / "data" / "leader_data" / "muaddib.json"
        with open(json_path, 'r') as f:
            data = json.load(f)

        super().__init__(
            name="Muad'Dib",
            leader_id=6,
            signet_progression=data.get('signet'),
            passive_ability=data.get('passive'),
            training_track_position=0
        )

    def apply_signet(self, game_state, player):
        """
        Apply Muad'Dib's signet ability: Draw 1 card from your deck.

        Returns:
            Effect to draw 1 card
        """
        return {
            "type": "draw",
            "deck": "deck",
            "amount": 1,
            "message": "Muad'Dib Signet: Draw 1 card from your deck"
        }

    def check_passive_trigger(self, game_state, trigger_type, **kwargs):
        """
        Check if passive ability should trigger.
        Triggers when there is a sandworm in the conflict.

        Args:
            trigger_type: Type of trigger event
            **kwargs: Additional context

        Returns:
            Dict with success status and reward
        """
        if trigger_type == "combat_phase_start":
            # Check if there's a sandworm in the current conflict
            has_sandworm = self.check_sandworm_in_conflict(game_state)

            if has_sandworm:
                return {
                    "success": True,
                    "message": "Muad'Dib: Sandworm in conflict, draw 1 intrigue card",
                    "reward": [{"type": "draw", "deck": "intrigue", "amount": 1}]
                }

        return {"success": False}

    def check_sandworm_in_conflict(self, game_state):
        """
        Check if there is a sandworm token in the current conflict.

        Returns:
            bool: True if sandworm is present in conflict
        """
        if hasattr(game_state, 'conflict'):
            conflict = game_state.conflict
            if hasattr(conflict, 'has_sandworm'):
                return conflict.has_sandworm
            if hasattr(conflict, 'modifiers'):
                return 'sandworm' in conflict.modifiers

        return False