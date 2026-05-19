"""
Contract Manager - Manages contract acquisition and completion.

Contracts have 3 types:
1. Location-based: Visit a specific board space
2. Harvest-based: Accumulate X spice
3. Immediate: Auto-complete on acquisition
"""

from typing import Dict, Any, Optional
from ..models.game import Game
from ..models.player import Player
from ..models.card import ContractCard
from .game_state import GameState


class ContractManager:
    """
    Manages contract lifecycle:
    - Acquisition (take from row)
    - Progress tracking
    - Completion validation
    - Reward distribution
    """

    def __init__(self, game: Game):
        self.game = game
        self.state = GameState(game)

    # ==================== CONTRACT ACQUISITION ====================

    def acquire_contract(self, player_id: str, contract: ContractCard) -> Dict[str, Any]:
        """
        Player acquires a contract from the contract row.

        Process:
        1. Remove from contract row
        2. Add to player's active contracts
        3. If immediate type, complete instantly
        4. Refill contract row

        Args:
            player_id: Player acquiring the contract
            contract: ContractCard to acquire

        Returns:
            Dict with acquisition results
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"success": False, "error": "Player not found"}

        # Validate contract is available
        if contract not in self.game.board.contract_row:
            return {"success": False, "error": "Contract not in row"}

        # Remove from row
        self.game.board.contract_row.remove(contract)

        # Check if immediate completion
        if contract.completion_type == "immediate":
            # Immediate contracts complete on acquisition
            player.contracts_completed.append(contract)

            # Apply rewards
            reward_results = self._apply_contract_rewards(player, contract)

            # Refill row
            self.game.board.refill_contract_row()

            return {
                "success": True,
                "action_type": "acquire_contract",
                "contract": contract.name,
                "completion_type": "immediate",
                "completed": True,
                "rewards": reward_results
            }
        else:
            # Add to active contracts (to be completed later)
            player.contracts_active.append(contract)

            # Refill row
            self.game.board.refill_contract_row()

            return {
                "success": True,
                "action_type": "acquire_contract",
                "contract": contract.name,
                "completion_type": contract.completion_type,
                "completed": False,
                "target": contract.completion_target,
                "required_spice": contract.required_spice
            }

    # ==================== CONTRACT COMPLETION ====================

    def check_location_contracts(
        self,
        player_id: str,
        location_id: str
    ) -> Dict[str, Any]:
        """
        Check if player completes any location-based contracts by visiting a location.

        Called when player places agent at a location.

        Args:
            player_id: Player who placed agent
            location_id: Location ID they visited

        Returns:
            Dict with completed contracts
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"completed_contracts": []}

        completed = []

        # Check each active contract
        for contract in player.contracts_active[:]:  # Copy list to modify during iteration
            if contract.completion_type == "location":
                if contract.completion_target == location_id:
                    # Contract completed!
                    player.contracts_active.remove(contract)
                    player.contracts_completed.append(contract)

                    # Apply rewards
                    reward_results = self._apply_contract_rewards(player, contract)

                    completed.append({
                        "contract": contract.name,
                        "type": "location",
                        "rewards": reward_results
                    })

        return {
            "completed_contracts": completed,
            "total_completed": len(completed)
        }

    def check_harvest_contracts(self, player_id: str) -> Dict[str, Any]:
        """
        Check if player completes any harvest-based contracts.

        Harvest contracts require accumulating X spice total (lifetime).

        Called during game state updates or at specific checkpoints.

        Args:
            player_id: Player to check

        Returns:
            Dict with completed contracts
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"completed_contracts": []}

        completed = []

        # Track total spice harvested (would need a counter on player)
        # For now, simplified: check current spice
        if not hasattr(player, 'total_spice_harvested'):
            player.total_spice_harvested = 0

        for contract in player.contracts_active[:]:
            if contract.completion_type == "harvest":
                if player.total_spice_harvested >= contract.required_spice:
                    # Contract completed!
                    player.contracts_active.remove(contract)
                    player.contracts_completed.append(contract)

                    # Apply rewards
                    reward_results = self._apply_contract_rewards(player, contract)

                    completed.append({
                        "contract": contract.name,
                        "type": "harvest",
                        "spice_required": contract.required_spice,
                        "rewards": reward_results
                    })

        return {
            "completed_contracts": completed,
            "total_completed": len(completed)
        }

    def update_spice_harvest(self, player_id: str, spice_amount: int):
        """
        Update player's total spice harvested counter.

        Call this whenever player gains spice from harvest actions.

        Args:
            player_id: Player who harvested spice
            spice_amount: Amount harvested
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return

        if not hasattr(player, 'total_spice_harvested'):
            player.total_spice_harvested = 0

        player.total_spice_harvested += spice_amount

        # Auto-check for completed harvest contracts
        self.check_harvest_contracts(player_id)

    # ==================== REWARD DISTRIBUTION ====================

    def _apply_contract_rewards(
        self,
        player: Player,
        contract: ContractCard
    ) -> Dict[str, Any]:
        """
        Apply rewards from a completed contract.

        Contract rewards can include:
        - Resources (solari, spice, water)
        - Victory points
        - Troops
        - Cards (draw, intrigue)
        - Influence

        Args:
            player: Player receiving rewards
            contract: Completed contract

        Returns:
            Dict with applied rewards
        """
        results = {"rewards_applied": []}

        for reward_type, value in contract.rewards.items():
            if reward_type == "solari":
                player.solari += value
            elif reward_type == "spice":
                player.spice += value
            elif reward_type == "water":
                player.water += value
            elif reward_type == "victory_points":
                player.victory_points += value
            elif reward_type == "troops":
                troops_to_add = min(value, player.troops_in_reserve)
                player.troops_in_reserve -= troops_to_add
                player.troops_in_garrison += troops_to_add
            elif reward_type == "draw":
                for _ in range(value):
                    card = player.deck.draw(player.discard_pile)
                    if card:
                        player.hand.add_card(card)
            elif reward_type == "intrigue":
                for _ in range(value):
                    intrigue = self.game.board.intrigue_deck.pop(0) if self.game.board.intrigue_deck else None
                    if intrigue:
                        player.intrigue_cards.append(intrigue)

            results["rewards_applied"].append({
                "reward": reward_type,
                "amount": value
            })

        return results

    # ==================== CONTRACT QUERIES ====================

    def get_available_contracts(self) -> list:
        """Get contracts available in the contract row."""
        return self.game.board.contract_row

    def get_player_active_contracts(self, player_id: str) -> list:
        """Get player's active (incomplete) contracts."""
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []
        return player.contracts_active

    def get_player_completed_contracts(self, player_id: str) -> list:
        """Get player's completed contracts."""
        player = self.state.get_player_by_id(player_id)
        if not player:
            return []
        return player.contracts_completed

    def get_contract_progress(self, player_id: str, contract: ContractCard) -> Dict[str, Any]:
        """
        Get progress on a specific contract.

        Returns:
            Dict with progress information
        """
        player = self.state.get_player_by_id(player_id)
        if not player:
            return {"error": "Player not found"}

        if contract.completion_type == "immediate":
            return {
                "type": "immediate",
                "completed": contract in player.contracts_completed
            }

        elif contract.completion_type == "location":
            return {
                "type": "location",
                "target": contract.completion_target,
                "completed": contract in player.contracts_completed
            }

        elif contract.completion_type == "harvest":
            total_harvested = getattr(player, 'total_spice_harvested', 0)
            return {
                "type": "harvest",
                "required": contract.required_spice,
                "current": total_harvested,
                "progress": f"{total_harvested}/{contract.required_spice}",
                "completed": total_harvested >= contract.required_spice
            }

        return {"error": "Unknown contract type"}
