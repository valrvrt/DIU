#!/usr/bin/env python3
"""
DUNE: IMPERIUM UPRISING - Interactive Playable Game

Play against random bots to test the game implementation.

Usage:
    python3 play_game.py
"""

import sys
import os
import time
import random
from typing import Dict, Any, List

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.engine.game_setup import GameSetup
from src.engine.phase_manager import PhaseManager
from src.engine.deck_manager import DeckManager
from src.engine.combat_manager import CombatManager
from src.engine.makers_manager import MakersManager
from src.engine.influence_manager import InfluenceManager
from src.engine.victory_point_manager import VictoryPointManager
from src.engine.action_generator import ActionGenerator
from src.engine.action_executor import ActionExecutor, PlaceAgentAction, RevealAction, AcquireCardAction
from src.engine.effect_resolver import EffectResolver


# ==================== RANDOM BOT ====================

class RandomBot:
    """AI that selects random valid actions."""

    def __init__(self, action_generator: ActionGenerator, action_executor: ActionExecutor):
        self.action_gen = action_generator
        self.action_exec = action_executor

    def take_turn(self, player_id: str, game: Game) -> Dict[str, Any]:
        """
        Bot decides and executes one action.

        Returns:
            Result dict from action execution
        """
        player = next(p for p in game.players if p.player_id == player_id)

        # If already revealed, try to acquire cards
        if player.has_revealed_this_round:
            return self._try_acquire_card(player_id)

        # Check if should reveal (80% chance if no agents left, or random 20% chance)
        should_reveal = (
            player.agents_available == 0 or
            random.random() < 0.2
        )

        if should_reveal:
            return self._reveal(player_id)
        else:
            return self._place_agent(player_id)

    def _place_agent(self, player_id: str) -> Dict[str, Any]:
        """Place agent on random valid location."""
        playable_cards = self.action_gen.get_playable_imperium_cards(player_id)

        if not playable_cards:
            # No playable cards, must reveal
            return self._reveal(player_id)

        # Random card
        card = random.choice(playable_cards)

        # Random valid location
        locations = self.action_gen.get_valid_locations_for_card(player_id, card)
        if not locations:
            return self._reveal(player_id)

        location, placement_type = random.choice(locations)

        # Execute action
        action = PlaceAgentAction(
            player_id=player_id,
            card=card,
            location=location,
            placement_type=placement_type
        )

        return self.action_exec.execute_place_agent(action)

    def _reveal(self, player_id: str) -> Dict[str, Any]:
        """Reveal hand."""
        action = RevealAction(player_id=player_id)
        return self.action_exec.execute_reveal(action)

    def _try_acquire_card(self, player_id: str) -> Dict[str, Any]:
        """Try to acquire a random affordable card, or pass."""
        options = self.action_gen.get_acquisition_options(player_id)

        # Collect affordable cards
        affordable = []
        for card in options["imperium_row"]:
            if card.cost <= options["total_persuasion"]:
                affordable.append(card)

        # 70% chance to acquire if can afford
        if affordable and random.random() < 0.7:
            card = random.choice(affordable)
            action = AcquireCardAction(
                player_id=player_id,
                card=card,
                source="imperium_row"
            )
            return self.action_exec.execute_acquire_card(action)

        # Pass (no action, just return success)
        return {"success": True, "action_type": "pass"}


# ==================== GAME DISPLAY ====================

