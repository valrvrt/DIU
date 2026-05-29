"""Game → JSON-safe dict serializer.

Converts the dataclass-based engine state into a plain dict so the frontend
can render it. The engine code is not modified; this module only reads.

The serializer is the single source of truth for the API's state envelope.
Keep field names stable — the frontend depends on them.
"""

from typing import Any, Dict, List, Optional

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.models.card import (
    ImperiumCard, IntrigueCard, ContractCard, ConflictCard,
    LeaderCard, ObjectiveCard,
)


# ───────────────────────── cards ──────────────────────────

def _imperium_card(card: ImperiumCard) -> Dict[str, Any]:
    return {
        "id": card.id,
        "name": card.name,
        "type": "imperium",
        "cost": card.cost,
        "factions": list(card.factions),
        "agent_icons": list(card.agent_icons),
        "agent_effects": card.agent_effects or [],
        "reveal_effects": card.reveal_effects or [],
        "on_acquire_effects": card.on_acquire_effects or [],
    }


def _intrigue_card(card: IntrigueCard) -> Dict[str, Any]:
    return {
        "id": card.id,
        "name": card.name,
        "type": "intrigue",
        "phases": [p.value for p in (card.phases or [])],
        "effects": card.effects or [],
    }


def _contract_card(card: ContractCard) -> Dict[str, Any]:
    return {
        "id": card.id,
        "name": card.name,
        "type": "contract",
        "completion_type": card.completion_type,
        "completion_target": card.completion_target,
        "required_spice": card.required_spice,
        "rewards": card.rewards or [],
    }


def _conflict_card(card: ConflictCard) -> Dict[str, Any]:
    return {
        "id": card.id,
        "name": card.name,
        "type": "conflict",
        "level": card.level,
        "tag": card.tag,
        "rewards": card.rewards or {},
        "location": card.location,
        "battle_icon": card.battle_icon,
        "wall": card.wall,
    }


def _leader_card(card) -> Optional[Dict[str, Any]]:
    """Serialize a leader. Accepts both LeaderCard (legacy) and Leader (engine).

    The engine uses the concrete `Leader` class hierarchy (PaulAtreides, etc.)
    which has `leader_id` and `name`. The LeaderCard dataclass has `id` and
    `name`. Handle both shapes.
    """
    if card is None:
        return None
    return {
        "id": getattr(card, "id", None) or str(getattr(card, "leader_id", "")),
        "name": getattr(card, "name", "Unknown"),
        "type": "leader",
        "signet": (
            getattr(card, "signet_progression", None)
            or getattr(card, "signet_ability", None)
            or getattr(card, "ring", None)
            or []
        ),
        "passive": getattr(card, "passive_ability", None),
        "training_track_position": getattr(card, "training_track_position", 0),
    }


def _objective_card(card) -> Dict[str, Any]:
    if card is None:
        return None
    return {
        "id": getattr(card, "id", ""),
        "name": getattr(card, "name", "Unknown"),
        "tag": getattr(card, "tag", ""),
        "description": getattr(card, "description", getattr(card, "text", getattr(card, "tag", ""))),
    }


# ───────────────────────── board ──────────────────────────

def _board_space(space: BoardSpace) -> Dict[str, Any]:
    return {
        "id": space.id,
        "name": space.name,
        "agent_icon": space.agent_icon,
        "faction": space.faction,
        "occupied_by": space.occupied_by,
        "infiltrated_by": space.infiltrated_by,
        "cost": space.cost or [],
        "reward": space.reward or [],
        "check": space.check or [],
        "is_combat_space": space.is_combat_space,
        "is_maker_space": space.is_maker_space,
        "spice_bonus": space.spice_bonus,
        "is_critical_location": space.is_critical_location,
        "controlled_by": space.controlled_by,
    }


def _board(board: Board) -> Dict[str, Any]:
    return {
        "spaces": [_board_space(s) for s in board.spaces],
        "imperium_row": [_imperium_card(c) for c in board.imperium_row],
        "imperium_deck_size": len(board.imperium_deck),
        "imperium_discard_size": len(board.imperium_discard),
        "reserve_prepare_the_way": {
            "top": _imperium_card(board.reserve_prepare_the_way[0])
                if board.reserve_prepare_the_way else None,
            "remaining": len(board.reserve_prepare_the_way),
        },
        "reserve_spice_must_flow": {
            "top": _imperium_card(board.reserve_spice_must_flow[0])
                if board.reserve_spice_must_flow else None,
            "remaining": len(board.reserve_spice_must_flow),
        },
        "contract_row": [_contract_card(c) for c in board.contract_row],
        "contract_deck_size": len(board.contract_deck),
        "intrigue_deck_size": len(board.intrigue_deck),
        "current_conflict": (
            _conflict_card(board.current_conflict) if board.current_conflict else None
        ),
        "conflict_deck_size": len(board.conflict_deck),
        "shield_active": board.shield_active,
        "observation_posts": [
            {
                "id": str(post.id),
                "name": post.name,
                "connected_locations": post.connected_locations,
            }
            for post in board.observation_posts
        ],
    }


# ───────────────────────── players ────────────────────────

