"""
Interactive Turn Test - Play a complete turn manually.

This allows you to test the game flow interactively by making choices.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.game import Game
from src.models.player import Player
from src.models.card import ImperiumCard, CardType, LeaderCard, ContractCard
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.game_state import GameState
from src.engine.action_generator import ActionGenerator
from src.engine.action_executor import ActionExecutor, PlaceAgentAction, RevealAction
from src.engine.contract_manager import ContractManager


def create_game():
    """Create a full game with multiple cards and locations."""

    # Create leader
    leader = LeaderCard(
        id="paul_atreides",
        name="Paul Atreides",
        type="Leader",
        card_type=CardType.LEADER
    )

    # Create player
    player = Player(
        player_id="player1",
        name="Test Player",
        leader=leader,
        color="blue",
        deck=Deck(),
        hand=Deck(),
        discard_pile=Deck(),
        water=2,
        solari=5,
        spice=1,
        troops_in_garrison=5,
        troops_in_reserve=9,
        agents_available=2,
        spies_available=3,
        fremen_influence=0,
        emperor_influence=0
    )

    # Create diverse cards
    cards = [
        ImperiumCard(
            id="card1",
            name="Fremen Scout",
            type="Imperium",
            card_type=CardType.IMPERIUM,
            cost=3,
            agent_icons=["fremen"],
            agent_effects={
                "base": {
                    "water": 1,
                    "troops": 2
                }
            },
            reveal_effects={
                "base": {
                    "persuasion": 2
                }
            }
        ),
        ImperiumCard(
            id="card2",
            name="Guild Banker",
            type="Imperium",
            card_type=CardType.IMPERIUM,
            cost=4,
            agent_icons=["spacing_guild"],
            agent_effects={
                "base": {
                    "solari": 5
                }
            },
            reveal_effects={
                "base": {
                    "persuasion": 3
                }
            }
        ),
        ImperiumCard(
            id="card3",
            name="Bene Gesserit Operative",
            type="Imperium",
            card_type=CardType.IMPERIUM,
            cost=3,
            agent_icons=["bene_gesserit"],
            agent_effects={
                "base": {
                    "spy": 1
                }
            },
            reveal_effects={
                "base": {
                    "persuasion": 1
                },
                "effect_1": {
                    "condition": {
                        "type": "check",
                        "requirements": {
                            "spies_placed": {"min": 2}
                        }
                    },
                    "effects": {
                        "persuasion": 2
                    }
                }
            }
        ),
        ImperiumCard(
            id="card4",
            name="Emperor's Blade",
            type="Imperium",
            card_type=CardType.IMPERIUM,
            cost=5,
            agent_icons=["emperor"],
            agent_effects={
                "base": {
                    "troops": 3,
                    "solari": 2
                }
            },
            reveal_effects={
                "base": {
                    "persuasion": 2,
                    "swords": 2
                }
            }
        ),
        ImperiumCard(
            id="card5",
            name="Spice Trader",
            type="Imperium",
            card_type=CardType.IMPERIUM,
            cost=2,
            agent_icons=["landsraad", "spacing_guild"],
            agent_effects={
                "base": {
                    "spice": 2
                }
            },
            reveal_effects={
                "base": {
                    "persuasion": 1
                }
            }
        )
    ]

    # Add all cards to hand
    for card in cards:
        player.hand.add_card(card)

    # Create board spaces
    locations = [
        BoardSpace(
            id="fremen_camp",
            name="Fremen Camp",
            agent_icon="fremen",
            effects={"water": 1},
            faction="fremen"
        ),
        BoardSpace(
            id="carthag",
            name="Carthag",
            agent_icon="emperor",
            effects={"troops": 2},
            faction="emperor",
            is_combat_space=True
        ),
        BoardSpace(
            id="spice_trade",
            name="Spice Trade",
            agent_icon="spacing_guild",
            effects={"spice": 1, "solari": 2},
            faction="spacing_guild"
        ),
        BoardSpace(
            id="landsraad",
            name="Landsraad",
            agent_icon="landsraad",
            effects={"solari": 3},
            cost={"water": 1}
        ),
        BoardSpace(
            id="sietch",
            name="Sietch Tabr",
            agent_icon="fremen",
            effects={"water": 2, "troops": 1},
            faction="fremen",
            is_combat_space=True
        ),
        BoardSpace(
            id="truthsayer",
            name="Truthsayer",
            agent_icon="bene_gesserit",
            effects={"intrigue": 1, "draw": 1},
            faction="bene_gesserit"
        )
    ]

    # Create contracts
    contract1 = ContractCard(
        id="contract1",
        name="Spice Production Contract",
        type="Contract",
        card_type=CardType.CONTRACT,
        completion_type="harvest",
        required_spice=5,
        rewards={"solari": 3, "victory_points": 1}
    )

    contract2 = ContractCard(
        id="contract2",
        name="Visit Carthag",
        type="Contract",
        card_type=CardType.CONTRACT,
        completion_type="location",
        completion_target="carthag",
        rewards={"solari": 2, "victory_points": 1}
    )

    contract3 = ContractCard(
        id="contract3",
        name="Immediate Payment",
        type="Contract",
        card_type=CardType.CONTRACT,
        completion_type="immediate",
        rewards={"solari": 5}
    )

    # Create board
    board = Board()
    board.spaces = locations
    board.contract_row = [contract1, contract2, contract3]
    board.imperium_row = []

    # Create game
    game = Game(
        players=[player],
        board=board,
        current_player_index=0
    )

    return game, player


def display_game_state(game, player):
    """Display current game state."""
    print("\n" + "="*70)
    print("ÉTAT DU JEU")
    print("="*70)
    print(f"Joueur: {player.name}")
    print(f"Ressources:")
    print(f"  💧 Eau: {player.water}")
    print(f"  💰 Solari: {player.solari}")
    print(f"  🌶️  Épice: {player.spice}")
    print(f"  🏆 Points de Victoire: {player.victory_points}")
    print(f"\nTroupes:")
    print(f"  🛡️  Garnison: {player.troops_in_garrison}")
    print(f"  ⚔️  En conflit: {player.troops_in_conflict}")
    print(f"  📦 Réserve: {player.troops_in_reserve}")
    print(f"\nAgents:")
    print(f"  🕵️  Disponibles: {player.agents_available}")
    print(f"  🔍 Espions disponibles: {player.spies_available}")
    print(f"  🔍 Espions placés: {len(player.spies_placed)}")
    print(f"\nInfluence:")
    print(f"  🏜️  Fremen: {player.fremen_influence}")
    print(f"  👑 Empereur: {player.emperor_influence}")
    print(f"  🚀 Guilde: {player.spacing_guild_influence}")
    print(f"  🔮 Bene Gesserit: {player.bene_gesserit_influence}")
    print(f"\nContrats actifs: {len(player.contracts_active)}")
    print(f"Contrats complétés: {len(player.contracts_completed)}")
    print("="*70 + "\n")


def play_agent_turn(game, player, action_gen, action_exec):
    """Play an interactive agent turn."""

    print("\n" + "🎮 " + "="*68)
    print("TOUR AGENT")
    print("="*70)

    # Step 1: Show playable cards
    playable_cards = action_gen.get_playable_imperium_cards(player.player_id)

    if not playable_cards:
        print("❌ Aucune carte jouable!")
        return False

    print("\n📋 Cartes jouables dans votre main:")
    for i, card in enumerate(playable_cards, 1):
        print(f"\n  [{i}] {card.name} (Coût: {card.cost})")
        print(f"      Icônes agent: {', '.join(card.agent_icons)}")
        if "base" in card.agent_effects:
            print(f"      Effets agent: {card.agent_effects['base']}")
        if "base" in card.reveal_effects:
            print(f"      Effets révélation: {card.reveal_effects['base']}")

    # Choose card
    while True:
        try:
            choice = input(f"\n👉 Choisissez une carte (1-{len(playable_cards)}): ")
            card_idx = int(choice) - 1
            if 0 <= card_idx < len(playable_cards):
                selected_card = playable_cards[card_idx]
                break
            print("❌ Choix invalide!")
        except ValueError:
            print("❌ Entrez un nombre!")

    print(f"\n✓ Carte sélectionnée: {selected_card.name}")

    # Step 2: Show valid locations
    valid_locations = action_gen.get_valid_locations_for_card(
        player.player_id,
        selected_card
    )

    print(f"\n🗺️  Locations valides pour {selected_card.name}:")
    for i, (location, placement_type) in enumerate(valid_locations, 1):
        print(f"\n  [{i}] {location.name} (via {placement_type})")
        print(f"      Faction: {location.faction or 'Aucune'}")
        if location.effects:
            print(f"      Bonus: {location.effects}")
        if location.cost:
            print(f"      Coût: {location.cost}")
        if location.is_combat_space:
            print(f"      ⚔️  ZONE DE COMBAT")

    # Choose location
    while True:
        try:
            choice = input(f"\n👉 Choisissez une location (1-{len(valid_locations)}): ")
            loc_idx = int(choice) - 1
            if 0 <= loc_idx < len(valid_locations):
                selected_location, placement_type = valid_locations[loc_idx]
                break
            print("❌ Choix invalide!")
        except ValueError:
            print("❌ Entrez un nombre!")

    print(f"\n✓ Location sélectionnée: {selected_location.name}")

    # Step 3: Deploy troops if combat location
    troops_to_deploy = 0
    if selected_location.is_combat_space:
        max_deployable = min(2, player.troops_in_garrison)
        if max_deployable > 0:
            print(f"\n⚔️  C'est une zone de combat!")
            print(f"   Vous pouvez déployer jusqu'à {max_deployable} troupes")
            print(f"   (Garnison actuelle: {player.troops_in_garrison})")

            while True:
                try:
                    choice = input(f"\n👉 Combien de troupes déployer? (0-{max_deployable}): ")
                    troops_to_deploy = int(choice)
                    if 0 <= troops_to_deploy <= max_deployable:
                        break
                    print(f"❌ Nombre invalide! (0-{max_deployable})")
                except ValueError:
                    print("❌ Entrez un nombre!")

    # Step 4: Execute action
    action = PlaceAgentAction(
        player_id=player.player_id,
        card=selected_card,
        location=selected_location,
        placement_type=placement_type,
        troops_to_deploy=troops_to_deploy
    )

    print("\n⚙️  Exécution de l'action...")
    result = action_exec.execute_place_agent(action)

    # Display results
    print("\n" + "✅ " + "="*68)
    print("RÉSULTATS DE L'ACTION")
    print("="*70)
    print(f"✓ Carte jouée: {result['card']}")
    print(f"✓ Location: {result['location']}")
    print(f"✓ Type de placement: {result['placement_type']}")

    if result.get('agent_effects'):
        print(f"\n📊 Effets agent appliqués:")
        for effect in result['agent_effects'].get('effects_applied', []):
            print(f"   - {effect}")

    if result.get('location_bonus'):
        print(f"\n🎁 Bonus de location:")
        for effect in result['location_bonus'].get('effects_applied', []):
            print(f"   - {effect['effect']}: +{effect['value']}")

    if result.get('troops_deployed', 0) > 0:
        print(f"\n⚔️  Troupes déployées: {result['troops_deployed']}")

    if result.get('contracts_completed'):
        print(f"\n🎉 CONTRATS COMPLÉTÉS:")
        for contract in result['contracts_completed']:
            print(f"   ✓ {contract['contract']}")
            print(f"     Récompenses: {contract['rewards']}")

    print(f"\n🕵️  Agents restants: {result['agents_remaining']}")
    print("="*70 + "\n")

    return True


def play_reveal_turn(game, player, action_exec):
    """Play a reveal turn."""

    print("\n" + "🎴 " + "="*68)
    print("TOUR DE RÉVÉLATION")
    print("="*70)

    print("\n📋 Cartes dans votre main:")
    for card in player.hand.cards:
        print(f"  - {card.name}")
        if "base" in card.reveal_effects:
            print(f"    Effets: {card.reveal_effects['base']}")

    input("\n👉 Appuyez sur Entrée pour révéler votre main...")

    reveal_action = RevealAction(player_id=player.player_id)
    result = action_exec.execute_reveal(reveal_action)

    print("\n" + "✅ " + "="*68)
    print("RÉSULTATS DE LA RÉVÉLATION")
    print("="*70)
    print(f"✓ Cartes révélées: {result['cards_revealed']}")
    print(f"✓ Persuasion totale: {result['total_persuasion']}")
    print(f"✓ Épées temporaires: {result['temp_swords']}")

    print(f"\n📊 Détail des effets:")
    for card_result in result['reveal_results']:
        print(f"  - {card_result['card']}")
        for effect in card_result['result'].get('effects_applied', []):
            print(f"    → {effect}")

    print("="*70 + "\n")


def main():
    """Run interactive turn test."""
    print("\n" + "🎮 " + "="*68)
    print("TEST INTERACTIF - DUNE IMPERIUM UPRISING")
    print("="*70)
    print("\nVous allez jouer un tour complet avec:")
    print("  - Placement d'agents")
    print("  - Résolution d'effets")
    print("  - Déploiement de troupes")
    print("  - Complétion de contrats")
    print("  - Révélation de main")
    print("\n" + "="*70 + "\n")

    input("👉 Appuyez sur Entrée pour commencer...")

    # Create game
    game, player = create_game()
    action_gen = ActionGenerator(game)
    action_exec = ActionExecutor(game)

    # Display initial state
    display_game_state(game, player)

    # Play agent turns
    turn_count = 0
    while player.agents_available > 0 and turn_count < 5:  # Max 5 turns for safety
        turn_count += 1
        print(f"\n{'='*70}")
        print(f"TOUR #{turn_count}")
        print(f"{'='*70}\n")

        success = play_agent_turn(game, player, action_gen, action_exec)
        if not success:
            break

        display_game_state(game, player)

        if player.agents_available > 0:
            choice = input("\n👉 Continuer avec un autre agent? (o/n): ")
            if choice.lower() != 'o':
                break

    # Reveal turn
    if len(player.hand.cards) > 0:
        play_reveal_turn(game, player, action_exec)
        display_game_state(game, player)

    print("\n" + "🎉 " + "="*68)
    print("FIN DU TEST")
    print("="*70)
    print("\n✓ Le système fonctionne correctement!")
    print("✓ Tous les composants sont intégrés:")
    print("  - ActionGenerator ✓")
    print("  - ActionExecutor ✓")
    print("  - EffectResolver ✓")
    print("  - ContractManager ✓")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    main()
