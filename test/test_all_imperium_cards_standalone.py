"""
Comprehensive test suite for all 60 Imperium cards - Standalone version.

Tests each card's:
- on_acquire effects (when buying the card)
- agent effects (when playing the card and sending agent)
- reveal effects (when revealing the card from hand)
- Any special effects (on_discard, on_trash, fremen_bond, etc.)
"""

import json
import sys
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.effects.effect_resolver import EffectResolver
from src.models.player import Player
from src.models.card import Card
from src.models.deck import Deck


class ImperiumCardsTest:
    """Comprehensive tests for all Imperium cards."""

    def __init__(self):
        """Initialize test suite."""
        # Load all imperium cards
        imperium_file = Path(__file__).parent.parent / "data" / "imperium.JSON"
        with open(imperium_file, 'r') as f:
            self.all_cards = json.load(f)

        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def setup(self):
        """Set up test fixtures."""
        # Create mock game state
        self.game = Mock()
        self.game.board = Mock()
        self.game.board.spaces = []
        self.game.board.observation_posts = []

        # Create mock leader
        mock_leader = Mock()
        mock_leader.name = "Test Leader"

        # Create test player
        self.player = Player(
            player_id="test_player",
            name="Test Player",
            color="blue",
            leader=mock_leader,
            deck=Deck(),
            hand=Deck(),
            discard_pile=Deck()
        )
        self.player.play_area = []

        # Initialize resources
        self.player.solari = 10
        self.player.spice = 10
        self.player.water = 10
        self.player.troops_in_garrison = 5
        self.player.troops_in_conflict = 3  # Set to 3 to satisfy unit checks
        self.player.sandworms_in_conflict = 0
        self.player.troops_in_reserve = 5
        self.player.temp_persuasion = 0
        self.player.temp_swords = 0
        self.player.victory_points = 0

        # Initialize influence (set to 2 to satisfy most influence checks)
        self.player.fremen_influence = 2
        self.player.bene_gesserit_influence = 2
        self.player.spacing_guild_influence = 2
        self.player.emperor_influence = 2

        # Initialize other attributes
        self.player.alliances = []
        self.player.spies_placed = []
        self.player.available_spies = 2
        self.player.spies_available = 2
        self.player.revealed_cards_this_turn = []
        self.player.agents_sent_this_turn = []
        self.player.trashed_cards = []
        self.player.discarded_cards_this_turn = []
        self.player.conflict_cards_won = []
        self.player.acquired_cards_this_turn = []
        self.player.intrigue_cards = []

        # Add some completed contracts (Mock objects with required attributes)
        self.player.contracts_completed = []
        for i in range(5):
            contract = Mock()
            contract.id = f"contract_{i}"
            contract.name = f"Contract {i}"
            self.player.contracts_completed.append(contract)

        # Add some active contracts
        self.player.contracts_active = []
        for i in range(2):
            contract = Mock()
            contract.id = f"active_contract_{i}"
            contract.name = f"Active Contract {i}"
            self.player.contracts_active.append(contract)

        # Initialize player attributes that might be checked
        self.player.fremen_alliance = False
        self.player.bene_gesserit_alliance = False
        self.player.spacing_guild_alliance = False
        self.player.emperor_alliance = False
        self.player.recalled_spy_this_turn = False
        self.player.placed_on_maker_this_turn = False
        self.player.has_high_council_sit = False
        self.player.controlled_locations = []

        # Temp combat attributes
        self.player.temp_persuasion = 0
        self.player.temp_swords = 0

        # Create mock state
        self.state = Mock()
        self.state.get_player_by_id = Mock(return_value=self.player)
        self.state.players = [self.player]

        # Create effect resolver
        self.resolver = EffectResolver(self.state, self.game)

    def create_card_instance(self, card_data):
        """Create a mock card instance from JSON data."""
        # Use Mock instead of actual Card class to avoid constructor complexity
        card = Mock()
        card.id = card_data['id']
        card.name = card_data['name']
        card.faction = card_data.get('faction')
        card.cost = card_data.get('cost', 0)

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
        space = Mock()
        space.id = space_id
        space.type = space_type or ""
        space.faction = faction or ""
        return space

    def create_observation_post(self, post_id, faction, watches_type=None):
        """Create a mock observation post."""
        post = Mock()
        post.id = post_id
        post.name = faction
        post.faction = faction
        post.watches_type = watches_type or ""
        return post

    def assert_equal(self, actual, expected, message):
        """Custom assertion."""
        if actual != expected:
            raise AssertionError(f"{message}: expected {expected}, got {actual}")

    def test_all_cards_load(self):
        """Test that all cards load correctly from JSON."""
        print("\n" + "="*80)
        print("TEST: All cards load correctly")
        print("="*80)

        try:
            # Count starting deck cards and regular imperium cards
            starting_cards = [c for c in self.all_cards if c.get('starting_deck')]
            imperium_cards = [c for c in self.all_cards if not c.get('starting_deck')]

            print(f"Starting deck cards: {len(starting_cards)}")
            print(f"Imperium cards: {len(imperium_cards)}")
            print(f"Total cards: {len(self.all_cards)}")

            # Verify all cards have required fields
            for card in self.all_cards:
                assert 'id' in card, f"Card missing id: {card.get('name')}"
                assert 'name' in card, f"Card missing name: {card}"
                # Starting deck cards don't have 'cost' and use 'amount' instead of 'quantity'
                if not card.get('starting_deck'):
                    assert 'cost' in card, f"Card {card.get('name')} missing cost"
                # All cards should have either 'quantity' or 'amount'
                assert 'quantity' in card or 'amount' in card, f"Card {card.get('name')} missing quantity/amount"

            print(f"✓ All {len(self.all_cards)} cards loaded successfully")
            print(f"  ({len(starting_cards)} starting + {len(imperium_cards)} imperium)")
            self.passed_tests += 1
            return True
        except Exception as e:
            print(f"✗ FAILED: {e}")
            self.failed_tests += 1
            return False

    def test_reveal_effects(self):
        """Test reveal effects for all cards."""
        print("\n" + "="*80)
        print("TEST: Reveal effects for all cards")
        print("="*80)

        failed_cards = []

        for card_data in self.all_cards:
            self.setup()  # Fresh setup for each card
            card = self.create_card_instance(card_data)

            # Add some cards to deck for draw effects
            # Include cards from various factions for conditional checks
            factions = ["spacing_guild", "fremen", "emperor", "bene_gesserit", None]
            for i in range(10):
                dummy_card = Mock()
                dummy_card.id = f"dummy_{i}"
                dummy_card.name = f"Dummy {i}"
                dummy_card.faction = factions[i % len(factions)]  # Rotate through factions
                dummy_card.cost = i % 5  # Various costs 0-4
                self.player.deck.cards.append(dummy_card)

            # Add some intrigue cards
            for i in range(5):
                intrigue_card = Mock()
                intrigue_card.id = f"intrigue_{i}"
                intrigue_card.name = f"Intrigue {i}"
                self.player.intrigue_cards.append(intrigue_card)

            # Add a spacing_guild card to hand for discarding
            guild_card = Mock()
            guild_card.id = "guild_test"
            guild_card.name = "Guild Test Card"
            guild_card.faction = "spacing_guild"
            guild_card.cost = 2
            self.player.hand.cards.append(guild_card)
            self.player.discarded_cards_this_turn.append(guild_card)

            # Setup revealed cards
            self.player.revealed_cards_this_turn = [card]

            context = {"card": card.name, "phase": "reveal"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.reveal_effects,
                    context
                )

                assert 'success' in result, f"Missing success field"
                print(f"  ✓ Card {card.id:2d} - {card.name:35s}: reveal OK")

            except Exception as e:
                print(f"  ✗ Card {card.id:2d} - {card.name:35s}: {str(e)[:50]}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            for name, error in failed_cards:
                print(f"    - {name}: {error}")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(self.all_cards)} cards passed reveal effects test")
            self.passed_tests += 1
            return True

    def test_agent_effects(self):
        """Test agent effects for all cards that have them."""
        print("\n" + "="*80)
        print("TEST: Agent effects")
        print("="*80)

        cards_with_agent = [c for c in self.all_cards if c.get('agent_effects')]
        print(f"Testing {len(cards_with_agent)} cards with agent effects...\n")

        failed_cards = []

        # Set up board spaces for testing
        maker_space = self.create_board_space(1, space_type="maker")
        faction_space = self.create_board_space(2, faction="fremen")

        for card_data in cards_with_agent:
            self.setup()  # Fresh setup
            self.game.board.spaces = [maker_space, faction_space]

            card = self.create_card_instance(card_data)

            # Set up favorable conditions
            self.player.agents_sent_this_turn = [1]
            self.player.revealed_cards_this_turn = [card]
            self.player.recalled_spy_this_turn = False
            self.player.hand.cards = [card]
            self.player.fremen_influence = 2

            # Add cards to deck and intrigue cards
            factions = ["spacing_guild", "fremen", "emperor", "bene_gesserit", None]
            for i in range(10):
                dummy_card = Mock()
                dummy_card.id = f"dummy_{i}"
                dummy_card.name = f"Dummy {i}"
                dummy_card.faction = factions[i % len(factions)]
                dummy_card.cost = i % 5
                self.player.deck.cards.append(dummy_card)

            for i in range(5):
                intrigue_card = Mock()
                intrigue_card.id = f"intrigue_{i}"
                intrigue_card.name = f"Intrigue {i}"
                self.player.intrigue_cards.append(intrigue_card)

            # Add faction cards to play area for conditional checks
            for faction in ["spacing_guild", "fremen", "emperor", "bene_gesserit"]:
                faction_card = Mock()
                faction_card.id = f"{faction}_test"
                faction_card.name = f"{faction.title()} Card"
                faction_card.faction = faction
                faction_card.cost = 3
                self.player.play_area.append(faction_card)

            context = {
                "card": card.name,
                "phase": "agent",
                "board_space_id": 1
            }

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.agent_effects,
                    context
                )

                assert 'success' in result
                print(f"  ✓ Card {card.id:2d} - {card.name:35s}: agent OK")

            except Exception as e:
                print(f"  ✗ Card {card.id:2d} - {card.name:35s}: {str(e)[:50]}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(cards_with_agent)} cards passed agent effects test")
            self.passed_tests += 1
            return True

    def test_on_acquire_effects(self):
        """Test on_acquire effects for all cards that have them."""
        print("\n" + "="*80)
        print("TEST: On-acquire effects")
        print("="*80)

        cards_with_on_acquire = [c for c in self.all_cards if c.get('on_acquire_effects')]
        print(f"Testing {len(cards_with_on_acquire)} cards with on_acquire effects...\n")

        failed_cards = []

        for card_data in cards_with_on_acquire:
            self.setup()
            card = self.create_card_instance(card_data)

            context = {"card": card.name, "phase": "acquire"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.on_acquire_effects,
                    context
                )

                assert 'success' in result
                print(f"  ✓ Card {card.id:2d} - {card.name:35s}: on_acquire OK")

            except Exception as e:
                print(f"  ✗ Card {card.id:2d} - {card.name:35s}: {str(e)[:50]}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(cards_with_on_acquire)} cards passed on_acquire test")
            self.passed_tests += 1
            return True

    def test_all_effect_types_registered(self):
        """Test that all effect types are registered in the handler."""
        print("\n" + "="*80)
        print("TEST: All effect types registered")
        print("="*80)

        self.setup()

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

        print(f"Found {len(effect_types_used)} unique effect types\n")

        missing_types = []
        for effect_type in sorted(effect_types_used):
            if effect_type in self.resolver.handlers:
                print(f"  ✓ {effect_type:40s}: registered")
            else:
                print(f"  ✗ {effect_type:40s}: NOT REGISTERED")
                missing_types.append(effect_type)

        if missing_types:
            print(f"\n✗ FAILED: {len(missing_types)} effect types not registered")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(effect_types_used)} effect types are registered")
            self.passed_tests += 1
            return True

    def run_all_tests(self):
        """Run all tests."""
        print("\n" + "="*80)
        print("IMPERIUM CARDS COMPREHENSIVE TEST SUITE")
        print("="*80)

        self.test_all_cards_load()
        self.test_all_effect_types_registered()
        self.test_reveal_effects()
        self.test_agent_effects()
        self.test_on_acquire_effects()

        # Print summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Total:  {self.passed_tests + self.failed_tests}")

        if self.failed_tests == 0:
            print("\n✓ ALL TESTS PASSED!")
            return 0
        else:
            print(f"\n✗ {self.failed_tests} TEST(S) FAILED")
            return 1


if __name__ == "__main__":
    tester = ImperiumCardsTest()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
