"""
Integration tests for all 60 Imperium cards in real game scenarios.

Tests each card's effects in a realistic game environment with:
- Real Card objects (not Mocks)
- Real game state
- Real board spaces
- Proper game setup
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.engine.effects.effect_resolver import EffectResolver
from src.models.player import Player
from src.models.card import Card, ImperiumCard, CardType
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace, ObservationPost
from src.models.game import Game
from src.engine.core.game_state import GameState


class ImperiumCardsIntegrationTest:
    """Integration tests for all Imperium cards in realistic game scenarios."""

    def __init__(self):
        """Initialize test suite."""
        # Load all imperium cards
        imperium_file = Path(__file__).parent.parent / "data" / "imperium.JSON"
        with open(imperium_file, 'r') as f:
            self.all_cards = json.load(f)

        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def create_real_card(self, card_data):
        """Create a real ImperiumCard instance from JSON data."""
        card = ImperiumCard(
            name=card_data['name'],
            type="imperium",
            card_type=CardType.IMPERIUM,
            id=str(card_data['id']),
            cost=card_data.get('cost', 0),
            factions=[card_data.get('faction')] if card_data.get('faction') else [],
            starting_hand=card_data.get('starting_deck', False),
            agent_effects=card_data.get('agent_effects', []),
            reveal_effects=card_data.get('reveal_effects', []),
            on_acquire_effects=card_data.get('on_acquire_effects', [])
        )
        return card

    def create_dummy_card(self, card_id, name, faction=None, cost=0):
        """Create a dummy ImperiumCard for testing."""
        return ImperiumCard(
            name=name,
            type="imperium",
            card_type=CardType.IMPERIUM,
            id=str(card_id),
            cost=cost,
            factions=[faction] if faction else [],
            starting_hand=False
        )

    def setup_game(self):
        """Set up a realistic game environment."""
        # Create game
        self.game = Game()
        self.game.player_count = 2

        # Create board with spaces
        self.game.board = Board()
        self.game.board.spaces = []

        # Add some board spaces
        for i in range(10):
            space = BoardSpace(
                id=str(i),
                name=f"Space {i}",
                agent_icon="any",
                faction="fremen" if i % 4 == 1 else ("spacing_guild" if i % 4 == 2 else ("emperor" if i % 4 == 3 else None)),
                is_maker_space=(i == 0)
            )
            self.game.board.spaces.append(space)

        # Create observation posts
        self.game.board.observation_posts = []
        for faction in ["fremen", "bene_gesserit", "spacing_guild", "emperor"]:
            post = ObservationPost(
                id=faction,
                name=faction.title().replace('_', ' ')
            )
            self.game.board.observation_posts.append(post)

        # Create mock leader
        mock_leader = type('Leader', (), {'name': 'Test Leader'})()

        # Create test player with full setup
        self.player = Player(
            player_id="test_player",
            name="Test Player",
            color="blue",
            leader=mock_leader,
            deck=Deck(),
            hand=Deck(),
            discard_pile=Deck()
        )

        # Set up player resources and state
        self.player.solari = 20
        self.player.spice = 10
        self.player.water = 10
        self.player.victory_points = 5

        # Troops
        self.player.troops_in_garrison = 5
        self.player.troops_in_conflict = 3
        self.player.troops_in_reserve = 5
        self.player.sandworms_in_conflict = 0

        # Influence
        self.player.fremen_influence = 2
        self.player.bene_gesserit_influence = 2
        self.player.spacing_guild_influence = 2
        self.player.emperor_influence = 2

        # Alliances
        self.player.fremen_alliance = False
        self.player.bene_gesserit_alliance = False
        self.player.spacing_guild_alliance = False
        self.player.emperor_alliance = False

        # Agents and spies
        self.player.total_available_agents = 2
        self.player.agents_available = 2
        self.player.agents_placed = []
        self.player.total_available_spies = 3
        self.player.spies_available = 3
        self.player.spies_placed = []

        # Turn state
        self.player.has_revealed_this_round = False
        self.player.played_cards_this_turn = []
        self.player.acquired_cards_this_turn = []
        self.player.discarded_cards_this_turn = []
        self.player.recalled_spy_this_turn = False
        self.player.placed_on_maker_this_turn = False
        self.player.revealed_cards_this_turn = []
        self.player.agents_sent_this_turn = [1]  # Sent agent to space 1
        self.player.trashed_cards = []

        # Other attributes
        self.player.has_high_council_sit = False
        self.player.controlled_locations = []
        self.player.intrigue_cards = []
        self.player.contracts_active = []
        self.player.contracts_completed = []
        self.player.conflict_cards_won = []
        self.player.objectives = []
        self.player.tag_pair_vp = 0

        # Add some dummy cards to deck
        factions = ["spacing_guild", "fremen", "emperor", "bene_gesserit", None]
        for i in range(15):
            dummy = self.create_dummy_card(
                f"dummy_{i}",
                f"Dummy {i}",
                factions[i % len(factions)],
                i % 5
            )
            self.player.deck.cards.append(dummy)

        # Add faction cards to played cards this turn
        for faction in ["spacing_guild", "fremen", "emperor", "bene_gesserit"]:
            faction_card = self.create_dummy_card(
                f"{faction}_play",
                f"{faction.title()} Card",
                faction,
                3
            )
            self.player.played_cards_this_turn.append(faction_card)

        # Add a discarded spacing_guild card for conditional checks
        guild_card = self.create_dummy_card("guild_discard", "Guild Discard", "spacing_guild", 2)
        self.player.discarded_cards_this_turn.append(guild_card)

        # Add some completed contracts
        for i in range(5):
            contract = type('Contract', (), {
                'id': f'contract_{i}',
                'name': f'Contract {i}'
            })()
            self.player.contracts_completed.append(contract)

        # Add some intrigue cards
        for i in range(5):
            intrigue = type('IntrigueCard', (), {
                'id': f'intrigue_{i}',
                'name': f'Intrigue {i}'
            })()
            self.player.intrigue_cards.append(intrigue)

        # Create game state
        self.game.players = [self.player]
        self.state = GameState(self.game)

        # Create effect resolver
        self.resolver = EffectResolver(self.game)

    def test_all_cards_load(self):
        """Test that all cards load correctly from JSON."""
        print("\n" + "="*80)
        print("TEST: All cards load correctly")
        print("="*80)

        try:
            starting_cards = [c for c in self.all_cards if c.get('starting_deck')]
            imperium_cards = [c for c in self.all_cards if not c.get('starting_deck')]

            print(f"Starting deck cards: {len(starting_cards)}")
            print(f"Imperium cards: {len(imperium_cards)}")
            print(f"Total cards: {len(self.all_cards)}")

            # Verify all cards can be created as real objects
            created_count = 0
            for card_data in self.all_cards:
                card = self.create_real_card(card_data)
                assert card.name == card_data['name']
                created_count += 1

            print(f"✓ All {created_count} cards created as real objects")
            print(f"  ({len(starting_cards)} starting + {len(imperium_cards)} imperium)")
            self.passed_tests += 1
            return True
        except Exception as e:
            print(f"✗ FAILED: {e}")
            self.failed_tests += 1
            return False

    def test_reveal_effects(self):
        """Test reveal effects for all cards in realistic game scenario."""
        print("\n" + "="*80)
        print("TEST: Reveal effects (Integration)")
        print("="*80)

        failed_cards = []

        for card_data in self.all_cards:
            self.setup_game()  # Fresh game setup for each card

            # Create real card
            card = self.create_real_card(card_data)

            # Add card to revealed cards this turn
            self.player.revealed_cards_this_turn.append(card)

            # Add card to hand
            self.player.hand.cards.append(card)

            context = {"card": card.name, "phase": "reveal"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.reveal_effects,
                    context
                )

                if 'success' not in result:
                    raise Exception("Missing success field in result")

                print(f"  ✓ Card {card.id:2s} - {card.name:35s}: reveal OK")

            except Exception as e:
                error_msg = str(e)[:80]
                print(f"  ✗ Card {card.id:2s} - {card.name:35s}: {error_msg}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            for name, error in failed_cards[:5]:  # Show first 5 errors
                print(f"    - {name}: {error[:100]}")
            if len(failed_cards) > 5:
                print(f"    ... and {len(failed_cards) - 5} more")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(self.all_cards)} cards passed reveal effects test")
            self.passed_tests += 1
            return True

    def test_agent_effects(self):
        """Test agent effects for all cards in realistic game scenario."""
        print("\n" + "="*80)
        print("TEST: Agent effects (Integration)")
        print("="*80)

        cards_with_agent = [c for c in self.all_cards if c.get('agent_effects')]
        print(f"Testing {len(cards_with_agent)} cards with agent effects...\n")

        failed_cards = []

        for card_data in cards_with_agent:
            self.setup_game()  # Fresh game setup

            # Create real card
            card = self.create_real_card(card_data)

            # Add to revealed cards and hand
            self.player.revealed_cards_this_turn.append(card)
            self.player.hand.cards.append(card)

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

                if 'success' not in result:
                    raise Exception("Missing success field in result")

                print(f"  ✓ Card {card.id:2s} - {card.name:35s}: agent OK")

            except Exception as e:
                error_msg = str(e)[:80]
                print(f"  ✗ Card {card.id:2s} - {card.name:35s}: {error_msg}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            for name, error in failed_cards[:5]:
                print(f"    - {name}: {error[:100]}")
            if len(failed_cards) > 5:
                print(f"    ... and {len(failed_cards) - 5} more")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(cards_with_agent)} cards passed agent effects test")
            self.passed_tests += 1
            return True

    def test_on_acquire_effects(self):
        """Test on_acquire effects for all cards in realistic game scenario."""
        print("\n" + "="*80)
        print("TEST: On-acquire effects (Integration)")
        print("="*80)

        cards_with_on_acquire = [c for c in self.all_cards if c.get('on_acquire_effects')]
        print(f"Testing {len(cards_with_on_acquire)} cards with on_acquire effects...\n")

        failed_cards = []

        for card_data in cards_with_on_acquire:
            self.setup_game()

            # Create real card
            card = self.create_real_card(card_data)

            context = {"card": card.name, "phase": "acquire"}

            try:
                result = self.resolver.resolve_effects(
                    self.player.player_id,
                    card.on_acquire_effects,
                    context
                )

                if 'success' not in result:
                    raise Exception("Missing success field in result")

                print(f"  ✓ Card {card.id:2s} - {card.name:35s}: on_acquire OK")

            except Exception as e:
                error_msg = str(e)[:80]
                print(f"  ✗ Card {card.id:2s} - {card.name:35s}: {error_msg}")
                failed_cards.append((card.name, str(e)))

        if failed_cards:
            print(f"\n✗ FAILED: {len(failed_cards)} cards failed")
            for name, error in failed_cards:
                print(f"    - {name}: {error[:100]}")
            self.failed_tests += 1
            return False
        else:
            print(f"\n✓ All {len(cards_with_on_acquire)} cards passed on_acquire test")
            self.passed_tests += 1
            return True

    def run_all_tests(self):
        """Run all integration tests."""
        print("\n" + "="*80)
        print("IMPERIUM CARDS INTEGRATION TEST SUITE")
        print("Testing with REAL game objects and state")
        print("="*80)

        self.test_all_cards_load()
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
            print("\n✓ ALL INTEGRATION TESTS PASSED!")
            return 0
        else:
            print(f"\n✗ {self.failed_tests} TEST(S) FAILED")
            return 1


if __name__ == "__main__":
    tester = ImperiumCardsIntegrationTest()
    exit_code = tester.run_all_tests()
    sys.exit(exit_code)
