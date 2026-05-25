#!/usr/bin/env python3
"""
DUNE: IMPERIUM UPRISING - Simple CLI
=====================================

A clean, streamlined command-line interface for playing DUNE: Imperium Uprising.

Features:
- Clear game state display
- Simple numbered menu choices
- Play against bots
- Auto-resolves complex choices for quick gameplay

Usage:
    python3 simple_cli.py
"""

import sys
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.engine.core.game_setup import GameSetup
from src.engine.managers.phase_manager import PhaseManager
from src.engine.managers.deck_manager import DeckManager
from src.engine.managers.combat_manager import CombatManager
from src.engine.managers.makers_manager import MakersManager
from src.engine.managers.influence_manager import InfluenceManager
from src.engine.managers.victory_point_manager import VictoryPointManager
from src.engine.actions.action_generator import ActionGenerator
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, RevealAction, AcquireCardAction, PlayIntrigueAction
from src.engine.effects.effect_resolver import EffectResolver
from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import ImperiumCard


class Colors:
    """ANSI color codes for terminal."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class SimpleCLI:
    """Simple command-line interface for DUNE Imperium."""

    def __init__(self):
        """Initialize the CLI."""
        self.game = None
        self.managers = {}
        self.human_player = None

    def clear_screen(self):
        """Clear the terminal screen."""
        print("\n" * 2)

    def print_header(self, text: str):
        """Print a styled header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{text.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.END}\n")

    def print_section(self, text: str):
        """Print a section header."""
        print(f"\n{Colors.BOLD}{Colors.YELLOW}{text}{Colors.END}")
        print(f"{Colors.YELLOW}{'-' * len(text)}{Colors.END}")

    def print_info(self, text: str):
        """Print info text."""
        print(f"{Colors.CYAN}{text}{Colors.END}")

    def print_success(self, text: str):
        """Print success message."""
        print(f"{Colors.GREEN}✓ {text}{Colors.END}")

    def print_error(self, text: str):
        """Print error message."""
        print(f"{Colors.RED}✗ {text}{Colors.END}")

    def get_input(self, prompt: str, valid_options: Optional[List[str]] = None) -> str:
        """Get user input with validation."""
        while True:
            try:
                choice = input(f"{Colors.BOLD}{prompt}{Colors.END} ").strip()
                if valid_options is None or choice in valid_options:
                    return choice
                self.print_error(f"Invalid choice. Please choose from: {', '.join(valid_options)}")
            except (KeyboardInterrupt, EOFError):
                print("\n\nGame interrupted. Goodbye!")
                sys.exit(0)

    def setup_game(self):
        """Set up a new game."""
        self.print_header("DUNE: IMPERIUM UPRISING")

        print("Welcome to DUNE: Imperium Uprising!")
        print("\nYou'll play against 2 AI opponents.")
        print("The game will guide you through each turn.\n")

        input("Press Enter to start...")

        self.print_section("Setting up game...")

        # Create game
        game, setup_info = GameSetup.create_game(player_count=3)
        self.game = game
        self.human_player = game.players[0]

        # Set up managers
        deck_manager = DeckManager(game)
        influence_manager = InfluenceManager(game)
        victory_point_manager = VictoryPointManager(game)
        effect_resolver = EffectResolver(game, influence_manager=influence_manager)
        combat_manager = CombatManager(game, effect_resolver=effect_resolver, victory_point_manager=victory_point_manager)
        makers_manager = MakersManager(game)
        phase_manager = PhaseManager(game, deck_manager=deck_manager, combat_manager=combat_manager, makers_manager=makers_manager)
        action_generator = ActionGenerator(game, phase_manager, effect_resolver)
        action_executor = ActionExecutor(game, phase_manager, deck_manager, effect_resolver)

        self.managers = {
            "phase_manager": phase_manager,
            "deck_manager": deck_manager,
            "combat_manager": combat_manager,
            "makers_manager": makers_manager,
            "action_generator": action_generator,
            "action_executor": action_executor,
            "influence_manager": influence_manager,
            "victory_point_manager": victory_point_manager,
            "effect_resolver": effect_resolver
        }

        self.print_success("Game initialized!")
        self.print_info(f"Players: {', '.join(p.name for p in game.players)}")
        self.print_info(f"You are: {self.human_player.name} ({self.human_player.color})")
        self.print_info(f"Your leader: {self.human_player.leader.name}")

        # Start the game - advance from SETUP to PLAYER_TURNS phase
        self.game.current_phase = GamePhase.PLAYER_TURNS
        self.game.current_round = 1

        time.sleep(2)

    def display_player_state(self, player: Player):
        """Display current player state."""
        self.print_section(f"{player.name}'s Status")

        # Resources
        print(f"  💰 Solari: {player.solari}  |  🧂 Spice: {player.spice}  |  💧 Water: {player.water}")
        print(f"  ⭐ Victory Points: {player.victory_points}")

        # Troops & Agents
        print(f"  🪖 Troops: {player.troops_in_garrison} garrison, {player.troops_in_conflict} in conflict")
        print(f"  👤 Agents: {player.agents_available}/{player.total_available_agents} available")
        print(f"  🕵️  Spies: {player.spies_available}/{player.total_available_spies} available")

        # Influence
        print(f"  🤝 Influence: F:{player.fremen_influence} B:{player.bene_gesserit_influence} " +
              f"S:{player.spacing_guild_influence} E:{player.emperor_influence}")

        # Cards
        print(f"  🎴 Hand: {len(player.hand.cards)} cards  |  📚 Deck: {len(player.deck.cards)} cards  " +
              f"|  🗑️  Discard: {len(player.discard_pile.cards)} cards")
        print(f"  🔍 Intrigue: {len(player.intrigue_cards)} cards")

    def display_hand(self, player: Player):
        """Display player's hand."""
        if not player.hand.cards:
            print("  (empty)")
            return

        for i, card in enumerate(player.hand.cards, 1):
            factions = ", ".join(card.factions) if hasattr(card, 'factions') and card.factions else "any"
            print(f"  {i}. {card.name} [{factions}]")

    def display_board_spaces(self, game: Game):
        """Display available board spaces."""
        self.print_section("Board Spaces")

        for i, space in enumerate(game.board.spaces[:10], 1):  # Show first 10
            status = "🔴 Occupied" if hasattr(space, 'occupied_by') and space.occupied_by else "🟢 Available"
            print(f"  {i}. {space.name:30s} {status}")

    def take_turn_human(self, player: Player):
        """Handle human player's turn."""
        self.clear_screen()
        self.print_header(f"{player.name}'s Turn")

        self.display_player_state(player)

        # Show hand
        self.print_section("Your Hand")
        self.display_hand(player)

        # Get action choice
        print("\nWhat would you like to do?")
        print("  1. Place agent (play card + use board space)")
        print("  2. Reveal hand (end agent phase)")
        print("  3. View board spaces")
        print("  4. View full game state")
        print("  5. Quit game")

        choice = self.get_input("\nChoice:", ["1", "2", "3", "4", "5"])

        if choice == "1":
            self.action_place_agent(player)
        elif choice == "2":
            self.action_reveal(player)
        elif choice == "3":
            self.display_board_spaces(self.game)
            input("\nPress Enter to continue...")
            self.take_turn_human(player)
        elif choice == "4":
            self.display_full_state()
            input("\nPress Enter to continue...")
            self.take_turn_human(player)
        elif choice == "5":
            print("\nThanks for playing!")
            sys.exit(0)

    def action_place_agent(self, player: Player):
        """Handle placing an agent action."""
        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]

        # Get playable cards
        playable_cards = action_gen.get_playable_imperium_cards(player.player_id)

        if not playable_cards:
            self.print_error("No playable cards! You must reveal.")
            time.sleep(2)
            self.action_reveal(player)
            return

        # Let player choose card
        print("\nChoose a card to play:")
        for i, card in enumerate(playable_cards, 1):
            factions = ", ".join(card.factions) if card.factions else "any"
            print(f"  {i}. {card.name} [{factions}]")
        print("  0. Cancel")

        choice = self.get_input("\nCard:", [str(i) for i in range(len(playable_cards) + 1)])

        if choice == "0":
            self.take_turn_human(player)
            return

        card = playable_cards[int(choice) - 1]

        # Get valid locations
        locations = action_gen.get_valid_locations_for_card(player.player_id, card)

        if not locations:
            self.print_error("No valid locations for this card!")
            time.sleep(2)
            self.take_turn_human(player)
            return

        # Let player choose location
        print(f"\nChoose location for {card.name}:")
        for i, (location, placement_type) in enumerate(locations, 1):
            status = f"({placement_type})" if placement_type != "normal" else ""
            print(f"  {i}. {location.name} {status}")
        print("  0. Cancel")

        choice = self.get_input("\nLocation:", [str(i) for i in range(len(locations) + 1)])

        if choice == "0":
            self.action_place_agent(player)
            return

        location, placement_type = locations[int(choice) - 1]

        # Execute placement
        action = PlaceAgentAction(
            player_id=player.player_id,
            card=card,
            location=location,
            placement_type=placement_type,
            troops_to_deploy=0
        )

        result = action_exec.execute_place_agent(action)

        if result.get("success"):
            self.print_success(f"Placed agent on {location.name}!")
            time.sleep(1)
        else:
            self.print_error(f"Failed: {result.get('error', 'Unknown error')}")
            time.sleep(2)
            self.take_turn_human(player)

    def action_reveal(self, player: Player):
        """Handle reveal action."""
        action_exec = self.managers["action_executor"]

        self.print_section("Revealing Hand")

        action = RevealAction(player_id=player.player_id)
        result = action_exec.execute_reveal(action)

        if result.get("success"):
            self.print_success("Hand revealed!")
            print(f"  Cards revealed: {result.get('cards_revealed', 0)}")
            time.sleep(2)
        else:
            self.print_error(f"Failed: {result.get('error', 'Unknown error')}")
            time.sleep(2)

    def display_full_state(self):
        """Display complete game state."""
        self.clear_screen()
        self.print_header("Full Game State")

        for player in self.game.players:
            self.display_player_state(player)
            print()

        self.display_board_spaces(self.game)

    def run(self):
        """Run the game loop."""
        self.setup_game()

        # For now, just show the initial state and let player take one turn
        self.clear_screen()
        self.print_header("Game Started!")

        self.take_turn_human(self.human_player)

        print("\n\nGame demo complete!")
        print("Full game loop with bot AI coming soon...")


def main():
    """Main entry point."""
    try:
        cli = SimpleCLI()
        cli.run()
    except KeyboardInterrupt:
        print("\n\nGame interrupted. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
