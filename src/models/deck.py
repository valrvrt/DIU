from dataclasses import dataclass, field
from typing import Optional
import random
from .card import Card, IntrigueCard, ContractCard, ConflictCard, ImperiumCard

@dataclass
class Deck:
    cards: list[Card] = field(default_factory=list)
    seed: Optional[int] = None  # For reproducible shuffling
    
    @property
    def size(self) -> int:
        return len(self.cards)
    
    @property
    def is_empty(self) -> bool:
        return len(self.cards) == 0
    
    def draw(self, discard_pile: Optional['Deck'] = None) -> Optional[Card]:
        """
        Draw a card. If deck is empty and discard_pile provided,
        shuffle discard into deck before drawing.
        """
        if self.is_empty and discard_pile and not discard_pile.is_empty:
            # Shuffle discard into deck
            self.cards = discard_pile.cards
            discard_pile.cards = []
            self.shuffle()
        
        if self.is_empty:
            return None
        
        card = self.cards.pop(0)  # Draw from top
        return card
    
    def add_card(self, card: Card):
        """Add a single card (e.g., to discard pile)"""
        if not isinstance(card, Card):
            raise TypeError(f"Expected a Card instance, got {type(card).__name__}")
        self.cards.append(card)
    
    def shuffle(self):
        """Shuffle the deck using seeded RNG for reproducibility"""
        if self.seed is not None:
            rng = random.Random(self.seed)
            rng.shuffle(self.cards)
        else:
            random.shuffle(self.cards)
    
    def __add__(self, other: 'Deck') -> 'Deck':
        """Create a new combined deck"""
        if not isinstance(other, Deck):
            raise TypeError(f"Can only add Deck to Deck, not {type(other).__name__}")
        return Deck(cards=self.cards + other.cards, seed=self.seed)

    def remove(self, card: Card) -> bool:
        """Remove a specific card from the deck. Returns True if removed."""
        try:
            self.cards.remove(card)
            return True
        except ValueError:
            return False