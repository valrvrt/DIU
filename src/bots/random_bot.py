"""
Random Bot - Makes random decisions but always tries to take actions.
"""

import random
from typing import Optional, List

from .base_bot import BaseBot
from ..models.card import ImperiumCard, IntrigueCard
from ..engine.actions.action_executor import PlaceAgentAction


class RandomBot(BaseBot):
    """
    A bot that makes random decisions but always tries to play actively.

    Strategy:
    - Never reveals on turn 1 if it has playable cards
    - Always tries to place agents if possible
    - Buys random cards when it can afford them
    - Deploys random amount of troops
    - Plays intrigue cards randomly
    """

    def __init__(self, player, managers):
        """Initialize the random bot."""
        super().__init__(player, managers)
        self.game = managers.get("game")

    def decide_agent_action(self) -> Optional[PlaceAgentAction]:
        """
        Decide whether to place an agent.

        Strategy:
        - Get all playable cards
        - If no playable cards, must reveal
        - If has playable cards, pick one at random
        - Find valid locations for that card
        - If no valid locations, try another card
        - Return placement action or None to reveal
        """
        # Get playable cards
        playable_cards = self.get_playable_cards()

        if not playable_cards:
            # No playable cards - must reveal
            return None

        # Shuffle cards to try them in random order
        random.shuffle(playable_cards)

        for card in playable_cards:
            # Get valid locations for this card
            locations = self.get_valid_locations_for_card(card)

            if locations:
                # Pick a random location
                location, placement_type = random.choice(locations)

                # Determine troops to deploy (if applicable)
                troops_to_deploy = 0
                if placement_type == "normal" and self.player.troops_in_garrison > 0:
                    # Randomly deploy 0-2 troops if available
                    max_deploy = min(2, self.player.troops_in_garrison)
                    troops_to_deploy = random.randint(0, max_deploy)

                # Create and return the action
                return PlaceAgentAction(
                    player_id=self.player.player_id,
                    card=card,
                    location=location,
                    placement_type=placement_type,
                    troops_to_deploy=troops_to_deploy
                )

        # No valid moves found - must reveal
        return None

    def decide_card_to_acquire(self, available_cards: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """
        Choose which card to acquire.

        Strategy:
        - Filter cards we can afford
        - Pick one at random
        - 80% chance to buy if we can afford something
        - 20% chance to skip (save persuasion for better cards)
        """
        if not available_cards:
            return None

        # Filter affordable cards
        affordable = [card for card in available_cards if self.can_afford_card(card)]

        if not affordable:
            return None

        # 80% chance to buy
        if random.random() < 0.8:
            return random.choice(affordable)
        else:
            return None

    def decide_intrigue_to_play(self, available_intrigues: List[IntrigueCard]) -> Optional[IntrigueCard]:
        """
        Choose intrigue card to play during combat.

        Strategy:
        - 60% chance to play an intrigue if we have one
        - Pick random intrigue
        """
        if not available_intrigues:
            return None

        # 60% chance to play
        if random.random() < 0.6:
            return random.choice(available_intrigues)
        else:
            return None

    def decide_troops_to_deploy(self, max_troops: int) -> int:
        """
        Decide how many troops to deploy.

        Strategy:
        - Deploy a random number between 0 and max
        - Slight bias toward deploying (70% chance to deploy at least 1)
        """
        if max_troops == 0:
            return 0

        # 70% chance to deploy at least 1 troop
        if random.random() < 0.7:
            # Deploy 1 to max_troops
            return random.randint(1, max_troops)
        else:
            # Don't deploy
            return 0

    def decide_card_to_discard(self, hand: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """
        Choose card to discard during recall.

        Strategy:
        - Prefer to discard starter cards (lower cost)
        - Random choice among lowest cost cards
        """
        if not hand:
            return None

        # Sort by cost (discard cheapest cards first)
        sorted_hand = sorted(hand, key=lambda c: c.cost)

        # Get all cards with the lowest cost
        min_cost = sorted_hand[0].cost
        cheapest_cards = [card for card in sorted_hand if card.cost == min_cost]

        # Pick one at random
        return random.choice(cheapest_cards)

    def should_reveal(self) -> bool:
        """
        Decide if bot should reveal.

        This is called by the game loop to determine if bot wants to reveal
        instead of checking if decide_agent_action returns None.
        """
        # Let decide_agent_action make this decision
        action = self.decide_agent_action()
        return action is None
