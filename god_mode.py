"""
DUNE IMPERIUM UPRISING - GOD MODE
===================================

Interactive testing tool that lets you play the game with full control:
- Spawn any card into your hand
- Give yourself infinite resources (999 of everything)
- Adjust influence with any faction
- Place agents anywhere
- Test card effects in real-time
- See full game state at any time

This is perfect for testing specific card combinations and game situations.

Usage:
    python god_mode.py
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

from src.engine.core.game_setup import GameSetup
from src.engine.effects.effect_resolver import EffectResolver
from src.engine.core.game_state import GameState
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction
from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import ImperiumCard, IntrigueCard
from src.models.boardspace import BoardSpace
from src.loaders.card_loader import load_imperium_cards, load_intrigue_cards


class GodMode:
    """Interactive god mode for testing DUNE Imperium Uprising."""

    def __init__(self):
        """Initialize god mode with a fresh game."""
        print("="*80)
        print("DUNE IMPERIUM UPRISING - GOD MODE")
        print("="*80)
        print("\nInitializing game with full control...")

        # Create game
        self.game, setup_info = GameSetup.create_game(player_count=3)
        self.player = self.game.players[0]  # You are player 1
        self.state = GameState(self.game)
        self.resolver = EffectResolver(self.game)
        self.executor = ActionExecutor(self.game)

        # Load all cards for spawning
        self.all_imperium_cards = self._load_all_imperium_cards()
        self.all_intrigue_cards = self._load_all_intrigue_cards()

        # Give god mode resources
        self._activate_god_mode()

        print(f"\n✓ Game initialized!")
        print(f"✓ You are {self.player.name} ({self.player.color})")
        print(f"✓ Leader: {self.player.leader.name}")
        print(f"✓ God mode activated: 999 resources, 4 influence everywhere")
        print()

    def _load_all_imperium_cards(self) -> Dict[str, Dict]:
        """Load all imperium cards from JSON."""
        data_path = Path(__file__).parent / "data" / "imperium.JSON"
        with open(data_path, 'r') as f:
            cards = json.load(f)
        return {card['name'].lower(): card for card in cards}

    def _load_all_intrigue_cards(self) -> Dict[str, Dict]:
        """Load all intrigue cards from JSON."""
        data_path = Path(__file__).parent / "data" / "intrigue.JSON"
        with open(data_path, 'r') as f:
            data = json.load(f)
            cards = data.get('intrigues', [])
        return {card['name'].lower(): card for card in cards}

    def _activate_god_mode(self):
        """Give player infinite resources and high influence."""
        self.player.solari = 999
        self.player.spice = 999
        self.player.water = 999
        self.player.troops_in_garrison = 20
        self.player.troops_in_reserve = 20
        self.player.agents_available = 5
        self.player.total_available_agents = 5
        self.player.spies_available = 5
        self.player.total_available_spies = 5

        # High influence everywhere
        self.player.fremen_influence = 4
        self.player.bene_gesserit_influence = 4
        self.player.spacing_guild_influence = 4
        self.player.emperor_influence = 4

        # Initialize temp resources
        self.player.temp_persuasion = 0
        self.player.temp_swords = 0

    def show_status(self):
        """Display current game state."""
        print("\n" + "="*80)
        print("CURRENT STATUS")
        print("="*80)

        print(f"\n📊 Resources:")
        print(f"  Solari: {self.player.solari}")
        print(f"  Spice:  {self.player.spice}")
        print(f"  Water:  {self.player.water}")
        print(f"  VP:     {self.player.victory_points}")

        print(f"\n⚔️  Combat:")
        print(f"  Troops (garrison): {self.player.troops_in_garrison}")
        print(f"  Troops (conflict): {self.player.troops_in_conflict}")
        print(f"  Temp Swords:       {getattr(self.player, 'temp_swords', 0)}")

        print(f"\n🎯 Influence:")
        print(f"  Fremen:        {self.player.fremen_influence} {'✓' if self.player.fremen_alliance else ''}")
        print(f"  Bene Gesserit: {self.player.bene_gesserit_influence} {'✓' if self.player.bene_gesserit_alliance else ''}")
        print(f"  Spacing Guild: {self.player.spacing_guild_influence} {'✓' if self.player.spacing_guild_alliance else ''}")
        print(f"  Emperor:       {self.player.emperor_influence} {'✓' if self.player.emperor_alliance else ''}")

        print(f"\n🃏 Cards:")
        print(f"  Hand:     {len(self.player.hand.cards)} cards")
        print(f"  Deck:     {len(self.player.deck.cards)} cards")
        print(f"  Discard:  {len(self.player.discard_pile.cards)} cards")
        print(f"  Intrigue: {len(self.player.intrigue_cards)} cards")

        print(f"\n🎮 Agents & Spies:")
        print(f"  Agents available: {self.player.agents_available}/{self.player.total_available_agents}")
        print(f"  Spies available:  {self.player.spies_available}/{self.player.total_available_spies}")

        print()

    def show_hand(self):
        """Display cards in hand."""
        print("\n" + "="*80)
        print("YOUR HAND")
        print("="*80)

        if not self.player.hand.cards:
            print("  (empty)")
        else:
            for i, card in enumerate(self.player.hand.cards, 1):
                print(f"  {i}. {card.name}")
        print()

    def spawn_card(self, card_name: str):
        """Spawn a card directly into your hand."""
        from src.models.card import CardType

        card_name_lower = card_name.lower()

        # Try imperium cards first
        if card_name_lower in self.all_imperium_cards:
            card_data = self.all_imperium_cards[card_name_lower]
            card = ImperiumCard(
                name=card_data['name'],
                type="Imperium",
                card_type=CardType.IMPERIUM,
                id=card_data['id'],
                cost=card_data.get('cost', 0)
            )
            # Add effects
            card.reveal_effects = card_data.get('reveal_effects', [])
            card.agent_effects = card_data.get('agent_effects', [])
            card.on_acquire_effects = card_data.get('on_acquire_effects', [])

            # Add agent icon (keep as list if it's a list, otherwise make it a list)
            agent_icons = card_data.get('agent_icon', ['agent'])
            card.agent_icon = agent_icons if isinstance(agent_icons, list) else [agent_icons]

            self.player.hand.add_card(card)
            print(f"✓ Spawned '{card.name}' into your hand")
            return True

        # Try intrigue cards
        elif card_name_lower in self.all_intrigue_cards:
            card_data = self.all_intrigue_cards[card_name_lower]
            self.player.intrigue_cards.append(card_data)
            print(f"✓ Spawned intrigue card '{card_data['name']}'")
            return True

        else:
            print(f"✗ Card '{card_name}' not found")
            print(f"  (Try /list to see all available cards)")
            return False

    def list_cards(self, filter_text: str = ""):
        """List all available cards."""
        print("\n" + "="*80)
        print("AVAILABLE IMPERIUM CARDS")
        print("="*80)

        imperium_list = sorted(self.all_imperium_cards.keys())
        if filter_text:
            imperium_list = [c for c in imperium_list if filter_text.lower() in c]

        for i, card_name in enumerate(imperium_list, 1):
            card_data = self.all_imperium_cards[card_name]
            cost = card_data.get('cost', 0)
            faction = card_data.get('faction', '')
            faction_str = f" [{faction}]" if faction else ""
            print(f"  {i:3d}. {card_data['name']:40s} (Cost: {cost}){faction_str}")

        print(f"\nTotal: {len(imperium_list)} imperium cards")

        print("\n" + "="*80)
        print("AVAILABLE INTRIGUE CARDS")
        print("="*80)

        intrigue_list = sorted(self.all_intrigue_cards.keys())
        if filter_text:
            intrigue_list = [c for c in intrigue_list if filter_text.lower() in c]

        for i, card_name in enumerate(intrigue_list, 1):
            card_data = self.all_intrigue_cards[card_name]
            print(f"  {i:3d}. {card_data['name']}")

        print(f"\nTotal: {len(intrigue_list)} intrigue cards")
        print()

    def play_card_from_hand(self, card_index: int):
        """Reveal a card from hand and resolve its effects."""
        if card_index < 1 or card_index > len(self.player.hand.cards):
            print("✗ Invalid card index")
            return

        card = self.player.hand.cards[card_index - 1]

        print(f"\n🎴 Playing card: {card.name}")
        print("-" * 80)

        # Show what effects this card has
        if hasattr(card, 'reveal_effects') and card.reveal_effects:
            print(f"\nReveal effects: {len(card.reveal_effects)} effect(s)")

        # Resolve reveal effects
        if hasattr(card, 'reveal_effects') and card.reveal_effects:
            context = {
                "card": card.name,
                "phase": "reveal",
                "player_id": self.player.player_id
            }

            result = self.resolver.resolve_effects(
                self.player.player_id,
                card.reveal_effects,
                context
            )

            print(f"\nResolution result:")
            print(f"  Success: {result.get('success', False)}")

            if result.get('effects_applied'):
                print(f"  Effects applied: {len(result['effects_applied'])}")
                for effect in result['effects_applied']:
                    print(f"    - {effect.get('type', 'unknown')}")

            if result.get('choices_required'):
                print(f"  Choices required: {len(result['choices_required'])}")
                for choice in result['choices_required']:
                    print(f"    - {choice.get('type', 'unknown')}")
        else:
            print("  (No reveal effects)")

        print()
        self.show_status()

    def reveal_hand(self):
        """Reveal all cards in hand and resolve all reveal effects."""
        if not self.player.hand.cards:
            print("\n✗ No cards in hand to reveal!")
            return

        print("\n" + "="*80)
        print("🎴 REVEALING HAND")
        print("="*80)

        # Reset temp resources
        self.player.temp_persuasion = 0
        self.player.temp_swords = 0

        total_persuasion = 0
        total_swords = 0

        print(f"\nRevealing {len(self.player.hand.cards)} cards:")
        print()

        # Resolve each card's reveal effects
        for i, card in enumerate(self.player.hand.cards, 1):
            print(f"  [{i}] {card.name}")

            if hasattr(card, 'reveal_effects') and card.reveal_effects:
                context = {
                    "card": card.name,
                    "phase": "reveal",
                    "player_id": self.player.player_id
                }

                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.reveal_effects,
                    context
                )

                # Show what was gained
                persuasion_before = total_persuasion
                swords_before = total_swords
                total_persuasion = getattr(self.player, 'temp_persuasion', 0)
                total_swords = getattr(self.player, 'temp_swords', 0)

                persuasion_gain = total_persuasion - persuasion_before
                swords_gain = total_swords - swords_before

                effects_str = []
                if persuasion_gain > 0:
                    effects_str.append(f"+{persuasion_gain} persuasion")
                if swords_gain > 0:
                    effects_str.append(f"+{swords_gain} swords")

                if effects_str:
                    print(f"      → {', '.join(effects_str)}")

                if result.get('choices_required'):
                    print(f"      → Requires choice")
            else:
                print(f"      → No reveal effects")

        print()
        print("="*80)
        print("REVEAL SUMMARY")
        print("="*80)
        print(f"  Total Persuasion: {total_persuasion} (use to acquire cards)")
        print(f"  Total Swords:     {total_swords} (combat strength)")
        print()

    def resolve_combat(self):
        """Resolve combat with current troops and swords."""
        print("\n" + "="*80)
        print("⚔️  COMBAT RESOLUTION")
        print("="*80)

        troops = self.player.troops_in_conflict
        swords = getattr(self.player, 'temp_swords', 0)
        sandworms = self.player.sandworms_in_conflict

        if troops == 0 and sandworms == 0:
            print("\n✗ No troops in conflict! Deploy troops first with /deploy")
            print("  Example: /deploy 5")
            return

        print(f"\n📊 Combat Strength Calculation:")
        print(f"  Troops in conflict:    {troops}")
        print(f"  Strength per troop:    2")
        print(f"  Base troop strength:   {troops * 2}")

        if sandworms > 0:
            print(f"  Sandworms in conflict: {sandworms}")
            print(f"  Strength per sandworm: 3")
            print(f"  Sandworm strength:     {sandworms * 3}")

        print(f"  Temp swords:           {swords}")
        print()

        total_strength = (troops * 2) + (sandworms * 3) + swords

        print(f"  {'='*40}")
        print(f"  TOTAL COMBAT STRENGTH: {total_strength}")
        print(f"  {'='*40}")
        print()

        # Show potential rewards based on strength
        print("💰 Potential Rewards (example conflict):")
        if total_strength >= 8:
            print("  🥇 1st Place (8+ strength): 2 solari, 1 spice, 1 VP")
        elif total_strength >= 4:
            print("  🥈 2nd Place (4-7 strength): 1 solari, 1 influence")
        elif total_strength >= 1:
            print("  🥉 3rd Place (1-3 strength): 1 troop")
        else:
            print("  No rewards (0 strength)")
        print()

    def deploy_troops(self, amount: int):
        """Deploy troops from garrison to conflict."""
        if amount < 0:
            print("✗ Cannot deploy negative troops")
            return

        if amount > self.player.troops_in_garrison:
            print(f"✗ Not enough troops in garrison (have {self.player.troops_in_garrison})")
            return

        self.player.troops_in_garrison -= amount
        self.player.troops_in_conflict += amount

        print(f"✓ Deployed {amount} troops to conflict")
        print(f"  Garrison: {self.player.troops_in_garrison}")
        print(f"  Conflict: {self.player.troops_in_conflict}")

    def retreat_troops(self, amount: int):
        """Retreat troops from conflict back to garrison."""
        if amount < 0:
            print("✗ Cannot retreat negative troops")
            return

        if amount > self.player.troops_in_conflict:
            print(f"✗ Not enough troops in conflict (have {self.player.troops_in_conflict})")
            return

        self.player.troops_in_conflict -= amount
        self.player.troops_in_garrison += amount

        print(f"✓ Retreated {amount} troops from conflict")
        print(f"  Garrison: {self.player.troops_in_garrison}")
        print(f"  Conflict: {self.player.troops_in_conflict}")

    def adjust_resource(self, resource: str, amount: int):
        """Adjust a resource by a specific amount."""
        resource_lower = resource.lower()

        if resource_lower in ['solari', 'sol']:
            self.player.solari = max(0, self.player.solari + amount)
            print(f"✓ Solari: {self.player.solari}")
        elif resource_lower in ['spice', 'sp']:
            self.player.spice = max(0, self.player.spice + amount)
            print(f"✓ Spice: {self.player.spice}")
        elif resource_lower in ['water', 'w']:
            self.player.water = max(0, self.player.water + amount)
            print(f"✓ Water: {self.player.water}")
        elif resource_lower in ['vp', 'victory', 'victory_points']:
            self.player.victory_points = max(0, self.player.victory_points + amount)
            print(f"✓ Victory Points: {self.player.victory_points}")
        elif resource_lower in ['troops', 'troop', 't']:
            self.player.troops_in_garrison = max(0, self.player.troops_in_garrison + amount)
            print(f"✓ Troops in garrison: {self.player.troops_in_garrison}")
        elif resource_lower in ['persuasion', 'p']:
            if not hasattr(self.player, 'temp_persuasion'):
                self.player.temp_persuasion = 0
            self.player.temp_persuasion = max(0, self.player.temp_persuasion + amount)
            print(f"✓ Persuasion: {self.player.temp_persuasion}")
        elif resource_lower in ['swords', 'sword', 's']:
            if not hasattr(self.player, 'temp_swords'):
                self.player.temp_swords = 0
            self.player.temp_swords = max(0, self.player.temp_swords + amount)
            print(f"✓ Swords: {self.player.temp_swords}")
        else:
            print(f"✗ Unknown resource '{resource}'")
            print(f"  Valid: solari, spice, water, vp, troops, persuasion, swords")

    def adjust_influence(self, faction: str, amount: int):
        """Adjust influence with a faction."""
        faction_lower = faction.lower()

        if faction_lower in ['fremen', 'f']:
            self.player.fremen_influence = max(0, self.player.fremen_influence + amount)
            print(f"✓ Fremen influence: {self.player.fremen_influence}")
        elif faction_lower in ['bene_gesserit', 'bene', 'bg', 'b']:
            self.player.bene_gesserit_influence = max(0, self.player.bene_gesserit_influence + amount)
            print(f"✓ Bene Gesserit influence: {self.player.bene_gesserit_influence}")
        elif faction_lower in ['spacing_guild', 'guild', 'sg', 'g']:
            self.player.spacing_guild_influence = max(0, self.player.spacing_guild_influence + amount)
            print(f"✓ Spacing Guild influence: {self.player.spacing_guild_influence}")
        elif faction_lower in ['emperor', 'emp', 'e']:
            self.player.emperor_influence = max(0, self.player.emperor_influence + amount)
            print(f"✓ Emperor influence: {self.player.emperor_influence}")
        else:
            print(f"✗ Unknown faction '{faction}'")
            print(f"  Valid: fremen, bene_gesserit, spacing_guild, emperor")

    def show_board(self, filter_text: str = ""):
        """Display all board spaces and their status."""
        print("\n" + "="*80)
        print("BOARD SPACES")
        print("="*80)

        spaces = self.game.board.spaces
        if filter_text:
            filter_lower = filter_text.lower()
            spaces = [s for s in spaces if
                     filter_lower in s.name.lower() or
                     (s.faction and filter_lower in s.faction.lower())]

        # Group by faction
        factions = {}
        for space in spaces:
            faction_key = space.faction if space.faction else "Neutral"
            if faction_key not in factions:
                factions[faction_key] = []
            factions[faction_key].append(space)

        for faction_name in sorted(factions.keys()):
            print(f"\n{faction_name.upper()}:")
            for space in factions[faction_name]:
                space_id = space.id
                occupied = ""
                if space.occupied_by:
                    if space.occupied_by == self.player.player_id:
                        occupied = " [YOU]"
                    else:
                        occupied = f" [P{space.occupied_by}]"
                elif space.infiltrated_by:
                    occupied = " [INFILTRATED]"

                combat = " ⚔️" if getattr(space, 'is_combat_space', False) else ""
                maker = " 🪱" if getattr(space, 'is_maker_space', False) else ""

                # Show cost if any
                cost_str = ""
                if hasattr(space, 'cost') and space.cost:
                    costs = []
                    for c in space.cost:
                        if c.get('type') == 'resource':
                            costs.append(f"{c['amount']} {c['resource']}")
                    if costs:
                        cost_str = f" (Cost: {', '.join(costs)})"

                print(f"  [{space_id:2d}] {space.name:30s}{combat}{maker}{cost_str}{occupied}")

        print(f"\nTotal: {len(spaces)} spaces")
        if filter_text:
            print(f"(Filtered by '{filter_text}')")
        print()

    def start_agent_placement(self, card_index: int):
        """Step 1: Choose a card to play, then show where you can go."""
        # Validate card
        if card_index < 1 or card_index > len(self.player.hand.cards):
            print("✗ Invalid card index")
            return

        card = self.player.hand.cards[card_index - 1]

        # Check if we have agents available
        if self.player.agents_available <= 0:
            print("✗ No agents available")
            print("  Use /godmode to reset agents")
            return

        print(f"\n🎴 Selected card: {card.name}")
        print("-" * 80)

        # Show card's agent icon(s)
        agent_icons = getattr(card, 'agent_icon', ['agent'])
        # Ensure it's a list
        if not isinstance(agent_icons, list):
            agent_icons = [agent_icons]
        print(f"Agent icons: {', '.join(agent_icons)}")

        # Show card's agent effects (what you'll get from the card)
        if hasattr(card, 'agent_effects') and card.agent_effects:
            print(f"\nCard agent effects:")
            for i, effect in enumerate(card.agent_effects, 1):
                effect_desc = self._describe_effect(effect)
                print(f"  [{i}] {effect_desc}")
        else:
            print("\nCard has no agent effects")

        print("\n" + "="*80)
        print("AVAILABLE BOARD SPACES")
        print("="*80)

        # Show all valid spaces for this card
        valid_spaces = []
        for space in self.game.board.spaces:
            # Check if space matches ANY of the card's agent icons
            if space.agent_icon not in agent_icons:
                continue

            # Check if occupied
            if space.occupied_by and space.occupied_by != self.player.player_id:
                continue

            valid_spaces.append(space)

        if not valid_spaces:
            print("No available spaces for this card's agent icon!")
            return

        # Display valid spaces
        for space in valid_spaces:
            combat = " ⚔️" if getattr(space, 'is_combat_space', False) else ""
            maker = " 🪱" if getattr(space, 'is_maker_space', False) else ""

            # Show cost
            cost_str = ""
            if hasattr(space, 'cost') and space.cost:
                costs = []
                for c in space.cost:
                    if c.get('type') == 'resource':
                        costs.append(f"{c['amount']} {c['resource']}")
                if costs:
                    cost_str = f" (Cost: {', '.join(costs)})"

            print(f"\n  [{space.id:2d}] {space.name}{combat}{maker}{cost_str}")

            # Show location effects
            if hasattr(space, 'effects') and space.effects:
                print(f"      Location effects:")
                for i, effect in enumerate(space.effects, 1):
                    effect_desc = self._describe_effect(effect)
                    print(f"        [{i}] {effect_desc}")

        print("\n" + "="*80)
        print(f"Type: /go <space_id> to place your agent")
        print("="*80)

        # Store pending placement
        self.pending_placement = {
            'card': card,
            'card_index': card_index,
            'valid_spaces': [s.id for s in valid_spaces]
        }

    def _describe_effect(self, effect: dict) -> str:
        """Describe an effect in human-readable form."""
        effect_type = effect.get('type', 'unknown')

        if effect_type == 'resource':
            resource = effect.get('resource', '')
            amount = effect.get('amount', 0)
            return f"Gain {amount} {resource}"
        elif effect_type == 'influence':
            target = effect.get('target', '')
            amount = effect.get('amount', 0)
            return f"Gain {amount} {target} influence"
        elif effect_type == 'draw':
            deck = effect.get('deck', '')
            amount = effect.get('amount', 0)
            return f"Draw {amount} card(s) from {deck}"
        elif effect_type == 'trash':
            amount = effect.get('amount', 1)
            return f"Trash {amount} card(s)"
        elif effect_type == 'steal':
            deck = effect.get('deck', '')
            amount = effect.get('amount', 0)
            return f"Steal {amount} card(s) from {deck}"
        elif effect_type == 'play':
            unit = effect.get('unit', '')
            amount = effect.get('amount', 0)
            return f"Place {amount} {unit}(s)"
        else:
            return f"{effect_type}"

    def go_to_space(self, space_id: int):
        """Step 2: Choose where to place your agent."""
        if not hasattr(self, 'pending_placement'):
            print("✗ No card selected. Use /play <card#> first")
            return

        if space_id not in self.pending_placement['valid_spaces']:
            print("✗ Invalid space for this card")
            return

        space = self.game.board.get_space_by_id(space_id)
        if not space:
            print("✗ Space not found")
            return

        card = self.pending_placement['card']

        print(f"\n🎯 Placing agent at: {space.name}")
        print(f"   Using card: {card.name}")
        print("-" * 80)

        # Collect all effects (card + location)
        all_effects = []

        # Card agent effects
        if hasattr(card, 'agent_effects') and card.agent_effects:
            for effect in card.agent_effects:
                all_effects.append(('card', effect))

        # Location effects
        if hasattr(space, 'effects') and space.effects:
            for effect in space.effects:
                all_effects.append(('location', effect))

        if all_effects:
            print("\n📋 All available effects:")
            for i, (source, effect) in enumerate(all_effects, 1):
                source_label = "CARD" if source == 'card' else "LOCATION"
                effect_desc = self._describe_effect(effect)
                print(f"  [{i}] [{source_label:8s}] {effect_desc}")

            print("\n" + "="*80)
            print("Choose effect resolution order:")
            print("  /order 1,2,3,...  - Resolve in this order")
            print("  /auto             - Auto-resolve in default order")
            print("="*80)
        else:
            print("\nNo effects to resolve")
            # Go straight to troop deployment if combat space
            if getattr(space, 'is_combat_space', False):
                self._ask_troop_deployment(card, space, [])
            else:
                self._finalize_placement(card, space, [], 0)

        # Store for next step
        self.pending_placement['space'] = space
        self.pending_placement['all_effects'] = all_effects

    def resolve_effects_in_order(self, order: list):
        """Step 3: Resolve effects in chosen order."""
        if not hasattr(self, 'pending_placement') or 'all_effects' not in self.pending_placement:
            print("✗ No pending placement")
            return

        all_effects = self.pending_placement['all_effects']
        card = self.pending_placement['card']
        space = self.pending_placement['space']

        # Validate order
        if len(order) != len(all_effects):
            print(f"✗ Must specify all {len(all_effects)} effects")
            return

        if any(i < 1 or i > len(all_effects) for i in order):
            print("✗ Invalid effect numbers")
            return

        print("\n📊 Resolving effects in your chosen order:")
        print("-" * 80)

        ordered_effects = [all_effects[i-1] for i in order]

        for i, (source, effect) in enumerate(ordered_effects, 1):
            source_label = "CARD" if source == 'card' else "LOCATION"
            effect_desc = self._describe_effect(effect)
            print(f"\n[{i}] Resolving: [{source_label}] {effect_desc}")

            # Actually resolve the effect
            result = self.resolver.resolve_effects(
                self.player.player_id,
                [effect],
                {"card": card.name, "location": space.name}
            )

            if result.get('success'):
                print("    ✓ Resolved")
            else:
                print(f"    ✗ Failed: {result.get('error', 'Unknown')}")

        # Now check if combat space for troop deployment
        if getattr(space, 'is_combat_space', False):
            self._ask_troop_deployment(card, space, ordered_effects)
        else:
            self._finalize_placement(card, space, ordered_effects, 0)

    def _ask_troop_deployment(self, card, space, effects_resolved):
        """Step 4: Ask about troop deployment for combat spaces."""
        print("\n" + "="*80)
        print("⚔️  COMBAT SPACE - TROOP DEPLOYMENT")
        print("="*80)
        print(f"\nYou have {self.player.troops_in_garrison} troops in garrison")
        print(f"Currently in conflict: {self.player.troops_in_conflict} troops")
        print("\nHow many troops do you want to deploy?")
        print("  /deploy <amount>  - Deploy troops")
        print("  /deploy 0         - Deploy no troops")
        print("="*80)

        # Store for finalization
        self.pending_placement['awaiting_deployment'] = True
        self.pending_placement['effects_resolved'] = effects_resolved

    def finalize_deployment(self, troops: int):
        """Step 5: Finalize with troop deployment choice."""
        if not hasattr(self, 'pending_placement') or not self.pending_placement.get('awaiting_deployment'):
            print("✗ Not awaiting deployment")
            return

        if troops > self.player.troops_in_garrison:
            print(f"✗ Not enough troops (have {self.player.troops_in_garrison})")
            return

        card = self.pending_placement['card']
        space = self.pending_placement['space']
        effects_resolved = self.pending_placement['effects_resolved']

        self._finalize_placement(card, space, effects_resolved, troops)

    def _finalize_placement(self, card, space, effects_resolved, troops_deployed):
        """Final step: Complete the placement."""
        # Remove agent
        self.player.agents_available -= 1
        self.player.agents_placed.append(space.id)

        # Mark space as occupied
        space.occupied_by = self.player.player_id

        # Remove card from hand
        self.player.hand.cards.remove(card)
        self.player.played_cards_this_turn.append(card)

        # Deploy troops if any
        if troops_deployed > 0:
            self.player.troops_in_garrison -= troops_deployed
            self.player.troops_in_conflict += troops_deployed

        print("\n" + "="*80)
        print("✅ AGENT PLACEMENT COMPLETE")
        print("="*80)
        print(f"\n🎴 Card played: {card.name}")
        print(f"🎯 Location: {space.name}")
        print(f"📊 Effects resolved: {len(effects_resolved)}")
        if troops_deployed > 0:
            print(f"⚔️  Troops deployed: {troops_deployed}")
        print()

        # Clear pending
        if hasattr(self, 'pending_placement'):
            delattr(self, 'pending_placement')

        self.show_status()

    def clear_board(self):
        """Clear all agents from the board (for testing multiple placements)."""
        for space in self.game.board.spaces:
            space.occupied_by = None
            space.infiltrated_by = None

        # Restore agents
        self.player.agents_placed = []
        self.player.spies_placed = []
        self._activate_god_mode()  # Reset agents

        print("✓ Board cleared - all spaces now available")
        print("✓ Agents restored to your pool")

    def show_help(self):
        """Display help message."""
        print("\n" + "="*80)
        print("COMMANDS")
        print("="*80)

        print("\n📋 Information:")
        print("  /help, /h              - Show this help")
        print("  /status, /s            - Show current game status")
        print("  /hand                  - Show cards in hand")
        print("  /list [filter]         - List all available cards (optional filter)")
        print("  /board [filter]        - Show all board spaces (optional filter)")

        print("\n🃏 Card Actions:")
        print("  /spawn <card name>     - Spawn a card into your hand")
        print("  /play <number>         - Play single card from hand (by number)")
        print("  /reveal                - Reveal entire hand (resolve all reveal effects)")

        print("\n🎯 Agent Placement (Interactive, Real Game!):")
        print("  /play <card#>      - Step 1: Choose card, see valid spaces")
        print("  /go <space#>       - Step 2: Choose space, see all effects")
        print("  /order 1,2,3,...   - Step 3: Choose effect resolution order")
        print("  /auto              - Step 3: Auto-resolve effects in default order")
        print("  /deploy <amount>   - Step 4: Deploy troops (combat spaces only)")
        print("  /clear             - Clear all agents from board")

        print("\n💰 Resource Management:")
        print("  /give <resource> <amt> - Add resources (solari/spice/water/vp/troops/persuasion/swords)")
        print("  /take <resource> <amt> - Remove resources")
        print("  /godmode               - Reset to 999 of everything")

        print("\n🎯 Influence:")
        print("  /influence <faction> <amt> - Adjust influence (fremen/bene/guild/emperor)")
        print("  /inf <faction> <amt>       - Short version")

        print("\n⚔️  Combat:")
        print("  /deploy <amount>       - Deploy troops from garrison to conflict")
        print("  /retreat <amount>      - Retreat troops from conflict to garrison")
        print("  /combat                - Calculate and show combat strength")

        print("\n🎮 Game Control:")
        print("  /reset                 - Start a new game")
        print("  /quit, /q              - Exit god mode")

        print("\n💡 Examples:")
        print("  /spawn leadership         - Add Leadership card to hand")
        print("  /board fremen             - Show all Fremen board spaces")
        print()
        print("  Agent Placement Flow:")
        print("    /play 1                 - Choose card #1, see valid spaces")
        print("    /go 5                   - Go to space #5, see effects")
        print("    /order 2,1,3            - Resolve effects in order: 2nd, 1st, 3rd")
        print("    /deploy 5               - Deploy 5 troops (if combat space)")
        print()
        print("  Quick commands:")
        print("  /reveal                   - Reveal all cards (get persuasion/swords)")
        print("  /combat                   - See total combat strength")
        print("  /give spice 10            - Add 10 spice")
        print("  /inf fremen 2             - Add 2 Fremen influence")
        print()

    def run(self):
        """Main interactive loop."""
        self.show_help()
        self.show_status()

        print("Type /help for commands, /quit to exit\n")

        while True:
            try:
                command = input("god> ").strip()

                if not command:
                    continue

                # Parse command
                parts = command.split(maxsplit=2)
                cmd = parts[0].lower()

                # Help
                if cmd in ['/help', '/h']:
                    self.show_help()

                # Status
                elif cmd in ['/status', '/s']:
                    self.show_status()

                # Hand
                elif cmd in ['/hand']:
                    self.show_hand()

                # List cards
                elif cmd in ['/list']:
                    filter_text = parts[1] if len(parts) > 1 else ""
                    self.list_cards(filter_text)

                # Show board
                elif cmd in ['/board', '/spaces']:
                    filter_text = parts[1] if len(parts) > 1 else ""
                    self.show_board(filter_text)

                # Clear board
                elif cmd in ['/clear']:
                    self.clear_board()

                # Agent placement: Step 2 - Choose space
                elif cmd in ['/go']:
                    if len(parts) < 2:
                        print("Usage: /go <space id>")
                    else:
                        try:
                            space_id = int(parts[1])
                            self.go_to_space(space_id)
                        except ValueError:
                            print("Invalid space id")

                # Agent placement: Step 3 - Effect order
                elif cmd in ['/order']:
                    if len(parts) < 2:
                        print("Usage: /order 1,2,3,...")
                    else:
                        try:
                            order_str = parts[1]
                            order = [int(x.strip()) for x in order_str.split(',')]
                            self.resolve_effects_in_order(order)
                        except ValueError:
                            print("Invalid order format. Use: /order 1,2,3")

                # Agent placement: Step 3 - Auto resolve
                elif cmd in ['/auto']:
                    if hasattr(self, 'pending_placement') and 'all_effects' in self.pending_placement:
                        all_effects = self.pending_placement['all_effects']
                        auto_order = list(range(1, len(all_effects) + 1))
                        self.resolve_effects_in_order(auto_order)
                    else:
                        print("✗ No pending effects to resolve")

                # Spawn card
                elif cmd in ['/spawn']:
                    if len(parts) < 2:
                        print("Usage: /spawn <card name>")
                    else:
                        card_name = " ".join(parts[1:])
                        self.spawn_card(card_name)

                # Play card - Agent placement Step 1
                elif cmd in ['/play']:
                    if len(parts) < 2:
                        print("Usage: /play <card number>")
                    else:
                        try:
                            card_num = int(parts[1])
                            self.start_agent_placement(card_num)
                        except ValueError:
                            print("Invalid card number")

                # Reveal hand
                elif cmd in ['/reveal']:
                    self.reveal_hand()

                # Deploy troops
                elif cmd in ['/deploy']:
                    if len(parts) < 2:
                        print("Usage: /deploy <amount>")
                    else:
                        try:
                            amount = int(parts[1])
                            # Check if we're finalizing agent placement or just deploying
                            if hasattr(self, 'pending_placement') and self.pending_placement.get('awaiting_deployment'):
                                self.finalize_deployment(amount)
                            else:
                                # Old functionality: just deploy troops
                                self.deploy_troops(amount)
                        except ValueError:
                            print("Invalid amount")

                # Retreat troops
                elif cmd in ['/retreat']:
                    if len(parts) < 2:
                        print("Usage: /retreat <amount>")
                    else:
                        try:
                            amount = int(parts[1])
                            self.retreat_troops(amount)
                        except ValueError:
                            print("Invalid amount")

                # Combat resolution
                elif cmd in ['/combat']:
                    self.resolve_combat()

                # Give resource
                elif cmd in ['/give']:
                    if len(parts) < 3:
                        print("Usage: /give <resource> <amount>")
                    else:
                        try:
                            amount = int(parts[2])
                            self.adjust_resource(parts[1], amount)
                        except ValueError:
                            print("Invalid amount")

                # Take resource
                elif cmd in ['/take']:
                    if len(parts) < 3:
                        print("Usage: /take <resource> <amount>")
                    else:
                        try:
                            amount = -int(parts[2])
                            self.adjust_resource(parts[1], amount)
                        except ValueError:
                            print("Invalid amount")

                # Adjust influence
                elif cmd in ['/influence', '/inf']:
                    if len(parts) < 3:
                        print("Usage: /influence <faction> <amount>")
                    else:
                        try:
                            amount = int(parts[2])
                            self.adjust_influence(parts[1], amount)
                        except ValueError:
                            print("Invalid amount")

                # God mode
                elif cmd in ['/godmode']:
                    self._activate_god_mode()
                    print("✓ God mode reactivated: 999 resources, 4 influence everywhere")

                # Reset
                elif cmd in ['/reset']:
                    print("\nStarting new game...")
                    self.__init__()

                # Quit
                elif cmd in ['/quit', '/q', '/exit']:
                    print("\nExiting god mode. May your path be long and your waters plentiful.")
                    break

                else:
                    print(f"Unknown command: {cmd}")
                    print("Type /help for available commands")

            except KeyboardInterrupt:
                print("\n\nExiting god mode. May your path be long and your waters plentiful.")
                break
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()


def main():
    """Entry point for god mode."""
    god_mode = GodMode()
    god_mode.run()


if __name__ == "__main__":
    main()
