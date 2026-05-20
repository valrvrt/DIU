"""
DUNE: IMPERIUM UPRISING - Interactive Playable Game

Play against bots or watch bot-only games with comprehensive logging.
"""

import random
import time
import sys
from typing import Dict, Any, List, Tuple

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.engine.phase_manager import PhaseManager
from src.engine.deck_manager import DeckManager
from src.engine.combat_manager import CombatManager
from src.engine.makers_manager import MakersManager
from src.engine.action_generator import ActionGenerator
from src.engine.action_executor import ActionExecutor, PlaceAgentAction, RevealAction, AcquireCardAction
from src.engine.influence_manager import InfluenceManager
from src.engine.victory_point_manager import VictoryPointManager
from src.engine.effect_resolver import EffectResolver
from src.engine.game_logger import GameLogger
from src.engine.game_setup import GameSetup


# ==================== RANDOM BOT AI ====================

class RandomBot:
    """AI that selects random valid actions."""

    def __init__(self, action_generator: ActionGenerator, action_executor: ActionExecutor, logger: GameLogger = None):
        self.action_gen = action_generator
        self.action_exec = action_executor
        self.logger = logger

    def take_turn(self, player_id: str, game: Game) -> Dict[str, Any]:
        """
        Bot decides and executes one action.

        Returns:
            Result dict from action execution
        """
        player = next(p for p in game.players if p.player_id == player_id)

        # If already revealed, try to acquire cards
        if player.has_revealed_this_round:
            return self._try_acquire_card(player_id, player.name)

        # Check if should reveal (80% chance if no agents left, or random 20% chance)
        should_reveal = (
            player.agents_available == 0 or
            random.random() < 0.2
        )

        if should_reveal:
            return self._reveal(player_id, player.name)
        else:
            return self._place_agent(player_id, player.name)

    def _place_agent(self, player_id: str, player_name: str) -> Dict[str, Any]:
        """Place agent on random valid location."""
        playable_cards = self.action_gen.get_playable_imperium_cards(player_id)

        if not playable_cards:
            # No playable cards, must reveal
            return self._reveal(player_id, player_name)

        # Random card
        card = random.choice(playable_cards)

        # Random valid location
        locations = self.action_gen.get_valid_locations_for_card(player_id, card)
        if not locations:
            return self._reveal(player_id, player_name)

        location, placement_type = random.choice(locations)

        # Log bot decision
        if self.logger:
            self.logger.log_bot_decision(
                player_id, player_name,
                decision_type="place_agent",
                options=[f"{card.name} -> {loc.name}" for loc, _ in locations],
                chosen=f"{card.name} -> {location.name}",
                reasoning=f"Random selection from {len(locations)} valid placements"
            )

        # Execute action
        action = PlaceAgentAction(
            player_id=player_id,
            card=card,
            location=location,
            placement_type=placement_type,
            troops_to_deploy=0  # Simplified: no troop deployment for bots
        )

        result = self.action_exec.execute_place_agent(action)

        # Log action
        if self.logger:
            self.logger.log_player_action(
                player_id, player_name,
                action_type="place_agent",
                details={
                    "card": card.name,
                    "location": location.name,
                    "placement_type": placement_type,
                    "success": result.get("success", False)
                }
            )

        return result

    def _reveal(self, player_id: str, player_name: str) -> Dict[str, Any]:
        """Reveal hand."""
        if self.logger:
            self.logger.log_bot_decision(
                player_id, player_name,
                decision_type="reveal",
                options=["reveal"],
                chosen="reveal",
                reasoning="No more agents or random choice"
            )

        action = RevealAction(player_id=player_id)
        result = self.action_exec.execute_reveal(action)

        if self.logger:
            self.logger.log_player_action(
                player_id, player_name,
                action_type="reveal",
                details={
                    "total_persuasion": result.get("total_persuasion", 0),
                    "cards_revealed": result.get("cards_revealed", 0)
                }
            )

        return result

    def _try_acquire_card(self, player_id: str, player_name: str) -> Dict[str, Any]:
        """Try to acquire a random affordable card, or pass."""
        options = self.action_gen.get_acquisition_options(player_id)

        # Collect affordable cards
        affordable = []
        for card in options.get("imperium_row", []):
            if card.cost <= options.get("total_persuasion", 0):
                affordable.append(("imperium_row", card))

        for card in options.get("reserve_cards", []):
            if card.cost <= options.get("total_persuasion", 0):
                affordable.append(("reserve", card))

        # 70% chance to acquire if can afford
        if affordable and random.random() < 0.7:
            source, card = random.choice(affordable)

            if self.logger:
                self.logger.log_bot_decision(
                    player_id, player_name,
                    decision_type="acquire_card",
                    options=[c.name for _, c in affordable],
                    chosen=card.name,
                    reasoning=f"Random selection from {len(affordable)} affordable cards"
                )

            action = AcquireCardAction(
                player_id=player_id,
                card=card,
                source=source
            )
            result = self.action_exec.execute_acquire_card(action)

            if self.logger and result.get("success"):
                self.logger.log_card_acquisition(
                    player_id, player_name,
                    card_name=card.name,
                    cost=card.cost,
                    source=source
                )

            return result

        # Pass (no action, just return success)
        if self.logger:
            self.logger.log_bot_decision(
                player_id, player_name,
                decision_type="acquire_card",
                options=["pass"],
                chosen="pass",
                reasoning="No affordable cards or random choice to pass"
            )

        return {"success": True, "action": "pass"}


