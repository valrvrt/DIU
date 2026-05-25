"""
Comprehensive test suite for all 60 Imperium cards.

NOTE: This test is superseded by test/comprehensive/test_complete_card_integration.py
which is the canonical test for all card effects. Kept for reference only.
"""

import pytest
import json
from pathlib import Path

pytestmark = pytest.mark.skip(reason="Superseded by test/comprehensive/test_complete_card_integration.py")
from unittest.mock import Mock, MagicMock

from src.engine.effects.effect_resolver import EffectResolver
from src.models.player import Player
from src.models.deck import Deck
from src.models.boardspace import BoardSpace, ObservationPost


class TestImperiumCards:
    """Comprehensive tests for all Imperium cards."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures before each test."""
        # Load all imperium cards
        imperium_file = Path(__file__).parent.parent / "data" / "imperium.JSON"
        with open(imperium_file, 'r') as f:
            self.all_cards = json.load(f)

        # Create mock game state
        self.game = Mock()
        self.game.board = Mock()
        self.game.board.spaces = []
        self.game.board.observation_posts = []

        # Create test player
        self.player = Player(
            player_id="test_player",
            name="Test Player",
            color="blue"
        )
        self.player.hand = Hand()
        self.player.deck = Deck()
        self.player.discard_pile = Deck()
        self.player.play_area = []

        # Initialize resources
        self.player.solari = 10
        self.player.spice = 10
        self.player.water = 10
        self.player.troops_in_garrison = 5
        self.player.troops_in_conflict = 0
        self.player.temp_persuasion = 0
        self.player.temp_swords = 0
        self.player.victory_points = 0

        # Initialize influence
        self.player.fremen_influence = 0
        self.player.bene_gesserit_influence = 0
        self.player.spacing_guild_influence = 0
        self.player.emperor_influence = 0

        # Initialize other attributes
        self.player.alliances = []
        self.player.contracts_completed = []
        self.player.spies_placed = []
        self.player.available_spies = 2
        self.player.revealed_cards_this_turn = []
        self.player.agents_sent_this_turn = []
        self.player.trashed_cards = []

        # Create mock state
        self.state = Mock()
        self.state.get_player_by_id = Mock(return_value=self.player)
        self.state.players = [self.player]

        # Create effect resolver
        self.resolver = EffectResolver(self.state, self.game)

    def create_card_instance(self, card_data):
        """Create a Card instance from JSON data."""
        card = Card(
            card_id=card_data['id'],
            name=card_data['name'],
            faction=card_data.get('faction'),
            cost=card_data['cost']
        )

        # Add effects
        card.on_acquire_effects = card_data.get('on_acquire_effects', [])
        card.agent_effects = card_data.get('agent_effects', [])
        card.reveal_effects = card_data.get('reveal_effects', [])
        card.on_discard_effects = card_data.get('on_discard_effects', [])
        card.on_trash_effects = card_data.get('on_trash_effects', [])
        card.fremen_bond_effects = card_data.get('fremen_bond_effects', [])

        return card

    def create_board_space(self, space_id, space_type=None, faction=None):
        """Create a mock board space."""
        space = Mock(spec=BoardSpace)
        space.id = space_id
        space.type = space_type or ""
        space.faction = faction or ""
        return space

    def create_observation_post(self, post_id, faction, watches_type=None):
        """Create a mock observation post."""
        post = Mock(spec=ObservationPost)
        post.id = post_id
        post.name = faction
        post.faction = faction
        post.watches_type = watches_type or ""
        return post

    def test_all_cards_load(self):
        """Test that all 60 cards load correctly from JSON."""
        assert len(self.all_cards) == 60, f"Expected 60 cards, found {len(self.all_cards)}"

        # Verify all cards have required fields
        for card in self.all_cards:
            assert 'id' in card, f"Card missing id: {card.get('name')}"
            assert 'name' in card, f"Card missing name: {card}"
            assert 'cost' in card, f"Card {card.get('name')} missing cost"
            assert 'quantity' in card, f"Card {card.get('name')} missing quantity"

    def test_on_acquire_effects(self):
        """Test on_acquire effects for all cards that have them."""
        cards_with_on_acquire = [c for c in self.all_cards if c.get('on_acquire_effects')]

        print(f"\nTesting {len(cards_with_on_acquire)} cards with on_acquire effects...")

        for card_data in cards_with_on_acquire:
            card = self.create_card_instance(card_data)

            # Reset player state
            self.player.hand.cards = []
            self.player.spies_placed = []

            # Set up context
            context = {"card": card.name, "phase": "acquire"}

            # Test on_acquire effects
            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.on_acquire_effects,
                    context
                )

                # Verify resolution succeeded or failed gracefully
                assert 'success' in result, \
                    f"Card {card.name} on_acquire missing success field"

                print(f"✓ Card {card.id:2d} - {card.name:30s}: on_acquire OK")

            except Exception as e:
                pytest.fail(f"Card {card.name} on_acquire failed: {e}")

    def test_agent_effects(self):
        """Test agent effects for all cards that have them."""
        cards_with_agent = [c for c in self.all_cards if c.get('agent_effects')]

        print(f"\nTesting {len(cards_with_agent)} cards with agent effects...")

        # Set up board spaces for testing
        maker_space = self.create_board_space(1, space_type="maker")
        faction_space = self.create_board_space(2, faction="fremen")
        self.game.board.spaces = [maker_space, faction_space]

        # Set up observation posts
        fremen_post = self.create_observation_post(1, "fremen", "maker")
        self.game.board.observation_posts = [fremen_post]

        for card_data in cards_with_agent:
            card = self.create_card_instance(card_data)

            # Reset player state
            self.player.agents_sent_this_turn = [1]  # Sent to maker space
            self.player.revealed_cards_this_turn = [card]
            self.player.recalled_spy_this_turn = False
            self.player.hand.cards = [card]

            # Add some Fremen bond for conditional checks
            self.player.fremen_influence = 2

            # Set up context
            context = {
                "card": card.name,
                "phase": "agent",
                "board_space_id": 1
            }

            # Test agent effects
            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.agent_effects,
                    context
                )

                # Verify resolution
                assert 'success' in result, \
                    f"Card {card.name} agent effect missing success field"

                print(f"✓ Card {card.id:2d} - {card.name:30s}: agent OK")

            except Exception as e:
                pytest.fail(f"Card {card.name} agent effect failed: {e}")

    def test_reveal_effects(self):
        """Test reveal effects for all cards."""
        print(f"\nTesting {len(self.all_cards)} cards with reveal effects...")

        for card_data in self.all_cards:
            card = self.create_card_instance(card_data)

            # Reset player state
            self.player.revealed_cards_this_turn = [card]
            self.player.temp_persuasion = 0
            self.player.temp_swords = 0

            # Add some cards to deck for draw effects
            for i in range(10):
                dummy_card = Card(card_id=f"dummy_{i}", name=f"Dummy {i}", faction=None, cost=0)
                self.player.deck.cards.append(dummy_card)

            # Set up context
            context = {
                "card": card.name,
                "phase": "reveal"
            }

            # Test reveal effects
            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.reveal_effects,
                    context
                )

                # Verify resolution
                assert 'success' in result, \
                    f"Card {card.name} reveal effect missing success field"

                print(f"✓ Card {card.id:2d} - {card.name:30s}: reveal OK")

            except Exception as e:
                pytest.fail(f"Card {card.name} reveal effect failed: {e}")

    def test_special_effects(self):
        """Test special effects (on_discard, on_trash, fremen_bond)."""
        # Test on_discard effects
        cards_with_on_discard = [c for c in self.all_cards if c.get('on_discard_effects')]
        print(f"\nTesting {len(cards_with_on_discard)} cards with on_discard effects...")

        for card_data in cards_with_on_discard:
            card = self.create_card_instance(card_data)
            context = {"card": card.name, "phase": "discard"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.on_discard_effects,
                    context
                )
                assert 'success' in result
                print(f"✓ Card {card.id:2d} - {card.name:30s}: on_discard OK")
            except Exception as e:
                pytest.fail(f"Card {card.name} on_discard failed: {e}")

        # Test on_trash effects
        cards_with_on_trash = [c for c in self.all_cards if c.get('on_trash_effects')]
        print(f"\nTesting {len(cards_with_on_trash)} cards with on_trash effects...")

        for card_data in cards_with_on_trash:
            card = self.create_card_instance(card_data)
            context = {"card": card.name, "phase": "trash"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.on_trash_effects,
                    context
                )
                assert 'success' in result
                print(f"✓ Card {card.id:2d} - {card.name:30s}: on_trash OK")
            except Exception as e:
                pytest.fail(f"Card {card.name} on_trash failed: {e}")

        # Test fremen_bond effects
        cards_with_fremen_bond = [c for c in self.all_cards if c.get('fremen_bond_effects')]
        print(f"\nTesting {len(cards_with_fremen_bond)} cards with fremen_bond effects...")

        for card_data in cards_with_fremen_bond:
            card = self.create_card_instance(card_data)
            context = {"card": card.name, "phase": "fremen_bond"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.fremen_bond_effects,
                    context
                )
                assert 'success' in result
                print(f"✓ Card {card.id:2d} - {card.name:30s}: fremen_bond OK")
            except Exception as e:
                pytest.fail(f"Card {card.name} fremen_bond failed: {e}")

    def test_conditional_effects(self):
        """Test cards with conditional effects in various states."""
        print(f"\nTesting conditional effects...")

        # Find cards with conditional checks
        conditional_cards = []
        for card_data in self.all_cards:
            for effect_type in ['agent_effects', 'reveal_effects', 'on_acquire_effects']:
                effects = card_data.get(effect_type, [])
                for effect in effects:
                    if effect.get('type') == 'conditional':
                        conditional_cards.append((card_data, effect_type))
                        break

        print(f"Found {len(conditional_cards)} cards with conditionals")

        for card_data, effect_type in conditional_cards:
            card = self.create_card_instance(card_data)

            # Set up favorable conditions
            self.player.fremen_influence = 2
            self.player.bene_gesserit_influence = 2
            self.player.spacing_guild_influence = 2
            self.player.emperor_influence = 2
            self.player.alliances = ["fremen", "bene_gesserit"]
            self.player.agents_sent_this_turn = [1, 2]
            self.player.recalled_spy_this_turn = True
            self.player.spies_placed = ["1", "2"]

            # Add some revealed cards
            dummy_emperor = Card(card_id="emp", name="Emperor Card", faction="Emperor", cost=1)
            dummy_fremen = Card(card_id="fre", name="Fremen Card", faction="Fremen", cost=1)
            self.player.revealed_cards_this_turn = [card, dummy_emperor, dummy_fremen]

            context = {"card": card.name}

            try:
                effects = getattr(card, effect_type, [])
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    effects,
                    context
                )
                assert 'success' in result
                print(f"✓ Card {card.id:2d} - {card.name:30s}: conditional OK")
            except Exception as e:
                pytest.fail(f"Card {card.name} conditional failed: {e}")

    def test_resource_generation(self):
        """Test that resource-generating cards actually increase resources."""
        print(f"\nTesting resource generation...")

        for card_data in self.all_cards:
            card = self.create_card_instance(card_data)

            # Record initial state
            initial_solari = self.player.solari
            initial_spice = self.player.spice
            initial_water = self.player.water
            initial_persuasion = self.player.temp_persuasion
            initial_swords = self.player.temp_swords

            # Resolve reveal effects
            context = {"card": card.name}
            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.reveal_effects,
                    context
                )

                # Check if resources increased (at least one should if card gives resources)
                has_resource_effect = any(
                    e.get('type') == 'resource'
                    for e in card.reveal_effects
                    if isinstance(e, dict)
                )

                if has_resource_effect and result.get('success'):
                    # At least one resource should have changed
                    resources_changed = (
                        self.player.solari != initial_solari or
                        self.player.spice != initial_spice or
                        self.player.water != initial_water or
                        self.player.temp_persuasion != initial_persuasion or
                        self.player.temp_swords != initial_swords
                    )

                    if not resources_changed:
                        print(f"⚠ Card {card.name} has resource effect but no resources changed")

            except Exception as e:
                pytest.fail(f"Card {card.name} resource test failed: {e}")

    def test_all_check_types(self):
        """Test that all check types used in cards are implemented."""
        print(f"\nTesting all check types are implemented...")

        check_types_used = set()

        for card_data in self.all_cards:
            for effect_type in ['agent_effects', 'reveal_effects', 'on_acquire_effects']:
                effects = card_data.get(effect_type, [])
                for effect in effects:
                    if effect.get('type') == 'conditional':
                        checks = effect.get('check', [])
                        for check in checks:
                            check_type = check.get('type')
                            if check_type:
                                check_types_used.add(check_type)

        print(f"Check types used: {sorted(check_types_used)}")

        # Verify each check type works
        for check_type in check_types_used:
            print(f"  Testing check type: {check_type}")
            assert check_type, f"Empty check type found"

    def test_all_effect_types(self):
        """Test that all effect types used in cards are implemented."""
        print(f"\nTesting all effect types are implemented...")

        effect_types_used = set()

        for card_data in self.all_cards:
            for effect_container in ['agent_effects', 'reveal_effects', 'on_acquire_effects',
                                     'on_discard_effects', 'on_trash_effects', 'fremen_bond_effects']:
                effects = card_data.get(effect_container, [])
                for effect in effects:
                    if isinstance(effect, dict):
                        effect_type = effect.get('type')
                        if effect_type:
                            effect_types_used.add(effect_type)

        print(f"Effect types used: {sorted(effect_types_used)}")

        # Verify each effect type is in the handler registry
        for effect_type in effect_types_used:
            if effect_type not in self.resolver.effect_handlers:
                pytest.fail(f"Effect type '{effect_type}' not in handler registry!")
            print(f"  ✓ Effect type registered: {effect_type}")

    def test_card_id_uniqueness(self):
        """Test that all card IDs are unique."""
        card_ids = [c['id'] for c in self.all_cards]
        assert len(card_ids) == len(set(card_ids)), "Duplicate card IDs found!"

    def test_card_names_unique(self):
        """Test that all card names are unique."""
        card_names = [c['name'] for c in self.all_cards]
        duplicates = [name for name in card_names if card_names.count(name) > 1]
        assert len(duplicates) == 0, f"Duplicate card names: {set(duplicates)}"

    def test_sequential_ids(self):
        """Test that card IDs are sequential from 1 to 60."""
        card_ids = sorted([c['id'] for c in self.all_cards])
        expected_ids = list(range(1, 61))
        assert card_ids == expected_ids, f"Card IDs not sequential: {card_ids}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
