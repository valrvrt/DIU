"""
Bot AI package for DUNE: Imperium Uprising.

Available bots:
- RandomBot: Plays randomly but always tries to take actions
"""

from .base_bot import BaseBot
from .random_bot import RandomBot

__all__ = ["BaseBot", "RandomBot"]