class GameDisplay:
    """Display game state in CLI."""

    @staticmethod
    def show_game_state(game: Game, vp_manager: VictoryPointManager = None):
        """Display current game state."""
        print("\n" + "=" * 80)
        print(f"ROUND {game.current_round} | PHASE: {game.current_phase.value}")
        print("=" * 80)

        # Show conflict
        if game.board.current_conflict:
            print(f"CONFLICT: {game.board.current_conflict.name} (Level {game.board.current_conflict.level})")

        # Show players
        for i, player in enumerate(game.players):
            marker = ">>> " if i == game.current_player_index else "    "
            print(f"\n{marker}{player.name} ({player.color})")

            # VP breakdown if available
            if vp_manager:
                breakdown = vp_manager.get_vp_breakdown(player.player_id)
                print(f"    VP: {breakdown['total']} "
                      f"(Influence: {breakdown['influence']}, "
                      f"Tags: {breakdown['tag_pairs']}, "
                      f"Other: {breakdown['other']})")
            else:
                print(f"    VP: {player.victory_points}")

            print(f"    Resources: Solari {player.solari} | Spice {player.spice} | Water {player.water}")
            print(f"    Troops: {player.troops_in_garrison} garrison, "
                  f"{player.troops_in_conflict} in conflict")
            print(f"    Agents: {player.agents_available}/{player.total_available_agents}")

            if player.has_revealed_this_round:
                persuasion = getattr(player, 'temp_persuasion', 0)
                print(f"    Persuasion: {persuasion}")

            print(f"    Hand: {len(player.hand.cards)} cards | "
                  f"Deck: {len(player.deck.cards)} | "
                  f"Discard: {len(player.discard_pile.cards)}")

            # Show objectives
            if hasattr(player, 'objectives') and player.objectives:
                obj_names = [obj.name for obj in player.objectives]
                print(f"    Objective: {', '.join(obj_names)}")

        print("\n" + "=" * 80)

    @staticmethod
    def show_player_options(player_id: str, game: Game, action_gen: ActionGenerator):
        """Display available actions for player."""
        player = next(p for p in game.players if p.player_id == player_id)

        print(f"\n{player.name}'s turn:")

        if player.has_revealed_this_round:
            # Show acquisition options
            options = action_gen.get_acquisition_options(player_id)
            print(f"Persuasion available: {options['total_persuasion']}")
            print("\nImperium Row:")
            for i, card in enumerate(options["imperium_row"]):
                affordable = "✓" if card.cost <= options["total_persuasion"] else "✗"
                print(f"  [{i+1}] {card.name} (Cost: {card.cost}) {affordable}")
            print("  [0] Pass (done acquiring)")
        else:
            # Show playable cards
            playable = action_gen.get_playable_imperium_cards(player_id)
            print(f"\nHand ({len(player.hand.cards)} cards):")
            for i, card in enumerate(player.hand.cards):
                playable_mark = "✓" if card in playable else "✗"
                print(f"  [{i+1}] {card.name} {playable_mark}")
            print(f"  [R] Reveal hand")

    @staticmethod
    def show_action_result(result: Dict[str, Any]):
        """Display action result."""
        if result.get("success"):
            action_type = result.get('action_type', 'Action')
            print(f"✓ {action_type} succeeded")
            if "effects_applied" in result:
                print(f"  Effects: {result['effects_applied']}")
        else:
            print(f"✗ Failed: {result.get('error', 'Unknown error')}")


# ==================== GAME LOOP ====================