def _player_public(player: Player) -> Dict[str, Any]:
    """Public view: everyone can see this. Used for opponents."""
    return {
        "player_id": player.player_id,
        "name": player.name,
        "color": player.color,
        "is_human": player.is_human,
        "leader": _leader_card(player.leader),

        # Resources
        "solari": player.solari,
        "spice": player.spice,
        "water": player.water,
        "victory_points": player.victory_points,

        # Troops
        "troops_in_garrison": player.troops_in_garrison,
        "troops_in_conflict": player.troops_in_conflict,
        "troops_in_reserve": player.troops_in_reserve,
        "sandworms_in_conflict": player.sandworms_in_conflict,

        # Agents / spies
        "agents_available": player.agents_available,
        "total_available_agents": player.total_available_agents,
        "agents_placed": list(player.agents_placed),
        "spies_available": player.spies_available,
        "total_available_spies": player.total_available_spies,
        "spies_placed": [str(s) for s in player.spies_placed],

        # Influence
        "influence": {
            "fremen": player.fremen_influence,
            "bene_gesserit": player.bene_gesserit_influence,
            "spacing_guild": player.spacing_guild_influence,
            "emperor": player.emperor_influence,
        },
        "alliances": {
            "fremen": player.fremen_alliance,
            "bene_gesserit": player.bene_gesserit_alliance,
            "spacing_guild": player.spacing_guild_alliance,
            "emperor": player.emperor_alliance,
        },

        # Card counts (NOT the cards themselves — hidden from opponents)
        "hand_size": player.hand.size,
        "deck_size": player.deck.size,
        "discard_size": player.discard_pile.size,
        "intrigue_count": len(player.intrigue_cards),

        # Contracts
        "contracts_active": [_contract_card(c) for c in player.contracts_active],
        "contracts_completed_count": len(player.contracts_completed),

        # Turn state
        "has_revealed_this_round": player.has_revealed_this_round,
        "combat_strength": (
            player.troops_in_conflict * 2
            + player.sandworms_in_conflict * 3
            + getattr(player, "temp_swords", 0)
        ) if (player.troops_in_conflict > 0 or player.sandworms_in_conflict > 0) else 0,
        "temp_swords": getattr(player, "temp_swords", 0),
    }


def _player_private(player: Player) -> Dict[str, Any]:
    """Private view: the player's own perspective. Includes hand + intrigue."""
    public = _player_public(player)
    public["hand"] = [_imperium_card(c) for c in player.hand.cards]
    public["intrigue_cards"] = [_intrigue_card(c) for c in player.intrigue_cards]
    public["discard"] = [_imperium_card(c) for c in player.discard_pile.cards]
    public["temp_persuasion"] = getattr(player, "temp_persuasion", 0)
    # Objectives are stored in player.objectives (list); fall back to the
    # legacy single objective_card attribute if present.
    obj = getattr(player, "objective_card", None)
    if obj is None:
        objs = getattr(player, "objectives", None) or []
        obj = objs[0] if objs else None
    public["objective"] = _objective_card(obj) if obj is not None else None
    return public


# ───────────────────────── game over ──────────────────────

def _game_over_data(game: Game, players_serialized: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build final score / ranking data shown on the game-over overlay."""
    # Official tiebreaker order: VP → Spice → Solari → Water → Garrison Troops.
    def _rank_key(p: Dict[str, Any]):
        return (
            p.get("victory_points", 0),
            p.get("spice", 0),
            p.get("solari", 0),
            p.get("water", 0),
            p.get("troops_in_garrison", 0),
        )

    ranked = sorted(players_serialized, key=_rank_key, reverse=True)
    top_key = _rank_key(ranked[0]) if ranked else ()
    # A true tie requires every tiebreaker to match, not just VP.
    winners = [p["name"] for p in ranked if _rank_key(p) == top_key]
    return {
        "ranked_players": [
            {
                "player_id": p["player_id"],
                "name": p["name"],
                "vp": p.get("victory_points", 0),
                "solari": p.get("solari", 0),
                "spice": p.get("spice", 0),
                "water": p.get("water", 0),
                "garrison": p.get("troops_in_garrison", 0),
                "is_human": p.get("is_human", False),
            }
            for p in ranked
        ],
        "winner_names": winners,
        "is_human_winner": any(p.get("is_human") for p in ranked
                                if _rank_key(p) == top_key),
        "total_rounds": game.current_round,
    }


# ───────────────────────── top level ──────────────────────

def serialize_state(game: Game, viewer_player_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Serialize the full game state from a given player's perspective.

    Args:
        game: the engine Game object
        viewer_player_id: which player's hand/intrigue to reveal. Others get
            public view only. If None, all players are public (spectator).

    Returns:
        A JSON-safe dict ready to send to the frontend.
    """
    players_serialized: List[Dict[str, Any]] = []

    for player in game.players:
        if viewer_player_id is not None and player.player_id == viewer_player_id:
            players_serialized.append(_player_private(player))
        else:
            players_serialized.append(_player_public(player))

    return {
        "phase": game.current_phase.value if isinstance(game.current_phase, GamePhase)
                  else str(game.current_phase),
        "round": game.current_round,
        "player_count": game.player_count,
        "current_player_index": game.current_player_index,
        "first_player_index": game.first_player_index,
        "current_player_id": (
            game.current_player.player_id
            if game.players else None
        ),
        "viewer_player_id": viewer_player_id,
        "players": players_serialized,
        "board": _board(game.board) if game.board else None,
        "game_over": game.current_phase == GamePhase.GAME_OVER,
        "game_over_data": _game_over_data(game, players_serialized)
            if game.current_phase == GamePhase.GAME_OVER else None,
    }
