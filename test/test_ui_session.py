"""Smoke tests for the UI GameSession + serializer.

Verifies the web-UI scaffolding can:
  - construct a fresh game without touching the engine
  - produce a JSON-safe state snapshot
  - hide opponents' hands but show the human's own hand
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from ui.game_session import GameSession
from ui.serializer import serialize_state


def test_session_constructs_with_three_players():
    session = GameSession.new(player_count=3, human_name="Alice")
    assert len(session.game.players) == 3
    assert session.human_player.name == "Alice"
    assert session.human_player.is_human is True
    # Bots created for non-human players
    assert len(session.bots) == 2
    assert session.human_player_id not in session.bots


def test_session_constructs_with_four_players():
    session = GameSession.new(player_count=4)
    assert len(session.game.players) == 4
    assert len(session.bots) == 3


def test_session_rejects_invalid_player_count():
    with pytest.raises(ValueError):
        GameSession.new(player_count=2)
    with pytest.raises(ValueError):
        GameSession.new(player_count=5)


def test_game_starts_in_player_turns_phase():
    session = GameSession.new(player_count=3)
    assert session.game.current_phase.value == "player_turns"
    assert session.game.current_round == 1
    # First conflict drawn
    assert session.game.board.current_conflict is not None


def test_is_human_turn_returns_bool():
    """First player is determined by Desert Mouse objective — may or may not
    be the human. Just verify the property returns a clean bool."""
    session = GameSession.new(player_count=3)
    assert isinstance(session.is_human_turn, bool)


def test_snapshot_is_json_serializable():
    """The whole state envelope must be JSON-encodable for the HTTP layer."""
    session = GameSession.new(player_count=3)
    snap = session.snapshot()
    # If this raises, we have a non-JSON-safe type somewhere
    encoded = json.dumps(snap)
    assert len(encoded) > 100  # non-empty


def test_snapshot_includes_expected_top_level_keys():
    session = GameSession.new(player_count=3)
    snap = session.snapshot()
    assert "state" in snap
    assert "pending_choice" in snap
    assert "is_human_turn" in snap
    assert "events" in snap


def test_state_includes_board_and_players():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    assert "board" in state
    assert "players" in state
    assert len(state["players"]) == 3
    assert state["round"] == 1
    assert state["phase"] == "player_turns"


def test_human_player_view_includes_hand():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    human = next(p for p in state["players"] if p["player_id"] == session.human_player_id)
    # Human should see their own hand
    assert "hand" in human
    assert "intrigue_cards" in human


def test_opponent_view_hides_hand():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    opponents = [p for p in state["players"] if p["player_id"] != session.human_player_id]
    for opp in opponents:
        # Opponents must NOT expose hand/intrigue contents
        assert "hand" not in opp, "Opponent hand should be hidden"
        assert "intrigue_cards" not in opp, "Opponent intrigue should be hidden"
        # But counts should be visible
        assert "hand_size" in opp
        assert "intrigue_count" in opp


def test_board_serializes_imperium_row():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    board = state["board"]
    assert "imperium_row" in board
    assert isinstance(board["imperium_row"], list)
    # Real game has 5 cards in row
    assert len(board["imperium_row"]) == 5
    # Each card has expected fields
    card = board["imperium_row"][0]
    for key in ("id", "name", "cost", "factions", "agent_icons"):
        assert key in card


def test_board_serializes_spaces():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    spaces = state["board"]["spaces"]
    assert len(spaces) > 0
    space = spaces[0]
    for key in ("id", "name", "agent_icon", "occupied_by"):
        assert key in space


def test_event_log_drains_on_snapshot():
    session = GameSession.new(player_count=3)
    session.log("test_event", message="hello")
    snap1 = session.snapshot()
    assert len(snap1["events"]) == 1
    assert snap1["events"][0]["type"] == "test_event"

    # Second snapshot should be empty (already drained)
    snap2 = session.snapshot()
    assert snap2["events"] == []


def test_pending_choice_initially_none():
    session = GameSession.new(player_count=3)
    assert session.pending_choice is None
    snap = session.snapshot()
    assert snap["pending_choice"] is None


def test_player_resources_present_in_view():
    session = GameSession.new(player_count=3)
    state = serialize_state(session.game, viewer_player_id=session.human_player_id)
    human = state["players"][0]
    for key in ("solari", "spice", "water", "victory_points",
                "troops_in_garrison", "agents_available",
                "influence", "alliances", "contracts_active"):
        assert key in human, f"Missing key: {key}"
    # Influence has four factions
    for faction in ("fremen", "bene_gesserit", "spacing_guild", "emperor"):
        assert faction in human["influence"]