# ==================== GAME DISPLAY ====================

class GameDisplay:
    """Display game state in CLI."""

    @staticmethod
    def show_game_state(game: Game, vp_manager: VictoryPointManager = None):
        """Display current game state."""
        print("\n" + "="*70)
        print(f"ROUND {game.current_round} | PHASE: {game.current_phase.value}")
        print("="*70)

        # Show conflict
        if game.board.current_conflict:
            print(f"⚔️  CONFLICT: {game.board.current_conflict.name}")

        # Show players
        for i, player in enumerate(game.players):
            marker = ">>> " if i == game.current_player_index else "    "
            print(f"\n{marker}{player.name} ({player.color})")

            # VP breakdown if available
            if vp_manager:
                breakdown = vp_manager.get_vp_breakdown(player.player_id)
                print(f"    VP: {breakdown['total']} (Influence: {breakdown['influence']}, "
                      f"Tags: {breakdown['tag_pairs']}, Other: {breakdown['other']})")
            else:
                print(f"    VP: {player.victory_points}")

            print(f"    Resources: Solari: {player.solari}, Spice: {player.spice}, Water: {player.water}")
            print(f"    Troops: {player.troops_in_garrison} garrison, {player.troops_in_conflict} in conflict")
            print(f"    Agents: {player.agents_available}/{player.total_available_agents}")

            if player.has_revealed_this_round:
                print(f"    Persuasion: {getattr(player, 'temp_persuasion', 0)}")

            print(f"    Hand: {len(player.hand.cards)} cards | Deck: {len(player.deck.cards)} cards")

            # Show influence
            influence_str = f"Influence: F:{player.fremen_influence} B:{player.bene_gesserit_influence} " \
                          f"S:{player.spacing_guild_influence} E:{player.emperor_influence}"
            print(f"    {influence_str}")

        print("\n" + "="*70)

    @staticmethod
    def show_final_results(game: Game, winner_info: Dict[str, Any], vp_manager: VictoryPointManager = None):
        """Display final scores and winner."""
        print("\n" + "="*70)
        print("🎮 GAME OVER!")
        print("="*70)

        print("\n📊 Final Scores:")
        for score_info in winner_info.get("final_scores", []):
            player = score_info["player"]
            vp = score_info["vp"]
            spice = score_info["spice"]

            # Get VP breakdown if available
            if vp_manager:
                breakdown = vp_manager.get_vp_breakdown(player.player_id)
                print(f"\n{player.name}: {vp} VP (Spice: {spice})")
                print(f"  - Influence VP: {breakdown['influence']}")
                print(f"  - Tag Pairs VP: {breakdown['tag_pairs']}")
                print(f"  - Other VP: {breakdown['other']}")
            else:
                print(f"{player.name}: {vp} VP (Spice: {spice})")

        # Show winner
        if winner_info.get("is_tie"):
            winners = ", ".join([p.name for p in winner_info["tied_players"]])
            print(f"\n🏆 TIE BETWEEN: {winners}")
        else:
            winner = winner_info["winner"]
            print(f"\n🎉 WINNER: {winner.name} 🎉")

        print("="*70)


