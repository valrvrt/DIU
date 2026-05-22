"""
Interactive Effect Resolution with Special Actions

Handles resolving effects one-by-one with interleaved special actions:
- Deploy troops to conflict
- Play intrigue cards
- Acquire cards (reveal phase)
"""

from typing import Dict, List, Any, Optional, Callable


class InteractiveEffectResolver:
    """
    Resolves effects with player interaction and special action interleaving.
    """

    def __init__(self, action_executor, effect_resolver):
        """
        Initialize interactive resolver.

        Args:
            action_executor: ActionExecutor instance
            effect_resolver: EffectResolver instance
        """
        self.action_executor = action_executor
        self.effect_resolver = effect_resolver

    def resolve_effects_interactive(
        self,
        player_id: str,
        ordered_effects: List[Dict[str, Any]],
        context: Dict[str, Any],
        get_input_fn: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Resolve effects one by one, handling special action markers.

        Special action types:
        - _deploy_troops_action: Prompt player to deploy troops
        - _play_intrigue_action: Prompt player to play intrigue
        - _acquire_card_action: Prompt player to acquire card

        Args:
            player_id: Player resolving effects
            ordered_effects: List of effects and special actions
            context: Resolution context
            get_input_fn: Function to get player input

        Returns:
            Combined result dict
        """
        all_effects_applied = []
        choices_required = []

        for effect in ordered_effects:
            effect_type = effect.get("type", "")

            # Handle special actions
            if effect_type == "_deploy_troops_action":
                self._handle_deploy_troops(player_id, get_input_fn)
                all_effects_applied.append("Troops deployed to conflict")

            elif effect_type == "_play_intrigue_action":
                self._handle_play_intrigue(player_id, get_input_fn)
                all_effects_applied.append("Intrigue card played")

            elif effect_type == "_acquire_card_action":
                self._handle_acquire_card(player_id, context, get_input_fn)
                all_effects_applied.append("Card acquired from row")

            else:
                # Regular effect - resolve it
                result = self.effect_resolver.resolve_effects(
                    player_id,
                    [effect],  # Resolve one at a time
                    context
                )

                if result.get("success"):
                    all_effects_applied.extend(result.get("effects_applied", []))
                    if result.get("choices_required"):
                        choices_required.extend(result.get("choices_required", []))
                else:
                    # Effect failed - return error
                    return result

        return {
            "success": True,
            "effects_applied": all_effects_applied,
            "choices_required": choices_required
        }

    def _handle_deploy_troops(self, player_id: str, get_input_fn: Optional[Callable]):
        """
        Prompt player to deploy troops to conflict.

        Args:
            player_id: Player deploying troops
            get_input_fn: Function to get player input
        """
        player = self.action_executor.state.get_player_by_id(player_id)

        print(f"\nDeploy troops to conflict? (You have {player.troops_in_garrison} in garrison)")
        print("Enter number of troops to deploy (0 to skip):")

        if get_input_fn:
            try:
                num_str = get_input_fn("Troops: ").strip()
                num_troops = int(num_str)
            except (ValueError, StopIteration):
                num_troops = 0
        else:
            # No input function - skip
            print("  (Auto: Deploying 0 troops)")
            num_troops = 0

        if num_troops > 0:
            result = self.action_executor.deploy_troops_to_conflict(player_id, num_troops)
            if result.get("success"):
                print(f"  ✓ Deployed {num_troops} troops to conflict")
            else:
                print(f"  ✗ Failed: {result.get('error')}")
        else:
            print("  Skipped troop deployment")

    def _handle_play_intrigue(self, player_id: str, get_input_fn: Optional[Callable]):
        """
        Prompt player to play an intrigue card.

        Args:
            player_id: Player playing intrigue
            get_input_fn: Function to get player input
        """
        player = self.action_executor.state.get_player_by_id(player_id)

        if not player.intrigue_cards:
            print("\n  No intrigue cards to play")
            return

        print(f"\nYou have {len(player.intrigue_cards)} intrigue card(s)")
        print("Play an intrigue card? (Enter card number, or 0 to skip):")

        for i, card in enumerate(player.intrigue_cards, 1):
            card_name = getattr(card, 'name', f'Intrigue {i}')
            print(f"  {i}. {card_name}")

        if get_input_fn:
            try:
                choice = get_input_fn("Choice: ").strip()
                card_idx = int(choice) - 1
            except (ValueError, StopIteration):
                card_idx = -1
        else:
            print("  (Auto: Skipping)")
            card_idx = -1

        if 0 <= card_idx < len(player.intrigue_cards):
            card = player.intrigue_cards[card_idx]
            print(f"  ✓ Playing: {getattr(card, 'name', 'Intrigue card')}")
            # TODO: Implement intrigue card resolution
            # For now, just acknowledge
        else:
            print("  Skipped intrigue play")

    def _handle_acquire_card(
        self,
        player_id: str,
        context: Dict[str, Any],
        get_input_fn: Optional[Callable]
    ):
        """
        Prompt player to acquire a card from imperium row.

        Args:
            player_id: Player acquiring card
            context: Context (must include game/board reference)
            get_input_fn: Function to get player input
        """
        player = self.action_executor.state.get_player_by_id(player_id)

        # Get imperium row from game board
        game = self.action_executor.game
        if not hasattr(game, 'board') or not hasattr(game.board, 'imperium_row'):
            print("\n  No imperium row available")
            return

        imperium_row = game.board.imperium_row

        if not imperium_row:
            print("\n  Imperium row is empty")
            return

        print("\nImperium Row:")
        for i, card in enumerate(imperium_row, 1):
            card_name = getattr(card, 'name', f'Card {i}')
            cost = getattr(card, 'cost', '?')
            print(f"  {i}. {card_name} (Cost: {cost})")

        print(f"\nYour persuasion: {player.temp_persuasion if hasattr(player, 'temp_persuasion') else 0}")
        print("Acquire a card? (Enter card number, or 0 to skip):")

        if get_input_fn:
            try:
                choice = get_input_fn("Choice: ").strip()
                card_idx = int(choice) - 1
            except (ValueError, StopIteration):
                card_idx = -1
        else:
            print("  (Auto: Skipping)")
            card_idx = -1

        if 0 <= card_idx < len(imperium_row):
            card = imperium_row[card_idx]
            print(f"  ✓ Acquiring: {getattr(card, 'name', 'Card')}")
            # TODO: Implement card acquisition logic
            # For now, just acknowledge
        else:
            print("  Skipped acquisition")


# Singleton instance
_interactive_resolver = None


def get_interactive_resolver(action_executor=None, effect_resolver=None):
    """
    Get or create the interactive resolver singleton.

    Args:
        action_executor: ActionExecutor instance
        effect_resolver: EffectResolver instance

    Returns:
        InteractiveEffectResolver instance
    """
    global _interactive_resolver
    if _interactive_resolver is None and action_executor and effect_resolver:
        _interactive_resolver = InteractiveEffectResolver(action_executor, effect_resolver)
    return _interactive_resolver
