"""
Bot AI package for DUNE: Imperium Uprising.

Available bots:
- RandomBot: Plays randomly but always tries to take actions
- HeuristicBot: Scores legal actions and picks the best
"""

from .base_bot import BaseBot
from .random_bot import RandomBot
from .heuristic_bot import HeuristicBot

__all__ = ["BaseBot", "RandomBot", "HeuristicBot"]
