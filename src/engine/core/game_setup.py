"""
Game Setup - Initialize a complete game with all components.

Responsibilities:
- Create players with starting decks and hands
- Distribute objective cards and determine first player
- Initialize board with all decks and cards
- Set up conflict deck (by level)
- Prepare imperium row, contracts, intrigue deck
"""

import random
from typing import List, Tuple, Dict, Any
from ...models.game import Game, GamePhase
from ...models.player import Player
from ...models.board import Board
from ...models.deck import Deck
from ...loaders.card_loader import (
    load_starter_deck, load_imperium_cards, load_intrigue_cards,
    load_conflict_cards, load_contract_cards,
    get_objectives_for_player_count, get_reserve_cards, ObjectiveCard
)
from ...loaders.leader_loader import load_leaders
from ...loaders.board_loader import load_board_spaces, load_observation_posts


class GameSetup:
    """
    Setup a complete game from scratch.

    Process:
    1. Choose number of players (3 or 4)
    2. Assign objectives and determine first player
    3. Give starting decks and hands
    4. Initialize board spaces
    5. Setup imperium row + deck + reserve cards
    6. Setup conflict deck (1 level 1, 5 level 2, 4 level 3)
    7. Setup intrigue deck (shuffled)
    8. Setup contract row (2 visible, rest in deck)
    """

    @staticmethod
    def get_available_leaders():
        """
        Get all leaders available for selection.

        Returns:
            List of Leader objects (excludes Reverend Mother)
        """
        all_leaders = load_leaders()
        # Filter out Reverend Mother (transformed form, not selectable)
        return [l for l in all_leaders if l.name != "Reverend Mother"]

    @staticmethod
    def create_game(player_count: int, human_player_name: str = "Player", selected_leaders: List[int] = None) -> Tuple[Game, Dict[str, Any]]:
        """
        Create a fully initialized game.

        Args:
            player_count: 3 or 4 players
            human_player_name: Name for the human player
            selected_leaders: Optional list of leader IDs for each player (must be unique, no Reverend Mother)

        Returns:
            (game, setup_info) where setup_info contains:
            {
                "human_player_id": str,
                "first_player_idx": int,
                "objectives": List[ObjectiveCard]
            }
        """
        if player_count not in [3, 4]:
            raise ValueError("Player count must be 3 or 4")

        # 1. Load all game data
        all_leaders = load_leaders()

        # Filter out Reverend Mother (she's the transformed side of Lady Jessica, not selectable)
        selectable_leaders = [l for l in all_leaders if l.name != "Reverend Mother"]

        starter_deck_cards = load_starter_deck()

        # 2. Validate and assign leaders
        if selected_leaders:
            if len(selected_leaders) != player_count:
                raise ValueError(f"Must provide exactly {player_count} leader IDs")

            # Check for duplicates
            if len(set(selected_leaders)) != len(selected_leaders):
                raise ValueError("Each player must have a unique leader")

            # Verify all leader IDs are valid and not Reverend Mother
            assigned_leaders = []
            for leader_id in selected_leaders:
                leader = next((l for l in selectable_leaders if l.leader_id == leader_id), None)
                if not leader:
                    raise ValueError(f"Invalid leader ID: {leader_id} or Reverend Mother cannot be selected")
                assigned_leaders.append(leader)
        else:
            # Random leader selection (ensure uniqueness)
            assigned_leaders = random.sample(selectable_leaders, player_count)

        # 3. Create players
        players = []
        player_names = [human_player_name] + [f"Bot {i}" for i in range(1, player_count)]
        player_colors = ["blue", "red", "green", "yellow"][:player_count]

        for i in range(player_count):
            # Get assigned leader
            leader = assigned_leaders[i]

            # Create player deck with starter cards (7 cards)
            # Apply leader-specific deck modifications if available
            cards_to_add = list(starter_deck_cards)  # Make a copy
            if hasattr(leader, 'modify_starting_deck') and callable(leader.modify_starting_deck):
                cards_to_add = leader.modify_starting_deck(cards_to_add)

            player_deck = Deck()
            for card in cards_to_add:
                player_deck.add_card(card)

            # Shuffle deck
            player_deck.shuffle()

            # Create player
            player = Player(
                player_id=f"p{i}",
                name=player_names[i],
                leader=leader,
                color=player_colors[i],
                deck=player_deck,
                hand=Deck(),
                discard_pile=Deck(),
                # Starting resources
                water=1,
                solari=0,
                spice=0,
                victory_points=0,
                # Troops
                troops_in_garrison=3,
                troops_in_reserve=9,
                troops_in_conflict=0,
                # Agents
                agents_available=2,
                total_available_agents=2,
                # Spies
                spies_available=3,
                total_available_spies=3,
                # Influence
                fremen_influence=0,
                bene_gesserit_influence=0,
                spacing_guild_influence=0,
                emperor_influence=0,
                # Player type
                is_human=(i == 0)  # First player is always the human
            )

            # Draw starting hand (5 cards)
            for _ in range(5):
                drawn = player.deck.draw()
                if drawn:
                    player.hand.add_card(drawn)

            players.append(player)

        # 3. Distribute objectives and determine first player
        objectives = get_objectives_for_player_count(player_count)
        random.shuffle(objectives)

        first_player_idx = 0
        for i, player in enumerate(players):
            if i < len(objectives):
                objective_card = objectives[i]
                player.objectives.append(objective_card)

                # Access the attribute directly using a dot instead of a bracket
                if objective_card.id == 2:
                    first_player_idx = i

        # 4. Initialize board
        board = Board()
        board.spaces = load_board_spaces()
        board.observation_posts = load_observation_posts()

        # 5. Setup imperium row + deck + reserve
        all_imperium_cards = load_imperium_cards()

        # Separate reserve cards
        reserve_cards = get_reserve_cards()
        board.reserve_prepare_the_way = reserve_cards.get('prepare_the_way', [])
        board.reserve_spice_must_flow = reserve_cards.get('spice_must_flow', [])

        # Filter out reserve cards from main deck
        imperium_deck = [
            card for card in all_imperium_cards
            if 'prepare' not in card.id.lower() and 'spice_must_flow' not in card.id.lower()
        ]

        # Shuffle and setup imperium row (first 6 cards visible)
        random.shuffle(imperium_deck)
        board.imperium_row = imperium_deck[:6]
        board.imperium_deck = imperium_deck[6:]

        # 6. Setup conflict deck (by level)
        all_conflicts = load_conflict_cards()

        # Separate by level
        level_1 = [c for c in all_conflicts if getattr(c, 'level', 1) == 1]
        level_2 = [c for c in all_conflicts if getattr(c, 'level', 2) == 2]
        level_3 = [c for c in all_conflicts if getattr(c, 'level', 3) == 3]

        # Shuffle each level
        random.shuffle(level_1)
        random.shuffle(level_2)
        random.shuffle(level_3)

        # Build conflict deck: 1 level 1, 5 level 2, 4 level 3
        conflict_deck = []
        conflict_deck.extend(level_1[:1])  # 1 level 1
        conflict_deck.extend(level_2[:5])  # 5 level 2
        conflict_deck.extend(level_3[:4])  # 4 level 3

        board.conflict_deck = conflict_deck
        board.current_conflict = None
        board.resolved_conflicts = []

        # 7. Setup intrigue deck (shuffled)
        intrigue_cards = load_intrigue_cards()
        random.shuffle(intrigue_cards)
        board.intrigue_deck = intrigue_cards

        # 8. Setup contract row (2 visible, rest in deck)
        contract_cards = load_contract_cards()
        random.shuffle(contract_cards)
        board.contract_row = contract_cards[:2]
        board.contract_deck = contract_cards[2:]

        # 9. Create game
        game = Game(
            players=players,
            board=board,
            current_phase=GamePhase.SETUP,
            current_round=0,
            player_count=player_count,
            first_player_index=first_player_idx,
            current_player_index=first_player_idx
        )

        setup_info = {
            "human_player_id": players[0].player_id,
            "first_player_idx": first_player_idx,
            "first_player_name": players[first_player_idx].name,
            "objectives": [obj.name for obj in objectives[:player_count]],
            "conflict_deck_size": len(conflict_deck),
            "imperium_deck_size": len(board.imperium_deck),
            "intrigue_deck_size": len(board.intrigue_deck),
            "contract_deck_size": len(board.contract_deck)
        }

        return game, setup_info

    @staticmethod
    def validate_game_setup(game: Game) -> Dict[str, bool]:
        """
        Validate that game was set up correctly.

        Returns:
            Dict of validation checks
        """
        checks = {}

        # Check players
        checks["has_players"] = len(game.players) in [3, 4]
        checks["all_players_have_hands"] = all(len(p.hand.cards) == 5 for p in game.players)
        checks["all_players_have_decks"] = all(len(p.deck.cards) == 5 for p in game.players)  # 10 starter - 5 drawn
        checks["all_players_have_objectives"] = all(len(p.objectives) > 0 for p in game.players)

        # Check board
        checks["has_board_spaces"] = len(game.board.spaces) > 0
        checks["has_imperium_row"] = len(game.board.imperium_row) == 6
        checks["has_conflict_deck"] = len(game.board.conflict_deck) == 10  # 1+5+4
        checks["has_intrigue_deck"] = len(game.board.intrigue_deck) > 0
        checks["has_contract_row"] = len(game.board.contract_row) == 2

        # Check first player
        desert_mouse_holder = None
        for i, player in enumerate(game.players):
            for obj in player.objectives:
                if obj.id == 2:
                    desert_mouse_holder = i
                    break

        checks["first_player_has_desert_mouse"] = desert_mouse_holder == game.first_player_index

        return checks
