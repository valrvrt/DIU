"""
Interactive Effect Ordering System

Allows players to choose the order in which effects are resolved during:
- Agent Phase: Card effects + Board space effects
- Reveal Phase: Reveal effects + Acquisitions

Players can also interleave special actions:
- Deploy troops to conflict
- Play intrigue cards (after agent placed)
"""

from typing import List, Dict, Any, Optional, Callable


class EffectOrderingManager:
    """
    Manages player choices for effect resolution order.

    Supports:
    - Interactive ordering for human players
    - Heuristic ordering for bots
    - Interleaving special actions (troops, intrigue)
    """

    def __init__(self, get_player_input_fn: Optional[Callable] = None):
        """
        Initialize effect ordering manager.

        Args:
            get_player_input_fn: Function to get input from human player
                                 If None, uses heuristic ordering for all players
        """
        self.get_player_input_fn = get_player_input_fn

    def order_effects_interactive(
        self,
        player_id: str,
        effects: List[Dict[str, Any]],
        context: Dict[str, Any],
        is_human: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get ordered effects with player interaction.

        Args:
            player_id: Player who will resolve effects
            effects: List of effect objects to order
            context: Context (phase, card/location, etc.)
            is_human: Whether this is a human player

        Returns:
            Ordered list of effects
        """
        if len(effects) <= 1:
            return effects

        if is_human and self.get_player_input_fn:
            return self._order_effects_human(player_id, effects, context)
        else:
            return self._order_effects_heuristic(effects)

    def _order_effects_human(
        self,
        player_id: str,
        effects: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Let human player choose effect order interactively.

        Args:
            player_id: Player choosing order
            effects: Effects to order
            context: Resolution context

        Returns:
            Ordered effects list
        """
        print("\n" + "="*80)
        print("CHOOSE EFFECT RESOLUTION ORDER")
        print("="*80)

        phase = context.get("phase", "unknown")
        card_name = context.get("card", "")
        location_name = context.get("location", "")

        if phase == "agent":
            print(f"Card: {card_name}")
            print(f"Location: {location_name}")
        elif phase == "reveal":
            print(f"Revealing: {card_name}")

        print("\nAvailable effects:")
        for i, effect in enumerate(effects, 1):
            effect_desc = self._describe_effect(effect)
            print(f"  {i}. {effect_desc}")

        print("\nYou will choose effects one at a time.")
        print("You can also choose special actions:")
        print("  D - Deploy troops to conflict")
        print("  I - Play an intrigue card")
        print("  A - Acquire a card from imperium row (reveal phase only)")

        ordered = []
        remaining = list(effects)

        while remaining:
            print(f"\n{len(remaining)} effect(s) remaining.")

            # Show remaining effects
            print("Remaining effects:")
            for i, effect in enumerate(remaining, 1):
                print(f"  {i}. {self._describe_effect(effect)}")

            print("\nChoose next effect to resolve (number), or special action (D/I/A):")

            if self.get_player_input_fn:
                try:
                    choice = self.get_player_input_fn("Choice: ").strip().upper()
                except (StopIteration, EOFError):
                    # Input exhausted, resolve remaining in heuristic order
                    ordered.extend(self._order_effects_heuristic(remaining))
                    break
            else:
                # Fallback to heuristic if no input function
                return self._order_effects_heuristic(effects)

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(remaining):
                    chosen = remaining.pop(idx)
                    ordered.append(chosen)
                    print(f"✓ Will resolve: {self._describe_effect(chosen)}")
                else:
                    print("Invalid number. Try again.")
            elif choice == 'D':
                # Insert troop deployment action
                ordered.append({"type": "_deploy_troops_action"})
                print("✓ Will prompt for troop deployment")
            elif choice == 'I':
                # Insert intrigue play action
                ordered.append({"type": "_play_intrigue_action"})
                print("✓ Will prompt to play intrigue card")
            elif choice == 'A' and phase == "reveal":
                # Insert acquisition action
                ordered.append({"type": "_acquire_card_action"})
                print("✓ Will prompt for card acquisition")
            else:
                print("Invalid choice. Try again.")

        return ordered

    def _order_effects_heuristic(self, effects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply heuristic ordering for bots.

        Heuristic priority:
        1. Resource gains (enable future actions)
        2. Draw cards (more options)
        3. Influence (long-term benefit)
        4. Other effects

        Args:
            effects: List of effect objects

        Returns:
            Ordered list of effects
        """
        def effect_priority(effect):
            """Return priority score (lower = resolve first)"""
            effect_type = effect.get("type", "")

            # Resource gains first
            if effect_type == "resource":
                resource = effect.get("resource", "")
                if resource in ["solari", "spice", "water"]:
                    return 1  # Currency first
                elif resource == "troop":
                    return 2  # Troops second
                else:
                    return 3  # Other resources

            # Draw cards second
            elif effect_type == "draw":
                return 4

            # Influence third
            elif effect_type == "influence":
                return 5

            # Play/trash/steal
            elif effect_type in ["play", "trash", "steal", "recall"]:
                return 6

            # Everything else
            else:
                return 10

        return sorted(effects, key=effect_priority)

    def _describe_effect(self, effect: Dict[str, Any]) -> str:
        """
        Create human-readable description of an effect.

        Args:
            effect: Effect object

        Returns:
            Description string
        """
        effect_type = effect.get("type", "unknown")

        if effect_type == "resource":
            resource = effect.get("resource", "")
            amount = effect.get("amount", 1)
            return f"Gain {amount} {resource}"

        elif effect_type == "draw":
            deck = effect.get("deck", "deck")
            amount = effect.get("amount", 1)
            deck_name = "intrigue" if deck == "intrigue" else "your deck"
            return f"Draw {amount} card(s) from {deck_name}"

        elif effect_type == "influence":
            target = effect.get("target", "")
            amount = effect.get("amount", 1)
            if target == "agent":
                return f"Gain {amount} influence with faction of board space"
            else:
                return f"Gain {amount} {target} influence"

        elif effect_type == "play":
            unit = effect.get("unit", "agent")
            return f"Play {unit}"

        elif effect_type == "trash":
            deck = effect.get("deck", "hand")
            amount = effect.get("amount", 1)
            return f"Trash {amount} card(s) from {deck}"

        elif effect_type == "discard":
            amount = effect.get("amount", 1)
            return f"Discard {amount} card(s)"

        elif effect_type == "recall":
            return "Recall an agent"

        elif effect_type == "steal":
            return "Steal from opponent"

        elif effect_type == "control":
            return "Take control of location"

        elif effect_type == "conditional":
            return "Conditional effect (if condition met)"

        elif effect_type == "choice":
            return "Choose between options"

        elif effect_type == "multiple":
            per = effect.get("per", "")
            return f"Effect per {per}"

        else:
            return f"{effect_type} effect"


# Singleton instance for easy access
_effect_ordering_manager = None


def get_effect_ordering_manager(get_input_fn: Optional[Callable] = None) -> EffectOrderingManager:
    """
    Get or create the effect ordering manager singleton.

    Args:
        get_input_fn: Optional function to get player input

    Returns:
        EffectOrderingManager instance
    """
    global _effect_ordering_manager
    if _effect_ordering_manager is None:
        _effect_ordering_manager = EffectOrderingManager(get_input_fn)
    return _effect_ordering_manager


def set_player_input_function(fn: Callable):
    """
    Set the function used to get input from human players.

    Args:
        fn: Function that takes a prompt string and returns player input
    """
    global _effect_ordering_manager
    if _effect_ordering_manager is None:
        _effect_ordering_manager = EffectOrderingManager(fn)
    else:
        _effect_ordering_manager.get_player_input_fn = fn
