"""
Deck Manager - Manages player deck operations (draw, discard, shuffle, acquire, trash).

Responsibilities:
- Draw cards from player's deck
- Discard played cards at end of turn
- Auto-shuffle discard pile into deck when empty
- Acquire cards from Imperium row using persuasion
- Trash cards (remove from game)
- Refill Imperium row after acquisitions
"""

from typing import Dict, Any, List, Optional
from ..models.game import Game
from ..models.player import Player
from ..models.card import ImperiumCard, Card
from .game_state import GameState


class DeckManager:
    """
    Manages all deck operations for players.

    Operations:
    1. Draw cards from deck (auto-shuffle discard when empty)
    2. Discard played cards at end of turn
    3. Acquire cards from Imperium row
    4. Trash cards (remove from game)
    5. Refill Imperium row
    """

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    # ==================== DRAW OPERATIONS ====================

    def draw_cards(self, player_id: str, count: int) -> Dict[str, Any]:
        """
        Draw cards from player's deck into their hand.

        Auto-shuffles discard pile into deck if needed.

        Args:
            player_id: Player drawing cards
            count: Number of cards to draw

        Returns:
            Dict with draw results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        drawn_cards = []

        for _ in range(count):
            # Try to draw from deck (Deck.draw auto-shuffles discard if needed)
            card = player.deck.draw(discard_pile=player.discard_pile)

            if card is None:
                # No more cards available (deck and discard both empty)
                break

            # Add to hand
            player.hand.add_card(card)
            drawn_cards.append(card)

        return {
            "success": True,
            "cards_drawn": len(drawn_cards),
            "cards": [card.name for card in drawn_cards],
            "hand_size": player.hand.size,
            "deck_size": player.deck.size,
            "discard_size": player.discard_pile.size
        }

    def draw_starting_hand(self, player_id: str) -> Dict[str, Any]:
        """
        Draw 5 cards at start of round.

        Args:
            player_id: Player drawing

        Returns:
            Dict with draw results
        """
        return self.draw_cards(player_id, 5)

    # ==================== DISCARD OPERATIONS ====================

    def discard_played_cards(self, player_id: str) -> Dict[str, Any]:
        """
        Move all cards played this turn to discard pile.

        Called at end of reveal turn.

        Args:
            player_id: Player discarding

        Returns:
            Dict with discard results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        # Get played cards from player's temporary tracking
        played_cards = getattr(player, 'played_cards_this_turn', [])

        if not played_cards:
            return {
                "success": True,
                "cards_discarded": 0,
                "message": "No cards were played this turn"
            }

        # Move to discard pile
        for card in played_cards:
            player.discard_pile.add_card(card)

        cards_count = len(played_cards)

        # Clear played cards tracking
        player.played_cards_this_turn = []

        return {
            "success": True,
            "cards_discarded": cards_count,
            "discard_size": player.discard_pile.size
        }

    def discard_hand(self, player_id: str) -> Dict[str, Any]:
        """
        Discard entire hand (e.g., at end of round).

        Args:
            player_id: Player discarding hand

        Returns:
            Dict with discard results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        cards_count = player.hand.size

        # Move all cards from hand to discard
        while not player.hand.is_empty:
            card = player.hand.draw()
            if card:
                player.discard_pile.add_card(card)

        return {
            "success": True,
            "cards_discarded": cards_count,
            "discard_size": player.discard_pile.size
        }

    # ==================== ACQUIRE OPERATIONS ====================

    def acquire_card_from_imperium(
        self,
        player_id: str,
        card: ImperiumCard,
        persuasion_cost: int
    ) -> Dict[str, Any]:
        """
        Acquire a card from the Imperium row.

        Process:
        1. Validate player has enough persuasion
        2. Remove card from Imperium row
        3. Add to player's discard pile
        4. Deduct persuasion
        5. Refill Imperium row

        Args:
            player_id: Player acquiring card
            card: Card being acquired
            persuasion_cost: Cost in persuasion

        Returns:
            Dict with acquisition results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        # Check persuasion
        temp_persuasion = getattr(player, 'temp_persuasion', 0)
        if temp_persuasion < persuasion_cost:
            return {
                "success": False,
                "error": f"Not enough persuasion (need {persuasion_cost}, have {temp_persuasion})"
            }

        # Check card is in Imperium row
        if card not in self.game.board.imperium_row:
            return {
                "success": False,
                "error": "Card not in Imperium row"
            }

        # Remove from Imperium row
        self.game.board.imperium_row.remove(card)

        # Add to player's discard pile
        player.discard_pile.add_card(card)

        # Deduct persuasion
        player.temp_persuasion -= persuasion_cost

        # Refill Imperium row
        self.game.board.refill_imperium_row()

        return {
            "success": True,
            "card_acquired": card.name,
            "persuasion_spent": persuasion_cost,
            "persuasion_remaining": player.temp_persuasion,
            "discard_size": player.discard_pile.size
        }

    def acquire_reserve_card(
        self,
        player_id: str,
        card_type: str,
        persuasion_cost: int
    ) -> Dict[str, Any]:
        """
        Acquire a card from reserve piles (Prepare the Way, Spice Must Flow).

        Args:
            player_id: Player acquiring card
            card_type: "prepare_the_way" or "spice_must_flow"
            persuasion_cost: Cost in persuasion (2 or 8)

        Returns:
            Dict with acquisition results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        # Check persuasion
        temp_persuasion = getattr(player, 'temp_persuasion', 0)
        if temp_persuasion < persuasion_cost:
            return {
                "success": False,
                "error": f"Not enough persuasion (need {persuasion_cost}, have {temp_persuasion})"
            }

        # Get reserve pile
        if card_type == "prepare_the_way":
            reserve_pile = self.game.board.reserve_prepare_the_way
        elif card_type == "spice_must_flow":
            reserve_pile = self.game.board.reserve_spice_must_flow
        else:
            return {
                "success": False,
                "error": f"Unknown reserve type: {card_type}"
            }

        if not reserve_pile:
            return {
                "success": False,
                "error": f"Reserve pile {card_type} is empty"
            }

        # Take card from reserve
        card = reserve_pile.pop(0)

        # Add to player's discard pile
        player.discard_pile.add_card(card)

        # Deduct persuasion
        player.temp_persuasion -= persuasion_cost

        return {
            "success": True,
            "card_acquired": card.name,
            "persuasion_spent": persuasion_cost,
            "persuasion_remaining": player.temp_persuasion,
            "discard_size": player.discard_pile.size
        }

    # ==================== TRASH OPERATIONS ====================

    def trash_card(
        self,
        player_id: str,
        card: Card,
        source: str = "hand"
    ) -> Dict[str, Any]:
        """
        Trash a card (remove from game permanently).

        Args:
            player_id: Player trashing card
            card: Card to trash
            source: Where card is coming from ("hand", "played", "discard")

        Returns:
            Dict with trash results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        # Determine source and remove card
        removed = False

        if source == "hand":
            removed = player.hand.remove(card)
        elif source == "played":
            played_cards = getattr(player, 'played_cards_this_turn', [])
            if card in played_cards:
                played_cards.remove(card)
                player.played_cards_this_turn = played_cards
                removed = True
        elif source == "discard":
            removed = player.discard_pile.remove(card)
        else:
            return {
                "success": False,
                "error": f"Unknown source: {source}"
            }

        if not removed:
            return {
                "success": False,
                "error": f"Card not found in {source}"
            }

        # Card is now removed from game (not added anywhere)

        return {
            "success": True,
            "card_trashed": card.name,
            "source": source,
            "message": f"Card '{card.name}' removed from game"
        }

    # ==================== QUERIES ====================

    def get_deck_state(self, player_id: str) -> Dict[str, Any]:
        """
        Get current deck state for a player.

        Args:
            player_id: Player to check

        Returns:
            Dict with deck statistics
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        return {
            "success": True,
            "player": player.name,
            "hand_size": player.hand.size,
            "deck_size": player.deck.size,
            "discard_size": player.discard_pile.size,
            "played_this_turn": len(getattr(player, 'played_cards_this_turn', []))
        }

    def get_acquirable_cards(self, player_id: str) -> Dict[str, Any]:
        """
        Get list of cards player can acquire with current persuasion.

        Args:
            player_id: Player to check

        Returns:
            Dict with acquirable cards
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {
                "success": False,
                "error": "Player not found"
            }

        temp_persuasion = getattr(player, 'temp_persuasion', 0)

        # Get cards from Imperium row player can afford
        acquirable = [
            {
                "card": card,
                "name": card.name,
                "cost": card.cost
            }
            for card in self.game.board.imperium_row
            if card.cost <= temp_persuasion
        ]

        # Check reserve piles
        reserve_options = []
        if self.game.board.reserve_prepare_the_way and temp_persuasion >= 2:
            reserve_options.append({
                "type": "prepare_the_way",
                "cost": 2,
                "available": len(self.game.board.reserve_prepare_the_way)
            })
        if self.game.board.reserve_spice_must_flow and temp_persuasion >= 8:
            reserve_options.append({
                "type": "spice_must_flow",
                "cost": 8,
                "available": len(self.game.board.reserve_spice_must_flow)
            })

        return {
            "success": True,
            "persuasion": temp_persuasion,
            "imperium_cards": acquirable,
            "reserve_cards": reserve_options
        }