# ==================== GAME LOOP ====================

class GameLoop:
    """Main game loop."""

    def __init__(self, game: Game, managers: dict, human_player_id: str = None, logger: GameLogger = None):
        self.game = game
        self.managers = managers
        self.human_player_id = human_player_id
        self.logger = logger
        self.bot = RandomBot(
            managers["action_generator"],
            managers["action_executor"],
            logger
        )
        self.display = GameDisplay()

    def run(self):
        """Run game until completion."""
        while self.game.current_phase != GamePhase.GAME_OVER:
            # Log game state snapshot at start of each round
            if self.game.current_phase == GamePhase.BEGIN_ROUND and self.logger:
                self.logger.log_game_state_snapshot(
                    self.game.current_round,
                    self.game.current_phase.value,
                    [
                        {
                            "player_id": p.player_id,
                            "name": p.name,
                            "vp": p.victory_points,
                            "resources": {"solari": p.solari, "spice": p.spice, "water": p.water}
                        }
                        for p in self.game.players
                    ]
                )

            # Show state
            self.display.show_game_state(self.game, self.managers.get("victory_point_manager"))

            # Handle phase
            if self.game.current_phase == GamePhase.PLAYER_TURNS:
                self._handle_player_turns()
            else:
                # Automated phases
                print(f"⚙️  Auto-advancing from {self.game.current_phase.value}...")
                time.sleep(0.5)

                old_phase = self.game.current_phase.value
                self.managers["phase_manager"].advance_phase()

                if self.logger:
                    self.logger.log_phase_transition(
                        old_phase,
                        self.game.current_phase.value,
                        self.game.current_round
                    )

        # Game over
        winner_info = self.managers["phase_manager"].determine_winner()
        self.display.show_final_results(
            self.game,
            winner_info,
            self.managers.get("victory_point_manager")
        )

        # Log game end
        if self.logger:
            self.logger.log_game_end(
                winner={
                    "player_id": winner_info["winner"].player_id,
                    "name": winner_info["winner"].name,
                    "vp": winner_info["winner"].victory_points
                },
                final_scores=[
                    {
                        "player_id": s["player"].player_id,
                        "name": s["player"].name,
                        "vp": s["vp"],
                        "spice": s["spice"]
                    }
                    for s in winner_info["final_scores"]
                ]
            )
            self.logger.print_summary()

    def _handle_player_turns(self):
        """Handle PLAYER_TURNS phase (core gameplay)."""
        phase_manager = self.managers["phase_manager"]

        while self.game.current_phase == GamePhase.PLAYER_TURNS:
            current_player = self.game.players[self.game.current_player_index]

            # Check if all players revealed
            if phase_manager.should_advance_phase():
                old_phase = self.game.current_phase.value
                phase_manager.advance_phase()

                if self.logger:
                    self.logger.log_phase_transition(
                        old_phase,
                        self.game.current_phase.value,
                        self.game.current_round
                    )
                break

            # Human player turn (if there is one)
            if self.human_player_id and current_player.player_id == self.human_player_id:
                self._human_turn(current_player.player_id)
            else:
                # Bot turn
                print(f"\n🤖 {current_player.name} (BOT) is thinking...")
                result = self.bot.take_turn(current_player.player_id, self.game)

                if result.get("success"):
                    action_type = result.get("action", result.get("action_type", "unknown"))

                    # Show detailed info based on action type
                    if action_type == "place_agent":
                        card_name = result.get("card", "?")
                        location_name = result.get("location", "?")
                        print(f"   ✓ {current_player.name} placed agent: {card_name} → {location_name}")

                        # Show what they gained (check player state changes)
                        player = self.game.get_player(current_player.player_id)
                        gains = []
                        if player.fremen_influence > 0 or player.bene_gesserit_influence > 0 or player.spacing_guild_influence > 0 or player.emperor_influence > 0:
                            gains.append(f"Influence: F{player.fremen_influence} B{player.bene_gesserit_influence} S{player.spacing_guild_influence} E{player.emperor_influence}")
                        if player.solari > 0:
                            gains.append(f"{player.solari} solari")
                        if player.spice > 0:
                            gains.append(f"{player.spice} spice")
                        if gains:
                            print(f"      Gained: {', '.join(gains)}")
                    elif action_type == "reveal":
                        persuasion = result.get("total_persuasion", 0)
                        print(f"   ✓ {current_player.name} revealed (persuasion: {persuasion})")
                    else:
                        print(f"   ✓ {current_player.name} performed: {action_type}")
                else:
                    print(f"   ✗ Action failed: {result.get('error', 'Unknown error')}")

            # Advance turn if appropriate
            if not phase_manager.should_advance_phase():
                phase_manager.advance_turn()

    def _human_turn(self, player_id: str):
        """Handle human player input with full information."""
        player = next(p for p in self.game.players if p.player_id == player_id)
        action_gen = self.managers["action_generator"]
        action_exec = self.managers["action_executor"]

        print(f"\n" + "="*70)
        print(f"👤 {player.name}'S TURN")
        print("="*70)

        if player.has_revealed_this_round:
            self._human_acquisition_phase(player_id, player, action_gen, action_exec)
        else:
            self._human_agent_phase(player_id, player, action_gen, action_exec)

    def _human_agent_phase(self, player_id: str, player, action_gen, action_exec):
        """Handle human agent placement phase."""
        # Check if must reveal (no agents left)
        if player.agents_available == 0:
            print(f"\n⚠️  No agents available - auto-revealing!")
            action = RevealAction(player_id=player_id)
            result = action_exec.execute_reveal(action)
            if result.get("success"):
                print(f"✓ Revealed hand! Persuasion: {result.get('total_persuasion', 0)}")
            return

        # Show hand
        print(f"\n📋 YOUR HAND ({len(player.hand.cards)} cards):")
        playable_cards = action_gen.get_playable_imperium_cards(player_id)

        for i, card in enumerate(player.hand.cards):
            playable = "✓" if card in playable_cards else "✗"
            agent_icons = ", ".join(card.agent_icons) if hasattr(card, 'agent_icons') and card.agent_icons else "none"
            print(f"  [{i+1}] {playable} {card.name} (icons: {agent_icons})")

        print(f"\n⚙️  AGENTS: {player.agents_available}/{player.total_available_agents} available")
        print(f"💰 RESOURCES: Solari:{player.solari} Spice:{player.spice} Water:{player.water} Troops:{player.troops_in_garrison}")

        print("\nOptions:")
        print("  [1-5] - Play card number")
        print("  [R]   - Reveal hand and end agent phase")
        print("  [skip] - Let bot play this turn")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "skip":
            result = self.bot.take_turn(player_id, self.game)
            return

        if choice == "r":
            action = RevealAction(player_id=player_id)
            result = action_exec.execute_reveal(action)
            if result.get("success"):
                print(f"\n✓ Revealed hand! Persuasion: {result.get('total_persuasion', 0)}")
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(player.hand.cards):
                card = player.hand.cards[idx]
                if card not in playable_cards:
                    print(f"\n✗ {card.name} cannot be played (no matching agent icons or no agents left)")
                    self._human_agent_phase(player_id, player, action_gen, action_exec)
                    return

                # Show valid locations
                locations = action_gen.get_valid_locations_for_card(player_id, card)
                if not locations:
                    print(f"\n✗ No valid locations for {card.name}")
                    self._human_agent_phase(player_id, player, action_gen, action_exec)
                    return

                print(f"\n📍 Valid locations for {card.name}:")
                for i, (loc, ptype) in enumerate(locations):
                    cost_str = ""
                    if hasattr(loc, 'cost') and loc.cost:
                        costs = []
                        for c in loc.cost if isinstance(loc.cost, list) else []:
                            if isinstance(c, dict) and c.get("type") == "resource":
                                costs.append(f"{c['amount']} {c['resource']}")
                        cost_str = f" (cost: {', '.join(costs)})" if costs else ""

                    print(f"  [{i+1}] {loc.name}{cost_str}")

                loc_choice = input("Choose location (number or 'back'): ").strip()
                if loc_choice == "back":
                    self._human_agent_phase(player_id, player, action_gen, action_exec)
                    return

                try:
                    loc_idx = int(loc_choice) - 1
                    if 0 <= loc_idx < len(locations):
                        location, placement_type = locations[loc_idx]

                        action = PlaceAgentAction(
                            player_id=player_id,
                            card=card,
                            location=location,
                            placement_type=placement_type,
                            troops_to_deploy=0
                        )
                        result = action_exec.execute_place_agent(action)

                        if result.get("success"):
                            print(f"\n✓ Placed agent at {location.name}!")

                            # Show what you gained
                            effects = result.get("effects_applied", [])
                            if effects:
                                print("  Effects:")
                                for eff in effects:
                                    if eff.get("type") == "resource":
                                        print(f"    → +{eff.get('amount', 0)} {eff.get('resource', '?')}")
                                    elif eff.get("type") == "influence":
                                        target = eff.get("target", "?")
                                        amt = eff.get("amount", 0)
                                        print(f"    → +{amt} {target} influence")
                                    elif eff.get("type") == "draw":
                                        deck = eff.get("deck", "?")
                                        amt = eff.get("amount", 0)
                                        print(f"    → Drew {amt} card(s) from {deck}")
                                    else:
                                        print(f"    → {eff.get('type', '?')}")
                        else:
                            print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")
                    else:
                        print("\n✗ Invalid location number")
                        self._human_agent_phase(player_id, player, action_gen, action_exec)
                except ValueError:
                    print("\n✗ Invalid input")
                    self._human_agent_phase(player_id, player, action_gen, action_exec)
            else:
                print("\n✗ Invalid card number")
                self._human_agent_phase(player_id, player, action_gen, action_exec)
        except ValueError:
            print("\n✗ Invalid input")
            self._human_agent_phase(player_id, player, action_gen, action_exec)

    def _human_acquisition_phase(self, player_id: str, player, action_gen, action_exec):
        """Handle human card acquisition phase."""
        options = action_gen.get_acquisition_options(player_id)
        total_persuasion = options.get("total_persuasion", 0)

        print(f"\n💎 PERSUASION: {total_persuasion}")
        print(f"\n🛒 AVAILABLE CARDS:")

        affordable_cards = []
        imperium_row = options.get("imperium_row", [])

        for i, card in enumerate(imperium_row):
            affordable = card.cost <= total_persuasion
            marker = "✓" if affordable else "✗"
            print(f"  [{i+1}] {marker} {card.name} (Cost: {card.cost})")
            if affordable:
                affordable_cards.append((i, card, "imperium_row"))

        print("\nOptions:")
        if affordable_cards:
            print("  [1-6] - Buy card number")
        print("  [pass] - Pass (done buying)")
        print("  [skip] - Let bot decide")

        choice = input("\nYour choice: ").strip().lower()

        if choice == "pass":
            print("\n✓ Passed on buying cards")
            return

        if choice == "skip":
            result = self.bot._try_acquire_card(player_id, player.name)
            return

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(imperium_row):
                card = imperium_row[idx]
                if card.cost > total_persuasion:
                    print(f"\n✗ Cannot afford {card.name} (need {card.cost}, have {total_persuasion})")
                    self._human_acquisition_phase(player_id, player, action_gen, action_exec)
                    return

                action = AcquireCardAction(
                    player_id=player_id,
                    card=card,
                    source="row"
                )
                result = action_exec.execute_acquire_card(action)

                if result.get("success"):
                    print(f"\n✓ Acquired {card.name}!")
                else:
                    print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")
            else:
                print("\n✗ Invalid card number")
                self._human_acquisition_phase(player_id, player, action_gen, action_exec)
        except ValueError:
            print("\n✗ Invalid input")
            self._human_acquisition_phase(player_id, player, action_gen, action_exec)


