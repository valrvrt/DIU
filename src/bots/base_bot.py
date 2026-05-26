"""
Base Bot class for AI players.
"""

from typing import Dict, Any, Optional, List, Tuple
from abc import ABC, abstractmethod

from ..models.player import Player
from ..models.card import ImperiumCard, IntrigueCard
from ..models.boardspace import BoardSpace
from ..engine.actions.action_executor import (
    PlaceAgentAction, RevealAction, AcquireCardAction, PlayIntrigueAction
)


class BaseBot(ABC):
    """
    Abstract base class for all bot AI implementations.

    Bots make decisions during different phases of the game:
    - Agent phase: Play cards and place agents
    - Reveal phase: Choose to reveal hand
    - Combat phase: Deploy troops, play intrigue cards
    - Recall phase: Choose cards to discard
    """

    def __init__(self, player: Player, managers: Dict[str, Any]):
        """
        Initialize the bot.

        Args:
            player: The Player object this bot controls
            managers: Dictionary of game managers (action_generator, action_executor, etc.)
        """
        self.player = player
        self.managers = managers

    @property
    def action_generator(self):
        """Get the ActionGenerator."""
        return self.managers.get("action_generator")

    @property
    def action_executor(self):
        """Get the ActionExecutor."""
        return self.managers.get("action_executor")

    @abstractmethod
    def decide_agent_action(self) -> Optional[PlaceAgentAction]:
        """
        Decide whether to place an agent or reveal.

        Returns:
            PlaceAgentAction if bot wants to place agent, None if bot wants to reveal
        """
        pass

    @abstractmethod
    def decide_card_to_acquire(self, available_cards: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """
        Choose which card to acquire from the imperium row.

        Args:
            available_cards: List of cards the player can afford

        Returns:
            Card to acquire, or None to skip
        """
        pass

    @abstractmethod
    def decide_intrigue_to_play(self, available_intrigues: List[IntrigueCard]) -> Optional[IntrigueCard]:
        """
        Choose which intrigue card to play during combat.

        Args:
            available_intrigues: List of playable intrigue cards

        Returns:
            Intrigue card to play, or None to skip
        """
        pass

    @abstractmethod
    def decide_troops_to_deploy(self, max_troops: int) -> int:
        """
        Decide how many troops to deploy to conflict.

        Args:
            max_troops: Maximum troops available to deploy

        Returns:
            Number of troops to deploy (0 to max_troops)
        """
        pass

    @abstractmethod
    def decide_card_to_discard(self, hand: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """
        Choose which card to discard during recall phase.

        Args:
            hand: List of cards in hand

        Returns:
            Card to discard, or None if no discard needed
        """
        pass

    def get_playable_cards(self) -> List[ImperiumCard]:
        """Helper: Get all playable imperium cards."""
        return self.action_generator.get_playable_imperium_cards(self.player.player_id)

    def get_valid_locations_for_card(self, card: ImperiumCard) -> List[Tuple[BoardSpace, str]]:
        """Helper: Get valid locations for a card."""
        return self.action_generator.get_valid_locations_for_card(self.player.player_id, card)

    def can_afford_card(self, card: ImperiumCard) -> bool:
        """Helper: Check if player can afford a card."""
        persuasion = getattr(self.player, "temp_persuasion", 0)
        return persuasion >= card.cost