class GameLoop:
    """Main game loop."""

    def __init__(self, game: Game, managers: dict, human_player_id: str):
        self.game = game
        self.managers = managers
        self.human_player_id = human_player_id
        self.bot = RandomBot(managers["action_generator"], managers["action_executor"])
        self.display = GameDisplay()

    def run(self):
        """Run game until completion."""
        while self.game.current_phase != GamePhase.GAME_OVER:
            # Show state
            self.display.show_game_state(self.game, self.managers.get("vp_manager"))

            # Handle phase
            if self.game.current_phase == GamePhase.PLAYER_TURNS:
                self._handle_player_turns()
            else:
                # Automated phases
                print(f"\nAuto-advancing from {self.game.current_phase.value}...")
                time.sleep(1)
                self.managers["phase_manager"].advance_phase()

        # Game over
        self._show_final_results()

    def _handle_player_turns(self):
        """Handle PLAYER_TURNS phase (core gameplay)."""
        phase_manager = self.managers["phase_manager"]

        while self.game.current_phase == GamePhase.PLAYER_TURNS:
            current_player = self.game.players[self.game.current_player_index]

            # Check if all players revealed
            if phase_manager.should_advance_phase():
                phase_manager.advance_phase()
                break

            # Human player turn
            if current_player.player_id == self.human_player_id:
                self._human_turn(current_player.player_id)
            else:
                # Bot turn
                print(f"\n{current_player.name} (BOT) is thinking...")
                time.sleep(1)  # Dramatic pause
                result = self.bot.take_turn(current_player.player_id, self.game)
                self.display.show_action_result(result)
                time.sleep(0.5)

            # Advance turn if appropriate
            if not phase_manager.should_advance_phase():
                phase_manager.advance_turn()

    def _human_turn(self, player_id: str):
        """Handle human player input."""
        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]
        player = next(p for p in self.game.players if p.player_id == player_id)

        self.display.show_player_options(player_id, self.game, action_gen)

        if player.has_revealed_this_round:
            # Acquisition phase
            choice = input("\nSelect card to acquire (number) or 0 to pass: ").strip()

            if choice == "0":
                print("Passing on acquisition.")
                return

            try:
                idx = int(choice) - 1
                options = action_gen.get_acquisition_options(player_id)
                card = options["imperium_row"][idx]

                action = AcquireCardAction(
                    player_id=player_id,
                    card=card,
                    source="imperium_row"
                )
                result = action_exec.execute_acquire_card(action)
                self.display.show_action_result(result)
            except (ValueError, IndexError):
                print("Invalid choice.")
        else:
            # Agent placement phase
            choice = input("\nSelect card (number) or R to reveal: ").strip().upper()

            if choice == "R":
                action = RevealAction(player_id=player_id)
                result = action_exec.execute_reveal(action)
                self.display.show_action_result(result)
            else:
                try:
                    idx = int(choice) - 1
                    card = player.hand.cards[idx]

                    # Show locations
                    locations = action_gen.get_valid_locations_for_card(player_id, card)
                    if not locations:
                        print("No valid locations for this card!")
                        return

                    print("\nValid locations:")
                    for i, (loc, ptype) in enumerate(locations):
                        print(f"  [{i+1}] {loc.name} ({ptype})")

                    loc_choice = int(input("Select location: ")) - 1
                    location, placement_type = locations[loc_choice]

                    action = PlaceAgentAction(
                        player_id=player_id,
                        card=card,
                        location=location,
                        placement_type=placement_type
                    )
                    result = action_exec.execute_place_agent(action)
                    self.display.show_action_result(result)

                except (ValueError, IndexError):
                    print("Invalid choice.")

    def _show_final_results(self):
        """Display final scores and winner."""
        print("\n" + "=" * 80)
        print("GAME OVER!")
        print("=" * 80)

        # Get winner info from phase manager
        winner_info = self.managers["phase_manager"].determine_winner()

        print("\nFinal Scores:")
        for score_data in winner_info["final_scores"]:
            player = score_data["player"]
            vp = score_data["vp"]
            spice = score_data["spice"]

            # Get VP breakdown
            if self.managers.get("vp_manager"):
                breakdown = self.managers["vp_manager"].get_vp_breakdown(player.player_id)
                print(f"{player.name}: {vp} VP (Spice: {spice})")
                print(f"  Breakdown: Influence {breakdown['influence']}, "
                      f"Tags {breakdown['tag_pairs']}, "
                      f"Other {breakdown['other']}")
            else:
                print(f"{player.name}: {vp} VP (Spice: {spice})")

        # Show winner
        if winner_info["is_tie"]:
            winners = [p.name for p in winner_info["tied_players"]]
            print(f"\n🏆 TIE! Winners: {', '.join(winners)} 🏆")
        else:
            print(f"\n🎉 {winner_info['winner'].name} WINS! 🎉")


# ==================== MAIN ====================

def main():
    """Main entry point for playable game."""
    print("=" * 80)
    print("DUNE: IMPERIUM UPRISING")
    print("Interactive Playable Game")
    print("=" * 80)

    # Get player name
    player_name = input("\nEnter your name: ").strip() or "Player"

    # Get player count
    while True:
        try:
            player_count = int(input("Number of players (3 or 4): ").strip())
            if player_count in [3, 4]:
                break
            print("Please enter 3 or 4.")
        except ValueError:
            print("Please enter a number.")

    print("\nInitializing game...")

    # Create game
    game, setup_info = GameSetup.create_game(player_count, player_name)

    print(f"\n✓ Game created with {player_count} players")
    print(f"✓ First player: {setup_info['first_player_name']}")
    print(f"✓ Conflict deck: {setup_info['conflict_deck_size']} cards")
    print(f"✓ Imperium deck: {setup_info['imperium_deck_size']} cards")

    # Create managers
    phase_manager = PhaseManager(game)
    deck_manager = DeckManager(game)
    combat_manager = CombatManager(game)
    makers_manager = MakersManager(game)
    influence_manager = InfluenceManager(game)
    vp_manager = VictoryPointManager(game)
    effect_resolver = EffectResolver(game)

    action_generator = ActionGenerator(game, phase_manager)
    action_executor = ActionExecutor(game, phase_manager, deck_manager)

    managers = {
        "phase_manager": phase_manager,
        "deck_manager": deck_manager,
        "combat_manager": combat_manager,
        "makers_manager": makers_manager,
        "influence_manager": influence_manager,
        "vp_manager": vp_manager,
        "effect_resolver": effect_resolver,
        "action_generator": action_generator,
        "action_executor": action_executor
    }

    # Start game (SETUP → BEGIN_ROUND → PLAYER_TURNS)
    print("\nStarting game...")
    phase_manager.advance_phase()  # SETUP → BEGIN_ROUND
    phase_manager.advance_phase()  # BEGIN_ROUND → PLAYER_TURNS

    # Run game
    loop = GameLoop(game, managers, setup_info["human_player_id"])
    loop.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nGame interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