# ==================== MAIN ====================

def main():
    """Main entry point for playable game."""
    print("="*70)
    print("DUNE: IMPERIUM UPRISING")
    print("Interactive Playable Game")
    print("="*70)

    # Ask for game mode
    print("\nGame Mode:")
    print("  1. Watch bots play (bot-only)")
    print("  2. Play against bots (human + 2 bots)")

    while True:
        choice = input("\nChoose mode (1 or 2): ").strip()
        if choice in ["1", "2"]:
            break
        print("Invalid choice. Please enter 1 or 2.")

    bot_only = (choice == "1")

    # Get player name if human playing
    if not bot_only:
        player_name = input("\nEnter your name: ").strip() or "Player"
    else:
        player_name = "Bot 0"

    # Ask for player count
    print("\nPlayer count: 3 or 4?")
    while True:
        count_input = input("Enter player count (3 or 4): ").strip()
        if count_input in ["3", "4"]:
            player_count = int(count_input)
            break
        print("Invalid choice. Please enter 3 or 4.")

    print("\nInitializing game...")

    # Create game using GameSetup
    game, setup_info = GameSetup.create_game(player_count, player_name)

    # If bot-only, rename first player
    if bot_only:
        game.players[0].name = "Bot 0"

    # Create logger
    logger = GameLogger()
    logger.log({
        "event_type": "game_setup",
        "player_count": player_count,
        "bot_only": bot_only,
        "setup_info": setup_info
    })

    # Create managers with new systems
    deck_manager = DeckManager(game)
    influence_manager = InfluenceManager(game)
    victory_point_manager = VictoryPointManager(game)

    effect_resolver = EffectResolver(game, influence_manager=influence_manager)
    combat_manager = CombatManager(game, effect_resolver=effect_resolver, victory_point_manager=victory_point_manager)
    makers_manager = MakersManager(game)

    phase_manager = PhaseManager(
        game,
        deck_manager=deck_manager,
        combat_manager=combat_manager,
        makers_manager=makers_manager
    )

    action_generator = ActionGenerator(game, phase_manager)
    action_executor = ActionExecutor(game, phase_manager, deck_manager, effect_resolver)

    managers = {
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

    print(f"\n✓ Game initialized!")
    print(f"✓ Players: {', '.join(p.name for p in game.players)}")
    print(f"✓ First Player: {setup_info['first_player_name']}")
    print(f"✓ Logging to: {logger.log_file}")

    # Run game
    human_player_id = None if bot_only else game.players[0].player_id

    loop = GameLoop(game, managers, human_player_id, logger)

    print("\n🎮 Starting game...\n")
    time.sleep(1)

    loop.run()


if __name__ == "__main__":
    main()
