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
from src.engine.managers.contract_manager import ContractManager
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


def _format_contract_rewards(rewards) -> str:
    """Format a contract's reward list into a readable string."""
    if not rewards:
        return "none"
    parts = []
    for r in rewards:
        rtype = r.get("type", "")
        if rtype == "resource":
            parts.append(f"+{r.get('amount', 1)} {r.get('resource', '?')}")
        elif rtype == "influence":
            parts.append(f"+{r.get('amount', 1)} {r.get('target', '?')} influence")
        elif rtype == "accept":
            parts.append("accept a contract")
        elif rtype == "draw":
            parts.append(f"draw {r.get('amount', 1)} {r.get('deck', 'card')}(s)")
        else:
            parts.append(rtype)
    return ", ".join(parts)


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

        contract_manager = ContractManager(game)

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
            "contract_manager": contract_manager,
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

        # Draw first conflict
        if self.game.board.conflict_deck:
            self.game.board.current_conflict = self.game.board.conflict_deck.pop(0)
            self.print_success(f"First conflict: {self.game.board.current_conflict.name}")

        time.sleep(2)

    def display_conflict_status(self):
        """Display current conflict and player combat strength."""
        if not self.game.board.current_conflict:
            return

        conflict = self.game.board.current_conflict

        self.print_section(f"⚔️  Current Conflict: {conflict.name}")

        # Show conflict rewards
        if hasattr(conflict, 'rewards') and conflict.rewards:
            print(f"  Rewards:")
            for rank, reward_list in conflict.rewards.items():
                reward_strs = []
                for r in reward_list:
                    if r.get('type') == 'resource':
                        reward_strs.append(f"+{r.get('amount', 0)} {r.get('resource', '')}")
                    elif r.get('type') == 'victory_points':
                        reward_strs.append(f"+{r.get('amount', 0)} VP")
                    elif r.get('type') == 'influence':
                        reward_strs.append(f"+{r.get('amount', 0)} {r.get('target', '')} influence")
                if reward_strs:
                    print(f"    {rank}: {', '.join(reward_strs)}")

        # Show player combat strength
        print(f"\n  Combat Strength:")
        for player in sorted(self.game.players, key=lambda p: p.troops_in_conflict, reverse=True):
            strength_icon = "🏆" if player.troops_in_conflict > 0 else "  "
            print(f"    {strength_icon} {player.name:20s} {player.troops_in_conflict} troops")

    def display_player_state(self, player: Player):
        """Display current player state."""
        self.print_section(f"{player.name}'s Status")

        # Show objectives
        if hasattr(player, 'objectives') and player.objectives:
            obj_names = [obj.name for obj in player.objectives]
            print(f"  🎯 Objective: {', '.join(obj_names)}")

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

        # Active contracts
        if getattr(player, 'contracts_active', []):
            print(f"\n  📋 Active Contracts ({len(player.contracts_active)}):")
            for c in player.contracts_active:
                ctype = c.completion_type
                if ctype == "harvest":
                    cond = f"harvest {c.required_spice} spice"
                elif ctype == "location":
                    cond = f"visit {c.completion_target or '?'}"
                elif ctype == "acquire_card":
                    cond = f"buy {c.completion_target or 'any card'}"
                else:
                    cond = ctype
                rewards_str = _format_contract_rewards(c.rewards)
                print(f"    • {c.name}: {cond} → {rewards_str}")

        # Completed contracts
        if getattr(player, 'contracts_completed', []):
            print(f"  ✅ Completed Contracts: {len(player.contracts_completed)}")

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
        """Display the imperium row and contract row."""
        self.print_section("Imperium Row (Cards for Purchase)")

        if hasattr(self.game.board, 'imperium_row') and self.game.board.imperium_row:
            for i, card in enumerate(self.game.board.imperium_row, 1):
                if card:
                    factions = ", ".join(card.factions) if hasattr(card, 'factions') and card.factions else "any"
                    print(f"  {i}. {card.name:30s} [{factions}] Cost: {card.cost} persuasion")
        else:
            print("  (imperium row not available)")

        # Reserve piles
        prepare = getattr(self.game.board, 'reserve_prepare_the_way', [])
        spice_flow = getattr(self.game.board, 'reserve_spice_must_flow', [])
        if prepare or spice_flow:
            print(f"\n  🔮 Reserve Piles:")
            if prepare:
                print(f"    Prepare the Way   — Cost: 2   ×{len(prepare)} remaining")
            if spice_flow:
                print(f"    The Spice Must Flow — Cost: 8  ×{len(spice_flow)} remaining")

        # Contract row
        self.display_contract_row()

    def display_contract_row(self):
        """Display the two visible contracts in the contract row."""
        contract_row = getattr(self.game.board, 'contract_row', [])
        if not contract_row:
            return

        self.print_section("Contract Row")
        for i, c in enumerate(contract_row[:2], 1):
            if c.completion_type == "harvest":
                cond = f"harvest {c.required_spice} spice"
            elif c.completion_type == "location":
                cond = f"visit {c.completion_target or '?'}"
            elif c.completion_type == "acquire_card":
                cond = f"buy {c.completion_target or 'any card'}"
            else:
                cond = c.completion_type
            rewards_str = _format_contract_rewards(c.rewards)
            print(f"  {i}. {c.name:20s} Complete: {cond:30s} → {rewards_str}")

    def take_turn_human(self, player: Player):
        """Handle human player's turn."""
        self.clear_screen()
        self.print_header(f"Round {self.game.current_round} - {player.name}'s Turn")

        # Show conflict status first
        self.display_conflict_status()

        # Show contract row (always visible)
        self.display_contract_row()

        # Then show player status
        self.display_player_state(player)

        # Show hand
        self.print_section("Your Hand")
        self.display_hand(player)

        # Detect plot intrigues
        plot_intrigues = [
            c for c in player.intrigue_cards
            if hasattr(c, 'phases') and any(p.value == 'Plot' for p in c.phases)
        ]

        # Get action choice
        print("\nWhat would you like to do?")
        print("  1. Place agent (play card + use board space)")
        print("  2. Reveal hand (end agent phase)")
        print("  3. View board spaces")
        print("  4. View imperium row")
        print("  5. View all players")
        if plot_intrigues:
            print(f"  6. Play plot intrigue ({len(plot_intrigues)} available)")
            print("  7. Quit game")
            valid = ["1", "2", "3", "4", "5", "6", "7"]
        else:
            print("  6. Quit game")
            valid = ["1", "2", "3", "4", "5", "6"]

        choice = self.get_input("\nChoice:", valid)

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
        elif choice == "6" and plot_intrigues:
            self.action_play_plot_intrigue(player, plot_intrigues)
        else:
            print("\nThanks for playing!")
            sys.exit(0)

    def action_play_plot_intrigue(self, player: Player, plot_intrigues):
        """Let player play a plot-phase intrigue card during their agent turn."""
        action_exec = self.managers["action_executor"]

        print("\nYour plot intrigue cards:")
        for i, card in enumerate(plot_intrigues, 1):
            print(f"  [{i}] {card.name}")
        print("  [0] Cancel")

        choice = self.get_input("Choice:", [str(i) for i in range(len(plot_intrigues) + 1)])
        if choice == "0":
            self.take_turn_human(player)
            return

        card = plot_intrigues[int(choice) - 1]
        result = action_exec.execute_play_intrigue(PlayIntrigueAction(
            player_id=player.player_id, intrigue_card=card
        ))
        if result.get("success"):
            self.print_success(f"Played intrigue: {card.name}")
            effects = result.get("effects", {}).get("effects_applied", [])
            for eff in effects:
                self.print_info(f"  • {eff}")
            # Resolve any choices the intrigue raised
            self._resolve_choices(player, result.get("choices_required", []))
        else:
            self.print_error(f"Cannot play: {result.get('error','')}")

        time.sleep(2)
        self.take_turn_human(player)

    def _resolve_choices(self, player: Player, choices_required: list):
        """Interactively resolve choice effects that need player input."""
        if not choices_required:
            return

        effect_resolver = self.managers["effect_resolver"]
        is_human = (player == self.human_player)
        import random as _random

        for choice_data in choices_required:
            ctype = choice_data.get("type")

            if ctype == "choice":
                # Generic option list with {id, label, available}
                options = choice_data.get("options", [])
                available = [o for o in options if o.get("available", True)]
                if not available:
                    continue
                if is_human:
                    print(f"\n  Choose one:")
                    for i, opt in enumerate(available, 1):
                        label = opt.get("label", opt.get("id", "?"))
                        print(f"    [{i}] {label}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(available)+1)])
                    chosen = available[int(sel)-1]
                else:
                    chosen = _random.choice(available)
                    self.print_info(f"  {player.name} chooses: {chosen.get('label', chosen.get('id'))}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen["id"])

            elif ctype == "spy_post":
                posts = choice_data.get("available_posts", [])
                if not posts:
                    continue
                if is_human:
                    print(f"\n  Place spy on which observation post?")
                    for i, p in enumerate(posts, 1):
                        controls = p.get("controlled_spaces", p.get("connected_locations", []))
                        ctrl_str = f" (controls: {', '.join(controls)})" if controls else ""
                        print(f"    [{i}] {p.get('post_name')}{ctrl_str}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(posts)+1)])
                    chosen = posts[int(sel)-1]
                else:
                    chosen = _random.choice(posts)
                    self.print_info(f"  {player.name} places spy on {chosen.get('post_name')}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen["post_id"])

            elif ctype == "influence_faction":
                factions = choice_data.get("factions", [])
                if not factions:
                    continue
                if is_human:
                    print(f"\n  Choose a faction to gain influence:")
                    for i, f in enumerate(factions, 1):
                        print(f"    [{i}] {f}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(factions)+1)])
                    chosen = factions[int(sel)-1]
                else:
                    chosen = _random.choice(factions)
                    self.print_info(f"  {player.name} gains influence with {chosen}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen)

            elif ctype == "conditional":
                # accept/decline a cost-for-reward trade
                if is_human:
                    costs = choice_data.get("costs", [])
                    rewards = choice_data.get("rewards", [])
                    print(f"\n  Optional: pay {costs} to gain {rewards}?")
                    sel = self.get_input("  [1] Accept  [2] Decline:", ["1", "2"])
                    chosen_id = "accept" if sel == "1" else "decline"
                else:
                    chosen_id = "accept" if _random.random() < 0.5 else "decline"
                effect_resolver.execute_choice(player.player_id, choice_data, chosen_id)

            elif ctype == "trash_card":
                # Pick a card from hand/played/intrigue/discard to trash
                cards = choice_data.get("available_cards", [])
                if not cards:
                    continue
                if is_human:
                    print(f"\n  Trash which card?")
                    for i, ci in enumerate(cards, 1):
                        print(f"    [{i}] {ci['card'].name} (from {ci['source']})")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(cards)+1)])
                    chosen = cards[int(sel)-1]
                else:
                    chosen = _random.choice(cards)
                    self.print_info(f"  {player.name} trashes {chosen['card'].name}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen["card"].id)

            elif ctype == "trash_to_acquire":
                cards = choice_data.get("available_cards", [])
                if not cards:
                    continue
                if is_human:
                    print(f"\n  Trash which card from hand (to unlock acquisition)?")
                    for i, c in enumerate(cards, 1):
                        # cards here might be card objects directly, not {card, source}
                        name = c.name if hasattr(c, 'name') else c.get('card', c).name
                        print(f"    [{i}] {name}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(cards)+1)])
                    chosen = cards[int(sel)-1]
                else:
                    chosen = _random.choice(cards)
                    name = chosen.name if hasattr(chosen, 'name') else chosen.get('card', chosen).name
                    self.print_info(f"  {player.name} trashes {name}")
                cid = chosen.id if hasattr(chosen, 'id') else chosen.get('card', chosen).id
                effect_resolver.execute_choice(player.player_id, choice_data, cid)

            elif ctype == "steal_intrigue":
                targets = choice_data.get("valid_targets", [])
                if not targets:
                    continue
                if is_human:
                    print(f"\n  Steal intrigue from which opponent?")
                    for i, t in enumerate(targets, 1):
                        print(f"    [{i}] {t['player_name']} ({t['intrigue_count']} intrigue cards)")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(targets)+1)])
                    chosen = targets[int(sel)-1]
                else:
                    chosen = _random.choice(targets)
                    self.print_info(f"  {player.name} steals from {chosen['player_name']}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen["player_id"])

            elif ctype == "recall_agent":
                locations = choice_data.get("placed_locations", [])
                if not locations:
                    continue
                # Resolve location IDs to names for display
                def _loc_name(lid):
                    for s in self.game.board.spaces:
                        if str(s.id) == str(lid):
                            return s.name
                    return str(lid)
                if is_human:
                    print(f"\n  Recall agent from which location?")
                    for i, lid in enumerate(locations, 1):
                        print(f"    [{i}] {_loc_name(lid)}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(locations)+1)])
                    chosen = locations[int(sel)-1]
                else:
                    chosen = _random.choice(locations)
                    self.print_info(f"  {player.name} recalls agent from {_loc_name(chosen)}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen)

            elif ctype == "recall_spy":
                posts = choice_data.get("placed_posts", [])
                if not posts:
                    continue
                def _post_name(pid):
                    for p in getattr(self.game.board, 'observation_posts', []):
                        if str(p.id) == str(pid):
                            return p.name
                    return str(pid)
                if is_human:
                    print(f"\n  Recall spy from which observation post?")
                    for i, pid in enumerate(posts, 1):
                        print(f"    [{i}] {_post_name(pid)}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(posts)+1)])
                    chosen = posts[int(sel)-1]
                else:
                    chosen = _random.choice(posts)
                    self.print_info(f"  {player.name} recalls spy from {_post_name(chosen)}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen)

            elif ctype == "accept_contract":
                contracts = choice_data.get("available_contracts", [])
                if not contracts:
                    continue
                if is_human:
                    print(f"\n  Accept which contract?")
                    for i, c in enumerate(contracts, 1):
                        rewards_str = _format_contract_rewards(getattr(c, 'rewards', []))
                        print(f"    [{i}] {c.name} → {rewards_str}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(contracts)+1)])
                    chosen = contracts[int(sel)-1]
                else:
                    chosen = _random.choice(contracts)
                    self.print_info(f"  {player.name} accepts contract {chosen.name}")
                effect_resolver.execute_choice(player.player_id, choice_data, chosen.id)

            elif ctype == "play_spy":
                # Same shape as spy_post — pick an observation post
                posts = choice_data.get("available_posts", choice_data.get("placed_posts", []))
                if not posts:
                    continue
                if is_human:
                    print(f"\n  Play spy on which observation post?")
                    for i, p in enumerate(posts, 1):
                        if isinstance(p, dict):
                            print(f"    [{i}] {p.get('post_name', p.get('post_id'))}")
                        else:
                            print(f"    [{i}] {p}")
                    sel = self.get_input("  Choice:", [str(i) for i in range(1, len(posts)+1)])
                    chosen = posts[int(sel)-1]
                else:
                    chosen = _random.choice(posts)
                pid = chosen.get("post_id") if isinstance(chosen, dict) else chosen
                effect_resolver.execute_choice(player.player_id, choice_data, pid)

            else:
                # Other choice types (trash_card, recall_agent, etc.)
                # Not yet wired into CLI — skip silently to avoid breaking flow
                self.print_info(f"  (Choice type '{ctype}' skipped — not yet supported in CLI)")

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

        # Calculate how many troops player will have AFTER location rewards
        future_troops = player.troops_in_garrison
        if hasattr(location, 'reward') and location.reward:
            for r in location.reward:
                if r.get('type') == 'resource' and r.get('resource') == 'troop':
                    future_troops += r.get('amount', 0)

        # Ask about troops if this is a combat space and player has/will have troops
        troops_to_deploy = 0
        # placement_type can be an icon ('blue', 'green', 'fremen', etc.) or 'spy_infiltrate'
        # Only spy infiltration doesn't allow troop deployment
        if placement_type != "spy_infiltrate" and future_troops > 0:
            # Check if this is a combat space
            if hasattr(location, 'is_combat_space') and location.is_combat_space:
                print(f"\n⚔️  {location.name} is a combat space!")
                print(f"You currently have {player.troops_in_garrison} troops in garrison.")
                if future_troops > player.troops_in_garrison:
                    print(f"After gaining rewards, you'll have {future_troops} troops.")
                print("How many troops to deploy to the conflict? (0-2)")
                max_troops = min(2, future_troops)
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
            if result.get("placement_type") == "spy_infiltrate":
                self.print_success(f"Infiltrated {location.name}! (spy recalled)")
            else:
                self.print_success(f"Placed agent on {location.name}!")
            if troops_to_deploy > 0:
                self.print_info(f"  Deployed {troops_to_deploy} troops to conflict")

            # Resolve any pending choices from the placement effects
            self._resolve_choices(player, result.get("choices_required", []))

            # Gather intel bonus — spy was at this location
            if result.get("gather_intel_card"):
                self.print_success(f"  🔍 Gather intel: drew intrigue card '{result['gather_intel_card']}'")

            # Check if signet ring was played
            if card.name == "Signet Ring" and player.leader:
                self.process_signet_ability(player, location)

            # Show what was gained (from both card agent effects and location effects)
            applied_effects = []
            card_eff = result.get('card_agent_effects', {}) or {}
            loc_eff = result.get('location_effects', {}) or {}
            applied_effects.extend(card_eff.get('effects_applied', []))
            applied_effects.extend(loc_eff.get('effects_applied', []))

            if applied_effects:
                self.print_section("Rewards Gained")
                for effect in applied_effects:
                    if isinstance(effect, dict):
                        # Format common shapes nicely
                        etype = effect.get('type', '?')
                        if etype == 'resource':
                            self.print_info(f"  • +{effect.get('amount',1)} {effect.get('resource','?')}")
                        elif etype == 'influence':
                            self.print_info(f"  • +{effect.get('amount',1)} {effect.get('target','?')} influence")
                        elif etype == 'draw':
                            self.print_info(f"  • drew {effect.get('amount',1)} card(s) from {effect.get('deck','deck')}")
                        else:
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

    def process_signet_ability(self, player: Player, location=None):
        """Process leader signet ability when Signet Ring is played."""
        self.print_section(f"⚡ {player.leader.name}'s Signet Ability")
        # location parameter reserved for future use (conditional signets based on placement)

        # Simple implementation for Princess Irulan
        if player.leader.name == "Princess Irulan":
            print("\nChoose signet ability:")
            print("  1. Acquire a card (cost ≤1) from the imperium row")
            print("  2. Trash a card from hand (gain 2 spice if it cost ≥1)")
            print("  3. Skip signet ability")

            choice = self.get_input("Choice:", ["1", "2", "3"])

            if choice == "1":
                # Show affordable cards (cost ≤ 1)
                affordable = [c for c in self.game.board.imperium_row if c and c.cost <= 1]
                if affordable:
                    print("\nChoose card to acquire:")
                    for i, card in enumerate(affordable, 1):
                        print(f"  {i}. {card.name} (cost: {card.cost})")
                    print("  0. Cancel")

                    card_choice = self.get_input("Card:", [str(i) for i in range(len(affordable) + 1)])
                    if card_choice != "0":
                        card_to_acquire = affordable[int(card_choice) - 1]
                        player.discard_pile.add_card(card_to_acquire)
                        self.game.board.imperium_row.remove(card_to_acquire)
                        self.print_success(f"Acquired {card_to_acquire.name}!")
                else:
                    self.print_info("No affordable cards in imperium row")

            elif choice == "2":
                # Trash a card
                if player.hand.cards:
                    print("\nChoose card to trash:")
                    for i, card in enumerate(player.hand.cards, 1):
                        print(f"  {i}. {card.name}")
                    print("  0. Cancel")

                    card_choice = self.get_input("Card:", [str(i) for i in range(len(player.hand.cards) + 1)])
                    if card_choice != "0":
                        card_to_trash = player.hand.cards[int(card_choice) - 1]
                        player.hand.cards.remove(card_to_trash)

                        # Check if card cost ≥ 1 for bonus
                        if card_to_trash.cost >= 1:
                            player.spice += 2
                            self.print_success(f"Trashed {card_to_trash.name}! Gained 2 spice")
                        else:
                            self.print_success(f"Trashed {card_to_trash.name}!")
                else:
                    self.print_info("No cards in hand to trash")

        elif player.leader.name == "Feyd Rautha Harkonnen":
            # Simplified Feyd-Rautha signet (complex multi-step ability)
            print("\nFeyd-Rautha's Signet (simplified):")
            print("  1. Choice: Pay 1 solari to trash a card, OR skip")
            print("  2. Trash a card from hand (mandatory)")
            print("  3. Gain 2 spice")
            print("  4. Skip")

            choice = self.get_input("Choice:", ["1", "2", "3", "4"])

            if choice == "1" and player.solari >= 1:
                # Pay 1 solari to trash
                if player.hand.cards:
                    print("\nChoose card to trash:")
                    for i, card in enumerate(player.hand.cards, 1):
                        print(f"  {i}. {card.name}")
                    card_choice = self.get_input("Card:", [str(i) for i in range(1, len(player.hand.cards) + 1)])
                    card_to_trash = player.hand.cards[int(card_choice) - 1]
                    player.hand.cards.remove(card_to_trash)
                    player.solari -= 1
                    self.print_success(f"Paid 1 solari, trashed {card_to_trash.name}")

            elif choice == "2":
                # Mandatory trash
                if player.hand.cards:
                    print("\nChoose card to trash:")
                    for i, card in enumerate(player.hand.cards, 1):
                        print(f"  {i}. {card.name}")
                    card_choice = self.get_input("Card:", [str(i) for i in range(1, len(player.hand.cards) + 1)])
                    card_to_trash = player.hand.cards[int(card_choice) - 1]
                    player.hand.cards.remove(card_to_trash)
                    self.print_success(f"Trashed {card_to_trash.name}")

            # Always get 2 spice
            player.spice += 2
            self.print_success("Gained 2 spice from signet")

        else:
            # For other leaders, show note
            self.print_info(f"  {player.leader.name}'s signet ability not yet implemented")

        time.sleep(1)

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
        import random as _random
        bot = self.bots[player.player_id]
        action_exec = self.managers["action_executor"]

        self.print_bot_action(f"{player.name} is thinking...")
        time.sleep(0.5)

        # Bot may play a plot intrigue card (~30% chance if they have one)
        plot_intrigues = [
            c for c in player.intrigue_cards
            if hasattr(c, 'phases') and any(p.value == 'Plot' for p in c.phases)
        ]
        if plot_intrigues and _random.random() < 0.3:
            chosen = _random.choice(plot_intrigues)
            result = action_exec.execute_play_intrigue(PlayIntrigueAction(
                player_id=player.player_id, intrigue_card=chosen
            ))
            if result.get("success"):
                self.print_bot_action(f"{player.name} plays plot intrigue: {chosen.name}")
                self._resolve_choices(player, result.get("choices_required", []))

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
                # Resolve any pending choices (bots auto-pick)
                self._resolve_choices(player, result.get("choices_required", []))
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
        """Run the reveal phase: all players buy cards with accumulated persuasion."""
        self.print_header(f"Round {self.game.current_round} - Acquisition Phase")

        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]

        for player in self.game.players:
            if not player.has_revealed_this_round:
                continue

            if player == self.human_player:
                self._human_acquisition(player, action_gen, action_exec)
            else:
                # Bot: buy a random affordable card or pass
                bot = self.bots.get(player.player_id)
                if bot and hasattr(bot, 'decide_acquisition'):
                    bot.decide_acquisition(player)
                else:
                    self._bot_acquisition(player, action_gen, action_exec)

        self.print_success("Acquisition phase complete")
        time.sleep(1)

    def _human_acquisition(self, player: Player, action_gen, action_exec):
        """Interactive acquisition menu for the human player."""
        contract_manager = self.managers.get("contract_manager")

        while True:
            options = action_gen.get_acquisition_options(player.player_id)
            persuasion = options.get("total_persuasion", 0)
            persuasion_left = getattr(player, 'temp_persuasion', persuasion)

            self.print_section(f"{player.name}'s Acquisition — {persuasion_left} persuasion remaining")

            # Build numbered buy list: imperium row + reserve piles
            choices = []   # list of (card_or_contract, source_str)

            print("\n  IMPERIUM ROW:")
            for card in options.get("imperium_row", []):
                affordable = card.cost <= persuasion_left
                marker = Colors.GREEN + "✓" + Colors.END if affordable else Colors.RED + "✗" + Colors.END
                idx = len(choices) + 1
                print(f"    [{idx}] {marker} {card.name:30s} Cost: {card.cost}")
                choices.append((card, "row"))

            reserve_prepare = options.get("reserve_prepare", [])
            reserve_spice = options.get("reserve_spice", [])
            if reserve_prepare or reserve_spice:
                print("\n  RESERVE PILES:")
                if reserve_prepare:
                    card = reserve_prepare[0]
                    affordable = card.cost <= persuasion_left
                    marker = Colors.GREEN + "✓" + Colors.END if affordable else Colors.RED + "✗" + Colors.END
                    idx = len(choices) + 1
                    print(f"    [{idx}] {marker} {card.name:30s} Cost: {card.cost}  ×{len(reserve_prepare)} left")
                    choices.append((card, "reserve"))
                if reserve_spice:
                    card = reserve_spice[0]
                    affordable = card.cost <= persuasion_left
                    marker = Colors.GREEN + "✓" + Colors.END if affordable else Colors.RED + "✗" + Colors.END
                    idx = len(choices) + 1
                    print(f"    [{idx}] {marker} {card.name:30s} Cost: {card.cost}  ×{len(reserve_spice)} left")
                    choices.append((card, "reserve"))

            # Show contracts (free to accept — no persuasion cost)
            contract_row = getattr(self.game.board, 'contract_row', [])
            if contract_manager and contract_row:
                print("\n  CONTRACTS (free — accept to take on a mission):")
                for contract in contract_row[:2]:
                    ctype = getattr(contract, 'completion_type', '?')
                    ctarget = getattr(contract, 'completion_target', '') or ''
                    creq = getattr(contract, 'required_spice', 0)
                    if ctype == 'location':
                        cond = f"visit {ctarget}"
                    elif ctype == 'harvest':
                        cond = f"harvest {creq} spice total"
                    elif ctype == 'acquire_card':
                        cond = f"acquire '{ctarget}'"
                    else:
                        cond = "immediate"
                    rewards_str = _format_contract_rewards(getattr(contract, 'rewards', []))
                    idx = len(choices) + 1
                    print(f"    [{idx}] 📋 {contract.name:28s} {cond} → {rewards_str}")
                    choices.append((contract, "contract"))

            valid = [str(i) for i in range(len(choices) + 1)]
            choice = self.get_input(f"\n  Choose [1-{len(choices)}] or [0] pass:", valid)

            if choice == "0":
                break

            idx = int(choice) - 1
            item, source = choices[idx]

            if source == "contract":
                # Accept a contract — no persuasion cost
                result = contract_manager.acquire_contract(player.player_id, item)
                if result.get("success"):
                    if result.get("completed"):
                        self.print_success(f"Contract '{item.name}' completed immediately!")
                        rewards = result.get("rewards", {})
                        applied = rewards.get("rewards_applied", [])
                        if applied:
                            reward_parts = [f'+{r["amount"]} {r["reward"]}' for r in applied]
                            print(f"  Rewards: {', '.join(reward_parts)}")
                    else:
                        self.print_success(f"Contract '{item.name}' accepted!")
                        ctype = result.get("completion_type", "")
                        ctarget = result.get("target", "")
                        print(f"  Complete by: {ctype} {ctarget or ''}")
                else:
                    self.print_error(f"Cannot accept contract: {result.get('error', 'Unknown error')}")
                continue  # Don't break — player can still buy cards

            # Card purchase
            if item.cost > persuasion_left:
                self.print_error(f"Cannot afford {item.name} (need {item.cost}, have {persuasion_left})")
                continue

            result = action_exec.execute_acquire_card(
                AcquireCardAction(player_id=player.player_id, card=item, source=source)
            )
            if result.get("success"):
                self.print_success(f"Acquired {item.name}!")
                # Resolve any on-acquire choices
                self._resolve_choices(player, result.get("choices_required", []))
                # Notify on any acquire-card contract completions
                for completed in result.get("contract_completions", {}).get("completed_contracts", []):
                    self.print_success(f"🎉 Contract completed: {completed['contract']}!")
                # Deduct cost from temp_persuasion
                player.temp_persuasion = getattr(player, 'temp_persuasion', persuasion_left) - item.cost
                if player.temp_persuasion <= 0:
                    break
            else:
                self.print_error(f"Failed: {result.get('error', 'Unknown error')}")

    def _bot_acquisition(self, player: Player, action_gen, action_exec):
        """Simple random bot acquisition fallback."""
        import random
        contract_manager = self.managers.get("contract_manager")
        options = action_gen.get_acquisition_options(player.player_id)
        persuasion = options.get("total_persuasion", 0)

        all_buyable = []
        for card in options.get("imperium_row", []):
            if card.cost <= persuasion:
                all_buyable.append((card, "row"))
        for card in options.get("reserve_cards", []):
            if card.cost <= persuasion:
                all_buyable.append((card, "reserve"))

        if all_buyable and random.random() < 0.7:
            card, source = random.choice(all_buyable)
            result = action_exec.execute_acquire_card(
                AcquireCardAction(player_id=player.player_id, card=card, source=source)
            )
            if result.get("success"):
                self.print_bot_action(f"{player.name} acquires {card.name}")

        # Bots accept a contract ~30% of the time if one is available
        if contract_manager and random.random() < 0.3:
            contract_row = getattr(self.game.board, 'contract_row', [])
            if contract_row:
                contract = random.choice(contract_row[:2])
                result = contract_manager.acquire_contract(player.player_id, contract)
                if result.get("success"):
                    self.print_bot_action(f"{player.name} accepts contract '{contract.name}'")

    def _format_conflict_rewards(self, rewards: dict) -> str:
        """Format conflict rewards dict into readable string."""
        if not rewards:
            return "none"
        parts = []
        for rank in ["1", "2", "3"]:
            if rank in rewards:
                effects = rewards[rank]
                effect_strs = []
                for e in effects:
                    if e.get("type") == "resource":
                        effect_strs.append(f"+{e.get('amount',1)} {e.get('resource','?')}")
                    elif e.get("type") == "influence":
                        effect_strs.append(f"+{e.get('amount',1)} {e.get('target','?')} influence")
                    elif e.get("type") == "victory_point":
                        effect_strs.append(f"+{e.get('amount',1)} VP")
                    elif e.get("type") == "draw":
                        effect_strs.append(f"draw {e.get('amount',1)} intrigue")
                    else:
                        effect_strs.append(e.get("type","?"))
                parts.append(f"  {rank}st: {', '.join(effect_strs)}")
        return "\n".join(parts) if parts else "no rewards"

    def run_combat_phase(self):
        """Run the combat phase."""
        combat_manager = self.managers["combat_manager"]
        action_exec = self.managers["action_executor"]

        self.print_header(f"Round {self.game.current_round} - Combat Phase")

        # Advance game phase to COMBAT so intrigue effects resolve correctly
        self.game.current_phase = GamePhase.COMBAT

        # Show current conflict and its rewards
        conflict = getattr(self.game.board, 'current_conflict', None)
        if conflict:
            self.print_section(f"⚔️  Conflict: {conflict.name}")
            reward_str = self._format_conflict_rewards(getattr(conflict, 'rewards', {}))
            if reward_str:
                print(f"  Rewards:\n{reward_str}")

        # --- Troop Deployment ---
        if self.human_player.troops_in_garrison > 0:
            print(f"\nYou have {self.human_player.troops_in_garrison} troops available.")
            max_troops = min(8, self.human_player.troops_in_garrison)
            choice = self.get_input(f"How many troops to deploy to conflict? (0-{max_troops}):", [str(i) for i in range(max_troops + 1)])
            troops = int(choice)
            if troops > 0:
                self.human_player.troops_in_conflict += troops
                self.human_player.troops_in_garrison -= troops
                self.print_success(f"Deployed {troops} troops to conflict")

        for player in self.game.players[1:]:
            bot = self.bots[player.player_id]
            troops = bot.decide_troops_to_deploy(player.troops_in_garrison)
            if troops > 0:
                player.troops_in_conflict += troops
                player.troops_in_garrison -= troops
                self.print_bot_action(f"{player.name} deploys {troops} troops")

        # Show troop summary
        print()
        participating = [(p, p.troops_in_conflict + getattr(p, 'sandworms_in_conflict', 0))
                         for p in self.game.players if p.troops_in_conflict > 0 or getattr(p, 'sandworms_in_conflict', 0) > 0]
        if participating:
            self.print_section("Combat Participants")
            for p, units in participating:
                swords = getattr(p, 'temp_swords', 0)
                strength = (p.troops_in_conflict * 2) + (getattr(p, 'sandworms_in_conflict', 0) * 3) + swords
                print(f"  {p.name}: {p.troops_in_conflict} troops + {swords} ⚔  = {strength} strength")
        else:
            self.print_info("No troops in conflict — skipping combat resolution.")
            self.game.current_phase = GamePhase.PLAYER_TURNS
            time.sleep(1)
            return

        # --- Intrigue Round ---
        intrigue_info = combat_manager.conduct_intrigue_round()
        players_with_intrigues = intrigue_info.get("players_with_intrigues", [])

        if players_with_intrigues:
            self.print_section("Combat Intrigue Round")
            print("  Players may play combat intrigue cards before strength is calculated.\n")

            # Human intrigue
            human_combat_intrigues = [
                card for card in self.human_player.intrigue_cards
                if hasattr(card, 'phases') and any(
                    phase.value == 'Combat' for phase in card.phases
                )
            ]
            if human_combat_intrigues:
                while True:
                    print(f"\n  Your combat intrigue cards:")
                    for i, card in enumerate(human_combat_intrigues, 1):
                        print(f"    [{i}] {card.name}")
                    choice = self.get_input("  Play [1-N] or [0] pass:", [str(i) for i in range(len(human_combat_intrigues) + 1)])
                    if choice == "0":
                        break
                    card = human_combat_intrigues[int(choice) - 1]
                    result = action_exec.execute_play_intrigue(PlayIntrigueAction(
                        player_id=self.human_player.player_id,
                        intrigue_card=card
                    ))
                    if result.get("success"):
                        self.print_success(f"Played {card.name}!")
                        self._resolve_choices(self.human_player, result.get("choices_required", []))
                        human_combat_intrigues = [c for c in self.human_player.intrigue_cards
                                                   if hasattr(c, 'phases') and any(p.value == 'Combat' for p in c.phases)]
                        if not human_combat_intrigues:
                            break
                    else:
                        self.print_error(f"Cannot play: {result.get('error','')}")
                        break

            # Bot intrigues
            for player in self.game.players[1:]:
                bot = self.bots[player.player_id]
                bot_combat_intrigues = [
                    card for card in player.intrigue_cards
                    if hasattr(card, 'phases') and any(p.value == 'Combat' for p in card.phases)
                ]
                chosen = bot.decide_intrigue_to_play(bot_combat_intrigues)
                if chosen:
                    result = action_exec.execute_play_intrigue(PlayIntrigueAction(
                        player_id=player.player_id,
                        intrigue_card=chosen
                    ))
                    if result.get("success"):
                        self.print_bot_action(f"{player.name} plays intrigue: {chosen.name}")
                        self._resolve_choices(player, result.get("choices_required", []))

        # --- Resolve Combat ---
        self.print_info("\nResolving combat...")
        result = combat_manager.resolve_conflict(intrigue_round_complete=True)

        def _pid_to_name(pid):
            p = next((x for x in self.game.players if x.player_id == pid), None)
            return p.name if p else pid

        if result.get("success"):
            self.print_success("Combat resolved!")
            rankings = result.get("rankings", {})
            for rank, player_ids in sorted(rankings.items()):
                ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(rank, f"{rank}th")
                names = [_pid_to_name(pid) for pid in player_ids]
                if names:
                    print(f"  {ordinal}: {', '.join(names)}")
            for winner_id in result.get("winners", []):
                winner = next((p for p in self.game.players if p.player_id == winner_id), None)
                if winner:
                    self.print_success(f"  🏆 {winner.name} wins the conflict card!")
        else:
            self.print_info(result.get("error", "Combat skipped"))

        # Restore phase
        self.game.current_phase = GamePhase.PLAYER_TURNS
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
        contract_manager = self.managers.get("contract_manager")

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

            # Check harvest contracts at end of each round
            if contract_manager:
                harvest_result = contract_manager.check_harvest_contracts(player.player_id)
                for completed in harvest_result.get("completed_contracts", []):
                    name = completed["contract"]
                    if player == self.human_player:
                        self.print_success(f"🎉 Harvest contract completed: {name}!")
                    else:
                        self.print_bot_action(f"{player.name} completed harvest contract: {name}")

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

        # Or when the conflict deck runs out (rules: game ends after last conflict resolves)
        if not self.game.board.conflict_deck and not self.game.board.current_conflict:
            return True

        # Safety cap: 10 rounds maximum
        if self.game.current_round > 10:
            return True

        return False

    def display_final_scores(self):
        """Display final scores and winner."""
        self.print_header("GAME OVER")

        # Advance to GAME_OVER phase so endgame intrigues resolve correctly
        self.game.current_phase = GamePhase.GAME_OVER

        # Resolve any end-game intrigue cards (phase = "End Game")
        action_exec = self.managers.get("action_executor")
        if action_exec:
            for player in self.game.players:
                endgame_intrigues = [
                    c for c in player.intrigue_cards
                    if hasattr(c, 'phases') and any(p.value == 'End Game' for p in c.phases)
                ]
                for card in list(endgame_intrigues):
                    result = action_exec.execute_play_intrigue(PlayIntrigueAction(
                        player_id=player.player_id, intrigue_card=card
                    ))
                    if result.get("success"):
                        self.print_info(f"  {player.name} resolves end-game intrigue: {card.name}")
                        self._resolve_choices(player, result.get("choices_required", []))

        # Sort by full tiebreaker order (matches phase_manager logic)
        sorted_players = sorted(
            self.game.players,
            key=lambda p: (p.victory_points, p.spice, p.solari, p.water, p.troops_in_garrison),
            reverse=True
        )

        self.print_section("Final Scores")
        print(f"  {'Player':<20} {'VP':>4}  {'Spice':>5}  {'Solari':>6}  {'Water':>5}  {'Garrison':>8}  Influence")
        print(f"  {'-'*20} {'-'*4}  {'-'*5}  {'-'*6}  {'-'*5}  {'-'*8}  {'-'*20}")
        for i, player in enumerate(sorted_players, 1):
            prefix = "🏆" if i == 1 else f"{i:2d}."
            fremen_inf = player.fremen_influence
            bg_inf = player.bene_gesserit_influence
            sg_inf = player.spacing_guild_influence
            emp_inf = player.emperor_influence
            influence_str = f"Fr:{fremen_inf} BG:{bg_inf} SG:{sg_inf} Em:{emp_inf}"
            print(f"  {prefix} {player.name:<18} {player.victory_points:>4}  {player.spice:>5}  {player.solari:>6}  {player.water:>5}  {player.troops_in_garrison:>8}  {influence_str}")

            # Completed contracts
            completed = getattr(player, 'contracts_completed', [])
            if completed:
                print(f"       ✅ Completed contracts: {', '.join(c.name for c in completed)}")

            # Active (incomplete) contracts
            active = getattr(player, 'contracts_active', [])
            if active:
                print(f"       📋 Unfinished contracts: {', '.join(c.name for c in active)}")

        winner = sorted_players[0]

        # Check if there's an actual tie
        runner_up = sorted_players[1] if len(sorted_players) > 1 else None
        is_tied = (runner_up and
                   winner.victory_points == runner_up.victory_points and
                   winner.spice == runner_up.spice and
                   winner.solari == runner_up.solari and
                   winner.water == runner_up.water and
                   winner.troops_in_garrison == runner_up.troops_in_garrison)

        print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.END}")
        if is_tied:
            print(f"{Colors.BOLD}{Colors.YELLOW}IT'S A TIE — SHARED VICTORY!{Colors.END}".center(88))
        else:
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

            # Draw next conflict card at the start of every round after the first
            # (Round 1 conflict is drawn during setup)
            if self.game.current_round > 1:
                if self.game.board.conflict_deck:
                    self.game.board.current_conflict = self.game.board.conflict_deck.pop(0)
                    self.print_info(f"New conflict: {self.game.board.current_conflict.name}")
                else:
                    self.game.board.current_conflict = None

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
