"""
GameState - Query the current state of the game.
This class provides read-only access to game state information.
No logic here - just queries about "what IS the current state?"
"""

from typing import Optional, List
from ...models.game import Game
from ...models.player import Player
from ...models.board import Board
from ...models.boardspace import BoardSpace, ObservationPost
from ...models.card import ConflictCard


class GameState:
    """
    Provides read-only queries about the current game state.

    This is a wrapper around the Game object that provides
    convenient methods to query state without modifying it.
    """

    def __init__(self, game: Game):
        self.game = game

    # ==================== BOARD QUERIES ====================

    def get_board(self) -> Board:
        """Get the game board"""
        return self.game.board

    def is_location_occupied(self, location_id: str) -> bool:
        """Check if a board location is occupied by an agent"""
        space = self.get_space_by_id(location_id)
        if space:
            return space.occupied_by is not None
        return False

    def get_occupied_locations(self) -> List[str]:
        """Get list of all occupied location IDs"""
        occupied = []
        for space in self.game.board.spaces:
            if space.occupied_by is not None:
                occupied.append(space.id)
        return occupied

    def get_space_by_id(self, space_id: str) -> Optional[BoardSpace]:
        """Get a board space by its ID"""
        for space in self.game.board.spaces:
            if space.id == space_id:
                return space
        return None

    def get_spaces_by_icon(self, agent_icon: str) -> List[BoardSpace]:
        """Get all board spaces that match an agent icon"""
        matching = []
        for space in self.game.board.spaces:
            if space.agent_icon == agent_icon:
                matching.append(space)
        return matching

    def get_observation_post_by_id(self, post_id: str) -> Optional[ObservationPost]:
        """Get an observation post by its ID"""
        for post in self.game.board.observation_posts:
            if post.id == post_id:
                return post
        return None

    def get_current_conflict(self) -> Optional[ConflictCard]:
        """Get the currently active conflict card"""
        return self.game.board.current_conflict

    def is_shield_active(self) -> bool:
        """Check if the shield is active (blocks sandworms at protected locations)"""
        return self.game.board.shield_active

    # ==================== PLAYER QUERIES ====================

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get a player by their unique ID"""
        return self.game.get_player(player_id)

    def get_current_player(self) -> Player:
        """Get the player whose turn it is"""
        return self.game.current_player

    def get_first_player(self) -> Player:
        """Get the first player (has the first player marker)"""
        return self.game.first_player

    def has_player_revealed(self, player_id: str) -> bool:
        """Check if a player has taken their reveal turn this round"""
        player = self.get_player_by_id(player_id)
        if player:
            return player.has_revealed_this_round
        return False

    def get_players_who_have_revealed(self) -> List[Player]:
        """Get all players who have revealed this round"""
        return [p for p in self.game.players if p.has_revealed_this_round]

    def get_players_who_havent_revealed(self) -> List[Player]:
        """Get all players who haven't revealed yet this round"""
        return [p for p in self.game.players if not p.has_revealed_this_round]

    def all_players_have_revealed(self) -> bool:
        """Check if all players have taken their reveal turn"""
        return all(p.has_revealed_this_round for p in self.game.players)

    # ==================== PLAYER RESOURCE QUERIES ====================

    def get_player_solari(self, player_id: str) -> int:
        """Get player's Solari count"""
        player = self.get_player_by_id(player_id)
        return player.solari if player else 0

    def get_player_spice(self, player_id: str) -> int:
        """Get player's Spice count"""
        player = self.get_player_by_id(player_id)
        return player.spice if player else 0

    def get_player_water(self, player_id: str) -> int:
        """Get player's Water count"""
        player = self.get_player_by_id(player_id)
        return player.water if player else 0

    def get_player_victory_points(self, player_id: str) -> int:
        """Get player's Victory Points"""
        player = self.get_player_by_id(player_id)
        return player.victory_points if player else 0

    # ==================== PLAYER INFLUENCE QUERIES ====================

    def get_player_influence(self, player_id: str, faction: str) -> int:
        """
        Get player's influence for a specific faction.

        Args:
            player_id: Player ID
            faction: 'fremen', 'emperor', 'spacing_guild', or 'bene_gesserit'

        Returns:
            Influence value (0-4+)
        """
        player = self.get_player_by_id(player_id)
        if not player:
            return 0

        if faction == "fremen":
            return player.fremen_influence
        elif faction == "emperor":
            return player.emperor_influence
        elif faction == "spacing_guild":
            return player.spacing_guild_influence
        elif faction == "bene_gesserit":
            return player.bene_gesserit_influence
        else:
            return 0

    def has_alliance(self, player_id: str, faction: str) -> bool:
        """Check if player has alliance with a faction"""
        player = self.get_player_by_id(player_id)
        if not player:
            return False

        if faction == "fremen":
            return player.fremen_alliance
        elif faction == "emperor":
            return player.emperor_alliance
        elif faction == "spacing_guild":
            return player.spacing_guild_alliance
        elif faction == "bene_gesserit":
            return player.bene_gesserit_alliance
        else:
            return False

    def get_alliance_holder(self, faction: str) -> Optional[Player]:
        """Get the player who holds the alliance for a faction (or None)"""
        for player in self.game.players:
            if self.has_alliance(player.player_id, faction):
                return player
        return None

    # ==================== PLAYER AGENT/SPY QUERIES ====================

    def get_player_available_agents(self, player_id: str) -> int:
        """Get number of agents player has available to place"""
        player = self.get_player_by_id(player_id)
        return player.agents_available if player else 0

    def get_player_placed_agents(self, player_id: str) -> List[str]:
        """Get list of location IDs where player has placed agents"""
        player = self.get_player_by_id(player_id)
        return player.agents_placed if player else []

    def get_player_available_spies(self, player_id: str) -> int:
        """Get number of spies player has available to place"""
        player = self.get_player_by_id(player_id)
        return player.spies_available if player else 0

    def get_player_placed_spies(self, player_id: str) -> List[str]:
        """Get list of observation post IDs where player has placed spies"""
        player = self.get_player_by_id(player_id)
        return player.spies_placed if player else []

    def has_spy_at_post(self, player_id: str, post_id: str) -> bool:
        """Check if player has a spy at a specific observation post"""
        placed_spies = self.get_player_placed_spies(player_id)
        return post_id in placed_spies

    def get_spy_accessible_locations(self, player_id: str) -> List[BoardSpace]:
        """
        Get all board locations accessible via player's spy network.
        Returns locations connected to observation posts where player has spies.
        """
        player = self.get_player_by_id(player_id)
        if not player:
            return []

        accessible = []
        for post_id in player.spies_placed:
            post = self.get_observation_post_by_id(str(post_id))
            if post:
                for loc_ref in post.connected_locations:
                    # connected_locations stores space NAMES, not IDs
                    space = next(
                        (s for s in self.game.board.spaces
                         if s.name == loc_ref or str(s.id) == str(loc_ref)),
                        None,
                    )
                    if space and space not in accessible:
                        accessible.append(space)

        return accessible

    # ==================== PLAYER TROOP/COMBAT QUERIES ====================

    def get_player_troops_in_reserve(self, player_id: str) -> int:
        """Get number of troops in player's reserve"""
        player = self.get_player_by_id(player_id)
        return player.troops_reserve if player else 0

    def get_player_troops_in_garrison(self, player_id: str) -> int:
        """Get number of troops in player's garrison"""
        player = self.get_player_by_id(player_id)
        return player.troops_garrison if player else 0

    def get_player_troops_in_conflict(self, player_id: str) -> int:
        """Get number of troops player has deployed in conflict"""
        player = self.get_player_by_id(player_id)
        return player.troops_conflict if player else 0

    def get_player_sandworms_in_conflict(self, player_id: str) -> int:
        """Get number of sandworms player has in conflict"""
        player = self.get_player_by_id(player_id)
        return player.sandworms_in_conflict if player else 0

    def has_maker_hooks(self, player_id: str) -> bool:
        """Check if player has Maker Hooks token (required for sandworms)"""
        player = self.get_player_by_id(player_id)
        return player.has_maker_hooks if player else False

    def get_player_combat_strength(self, player_id: str) -> int:
        """
        Calculate player's current combat strength.
        Returns 0 if player has no troops in conflict.
        """
        player = self.get_player_by_id(player_id)
        if player:
            return player.combat_strength
        return 0

    # ==================== GAME PHASE QUERIES ====================

    def get_current_phase(self) -> str:
        """Get the current game phase"""
        return self.game.current_phase.value

    def get_current_round(self) -> int:
        """Get the current round number"""
        return self.game.current_round

    def is_game_over(self) -> bool:
        """Check if game is over (someone reached 10 VP or conflict deck empty)"""
        # Check VP condition
        for player in self.game.players:
            if player.victory_points >= 10:
                return True

        # Check conflict deck empty
        if len(self.game.board.conflict_deck) == 0:
            return True

        return False

    def get_winner(self) -> Optional[Player]:
        """
        Get the winner if game is over.
        Returns None if game not over or tie.
        """
        if not self.is_game_over():
            return None

        # Find player(s) with most VP
        max_vp = max(p.victory_points for p in self.game.players)
        winners = [p for p in self.game.players if p.victory_points == max_vp]

        if len(winners) == 1:
            return winners[0]

        # Tie-breaker: most spice
        max_spice = max(w.spice for w in winners)
        winners = [w for w in winners if w.spice == max_spice]

        if len(winners) == 1:
            return winners[0]

        # Still tied - could continue with other tie-breakers
        return None  # Or return first winner for simplicity

    # ==================== CONTROLLED LOCATIONS ====================

    def get_controlled_locations(self, player_id: str) -> List[str]:
        """Get list of critical location IDs controlled by player"""
        player = self.get_player_by_id(player_id)
        return player.controlled_locations if player else []

    def who_controls_location(self, location_id: str) -> Optional[str]:
        """Get player_id of who controls a critical location (or None)"""
        space = self.get_space_by_id(location_id)
        if space and space.is_critical_location:
            return space.controlled_by
        return None
