#!/usr/bin/env python3
"""
DUNE: IMPERIUM UPRISING - Simple CLI
=====================================

A clean, streamlined command-line interface for playing DUNE: Imperium Uprising.

Features:
- Clear game state display
- Simple numbered menu choices
- Play against bots
- Full game loop with all phases

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
from src.bots import RandomBot


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
        self.bots = {}

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

    def print_bot_action(self, text: str):
        """Print bot action in distinct color."""
        print(f"{Colors.BLUE}🤖 {text}{Colors.END}")

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
            "effect_resolver": effect_resolver,
            "game": game
        }

        # Create bots for AI players
        for player in game.players[1:]:  # Skip human player
            self.bots[player.player_id] = RandomBot(player, self.managers)

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

        for i, space in enumerate(game.board.spaces[:15], 1):  # Show first 15
            status = "🔴 Occupied" if hasattr(space, 'occupied_by') and space.occupied_by else "🟢 Available"

            # Show maker space bonus
            spice_info = ""
            if hasattr(space, 'is_maker_space') and space.is_maker_space and hasattr(space, 'spice_bonus'):
                if space.spice_bonus > 0:
                    spice_info = f" [+{space.spice_bonus} 🧂]"

            # Show cost if any
            cost_info = ""
            if hasattr(space, 'cost') and space.cost:
                costs = []
                for c in space.cost:
                    if c.get('type') == 'resource':
                        resource = c.get('resource', '')
                        amount = c.get('amount', 0)
                        costs.append(f"{amount} {resource}")
                if costs:
                    cost_info = f" (Cost: {', '.join(costs)})"

            # Show rewards
            reward_info = ""
            if hasattr(space, 'reward') and space.reward:
                rewards = []
                for r in space.reward:
                    if r.get('type') == 'resource':
                        resource = r.get('resource', '')
                        amount = r.get('amount', 0)
                        rewards.append(f"+{amount} {resource}")
                    elif r.get('type') == 'influence':
                        faction = r.get('faction', '')
                        amount = r.get('amount', 0)
                        rewards.append(f"+{amount} {faction}")
                if rewards:
                    reward_info = f" → {', '.join(rewards)}"

            print(f"  {i}. {space.name:30s} {status}{cost_info}{reward_info}{spice_info}")

    def display_imperium_row(self):
        """Display the imperium row."""
        self.print_section("Imperium Row (Cards for Purchase)")

        if hasattr(self.game.board, 'imperium_row') and self.game.board.imperium_row:
            for i, card in enumerate(self.game.board.imperium_row, 1):
                if card:
                    factions = ", ".join(card.factions) if hasattr(card, 'factions') and card.factions else "any"
                    print(f"  {i}. {card.name:30s} [{factions}] Cost: {card.cost} persuasion")
        else:
            print("  (imperium row not available)")

    def take_turn_human(self, player: Player):
        """Handle human player's turn."""
        self.clear_screen()
        self.print_header(f"Round {self.game.current_round} - {player.name}'s Turn")

        self.display_player_state(player)

        # Show hand
        self.print_section("Your Hand")
        self.display_hand(player)

        # Get action choice
        print("\nWhat would you like to do?")
        print("  1. Place agent (play card + use board space)")
        print("  2. Reveal hand (end agent phase)")
        print("  3. View board spaces")
        print("  4. View imperium row")
        print("  5. View all players")
        print("  6. Quit game")

        choice = self.get_input("\nChoice:", ["1", "2", "3", "4", "5", "6"])

        if choice == "1":
            self.action_place_agent(player)
        elif choice == "2":
            self.action_reveal(player)
        elif choice == "3":
            self.display_board_spaces(self.game)
            input("\nPress Enter to continue...")
            self.take_turn_human(player)
        elif choice == "4":
            self.display_imperium_row()
            input("\nPress Enter to continue...")
            self.take_turn_human(player)
        elif choice == "5":
            self.display_full_state()
            input("\nPress Enter to continue...")
            self.take_turn_human(player)
        elif choice == "6":
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

            # Show if combat space
            combat_marker = ""
            if hasattr(location, 'is_combat_space') and location.is_combat_space:
                combat_marker = "⚔️  "

            # Show cost
            cost_info = ""
            if hasattr(location, 'cost') and location.cost:
                costs = []
                for c in location.cost:
                    if c.get('type') == 'resource':
                        resource = c.get('resource', '')
                        amount = c.get('amount', 0)
                        costs.append(f"{amount} {resource}")
                if costs:
                    cost_info = f" [Cost: {', '.join(costs)}]"

            # Show rewards
            reward_info = ""
            if hasattr(location, 'reward') and location.reward:
                rewards = []
                for r in location.reward:
                    if r.get('type') == 'resource':
                        resource = r.get('resource', '')
                        amount = r.get('amount', 0)
                        rewards.append(f"+{amount} {resource}")
                    elif r.get('type') == 'influence':
                        faction = r.get('faction', '')
                        amount = r.get('amount', 0)
                        rewards.append(f"+{amount} {faction}")
                    elif r.get('type') == 'draw':
                        deck = r.get('deck', 'card')
                        amount = r.get('amount', 1)
                        rewards.append(f"+{amount} {deck}")
                if rewards:
                    reward_info = f" → {', '.join(rewards)}"

            print(f"  {i}. {combat_marker}{location.name:30s} {status}{cost_info}{reward_info}")
        print("  0. Cancel")

        choice = self.get_input("\nLocation:", [str(i) for i in range(len(locations) + 1)])

        if choice == "0":
            self.action_place_agent(player)
            return

        location, placement_type = locations[int(choice) - 1]

        # Ask about troops if this is a combat space and player has troops
        troops_to_deploy = 0
        if placement_type == "normal" and player.troops_in_garrison > 0:
            # Check if this is a combat space
            if hasattr(location, 'is_combat_space') and location.is_combat_space:
                print(f"\n⚔️  {location.name} is a combat space!")
                print(f"You have {player.troops_in_garrison} troops in garrison.")
                print("How many troops to deploy to the conflict? (0-2)")
                max_troops = min(2, player.troops_in_garrison)
                troop_choice = self.get_input("Troops:", [str(i) for i in range(max_troops + 1)])
                troops_to_deploy = int(troop_choice)

        # Execute placement
        action = PlaceAgentAction(
            player_id=player.player_id,
            card=card,
            location=location,
            placement_type=placement_type,
            troops_to_deploy=troops_to_deploy
        )

        result = action_exec.execute_place_agent(action)

        if result.get("success"):
            self.print_success(f"Placed agent on {location.name}!")
            if troops_to_deploy > 0:
                self.print_info(f"  Deployed {troops_to_deploy} troops to conflict")

            # Check if signet ring was played
            if card.name == "Signet Ring" and player.leader:
                self.print_section(f"⚡ {player.leader.name}'s Signet Ability")
                self.print_info(f"  Note: Signet abilities are currently auto-resolved")
                # TODO: Implement interactive signet ability choices

            # Show what was gained
            if 'effects_applied' in result and result['effects_applied']:
                self.print_section("Rewards Gained")
                for effect in result['effects_applied']:
                    if isinstance(effect, dict):
                        self.print_info(f"  • {effect}")
                    else:
                        self.print_info(f"  • {effect}")

            # Show current resources after placement
            self.print_info(f"\n  Current resources: 💰{player.solari} 🧂{player.spice} 💧{player.water}")
            self.print_info(f"  Troops: {player.troops_in_garrison} garrison, {player.troops_in_conflict} in conflict")

            time.sleep(2)
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

    def take_turn_bot(self, player: Player):
        """Handle bot player's turn."""
        bot = self.bots[player.player_id]
        action_exec = self.managers["action_executor"]

        self.print_bot_action(f"{player.name} is thinking...")
        time.sleep(0.5)

        # Bot decides action
        action = bot.decide_agent_action()

        if action is None:
            # Bot wants to reveal
            self.print_bot_action(f"{player.name} reveals their hand")
            reveal_action = RevealAction(player_id=player.player_id)
            result = action_exec.execute_reveal(reveal_action)
            if result.get("success"):
                self.print_info(f"  Revealed {result.get('cards_revealed', 0)} cards")
        else:
            # Bot places agent
            self.print_bot_action(f"{player.name} plays {action.card.name} on {action.location.name}")
            result = action_exec.execute_place_agent(action)
            if result.get("success"):
                if action.troops_to_deploy > 0:
                    self.print_info(f"  Deployed {action.troops_to_deploy} troops")
            else:
                self.print_error(f"  Bot action failed: {result.get('error')}")

        time.sleep(1)

    def run_agent_phase(self):
        """Run the agent placement phase for all players."""
        self.print_header(f"Round {self.game.current_round} - Agent Phase")

        # Reset revealed status for all players
        for player in self.game.players:
            player.has_revealed_this_round = False

        # Keep going until all players have revealed
        while not all(p.has_revealed_this_round for p in self.game.players):
            for player in self.game.players:
                if player.has_revealed_this_round:
                    continue

                # Check if player still has agents
                if player.agents_available <= 0:
                    player.has_revealed_this_round = True
                    continue

                if player == self.human_player:
                    self.take_turn_human(player)
                else:
                    self.take_turn_bot(player)

    def run_reveal_phase(self):
        """Run the reveal phase."""
        self.print_header(f"Round {self.game.current_round} - Reveal Phase")
        self.print_info("Processing reveal effects for all players...")

        # Process reveal effects for each player who revealed
        for player in self.game.players:
            if player.has_revealed_this_round:
                # Reveal effects are processed automatically when they revealed
                pass

        self.print_success("Reveal phase complete")
        time.sleep(1)

    def run_combat_phase(self):
        """Run the combat phase."""
        combat_manager = self.managers["combat_manager"]

        self.print_header(f"Round {self.game.current_round} - Combat Phase")

        # Show current conflict
        if hasattr(self.game, 'current_conflict') and self.game.current_conflict:
            conflict = self.game.current_conflict
            self.print_section(f"Conflict: {conflict.name}")
            print(f"  Rewards: {conflict.rewards}")

        # Ask human player about troop deployment
        if self.human_player.troops_in_garrison > 0:
            print(f"\nYou have {self.human_player.troops_in_garrison} troops available.")
            print("How many troops to deploy to conflict?")
            max_troops = min(8, self.human_player.troops_in_garrison)
            choice = self.get_input(f"Troops (0-{max_troops}):", [str(i) for i in range(max_troops + 1)])
            troops = int(choice)
            if troops > 0:
                self.human_player.troops_in_conflict += troops
                self.human_player.troops_in_garrison -= troops
                self.print_success(f"Deployed {troops} troops to conflict")

        # Bots deploy troops
        for player in self.game.players[1:]:
            bot = self.bots[player.player_id]
            troops = bot.decide_troops_to_deploy(player.troops_in_garrison)
            if troops > 0:
                player.troops_in_conflict += troops
                player.troops_in_garrison -= troops
                self.print_bot_action(f"{player.name} deploys {troops} troops")

        # Resolve combat
        self.print_info("\nResolving combat...")
        result = combat_manager.resolve_combat()

        if result.get("success"):
            self.print_success("Combat resolved!")
            if "winners" in result:
                for winner_id in result["winners"]:
                    winner = self.game.get_player_by_id(winner_id)
                    self.print_success(f"  {winner.name} wins combat!")

        time.sleep(2)

    def run_makers_phase(self):
        """Run the MAKERS phase."""
        makers_manager = self.managers["makers_manager"]

        self.print_header(f"Round {self.game.current_round} - MAKERS Phase")

        result = makers_manager.execute_makers_phase()

        if result.get("success"):
            total_spice = result.get("total_bonus_added", 0)
            if total_spice > 0:
                self.print_success(f"Added {total_spice} bonus spice to unoccupied maker spaces")
            else:
                self.print_info("No maker spaces to update")

        time.sleep(1)

    def run_recall_phase(self):
        """Run the recall phase."""
        phase_manager = self.managers["phase_manager"]
        deck_manager = self.managers["deck_manager"]

        self.print_header(f"Round {self.game.current_round} - Recall Phase")

        # Recall agents and draw cards
        for player in self.game.players:
            # Reset agents
            player.agents_available = player.total_available_agents
            player.has_revealed_this_round = False

            # Draw cards
            deck_manager.draw_cards(player.player_id, 5)

            if player == self.human_player:
                self.print_success(f"Your agents recalled, drew 5 cards")
            else:
                self.print_bot_action(f"{player.name} recalls agents and draws cards")

        # Clean up board
        for space in self.game.board.spaces:
            if hasattr(space, 'occupied_by'):
                space.occupied_by = None

        time.sleep(1)

    def check_game_end(self) -> bool:
        """Check if game has ended."""
        # Game ends when someone reaches 10 VP
        for player in self.game.players:
            if player.victory_points >= 10:
                return True

        # Or after 10 rounds
        if self.game.current_round >= 10:
            return True

        return False

    def display_final_scores(self):
        """Display final scores and winner."""
        self.print_header("GAME OVER")

        self.print_section("Final Scores")

        # Sort players by VP
        sorted_players = sorted(self.game.players, key=lambda p: p.victory_points, reverse=True)

        for i, player in enumerate(sorted_players, 1):
            prefix = "🏆" if i == 1 else f"{i}."
            print(f"  {prefix} {player.name:20s} {player.victory_points} VP")

        winner = sorted_players[0]
        print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{winner.name} WINS!{Colors.END}".center(88))
        print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.END}\n")

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

        # Main game loop
        while not self.check_game_end():

            # Agent Phase
            self.run_agent_phase()

            # Reveal Phase
            self.run_reveal_phase()

            # Combat Phase
            self.run_combat_phase()
            
            # MAKERS Phase
            self.run_makers_phase()

            # Recall Phase
            self.run_recall_phase()

            # Next round
            self.game.current_round += 1

        # Game ended
        self.display_final_scores()


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
