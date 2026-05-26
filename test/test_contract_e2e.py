"""
End-to-end tests for the Contract acquisition & completion lifecycle.

Covers all four contract types:
  - immediate      → completes on acquisition
  - location       → completes when agent placed at target location
  - harvest        → completes when total_spice_harvested reaches threshold
  - acquire_card   → completes when player acquires the named card
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from src.models.game import Game, GamePhase
from src.models.player import Player
from src.models.card import (
    LeaderCard, ImperiumCard, ContractCard, CardType
)
from src.models.deck import Deck
from src.models.board import Board
from src.models.boardspace import BoardSpace
from src.engine.managers.contract_manager import ContractManager
from src.engine.managers.deck_manager import DeckManager
from src.engine.managers.phase_manager import PhaseManager
from src.engine.actions.action_executor import ActionExecutor, PlaceAgentAction, AcquireCardAction, RevealAction
from src.engine.actions.action_generator import ActionGenerator


# ───────────────────────── helpers ──────────────────────────

def _make_leader(name="Test Leader"):
    return LeaderCard(id="ldr", name=name, type="Leader", card_type=CardType.LEADER)


def _make_imperium_card(card_id="c1", name="Test Card", cost=3, persuasion=2):
    return ImperiumCard(
        id=card_id,
        name=name,
        type="Imperium",
        card_type=CardType.IMPERIUM,
        cost=cost,
        reveal_effects=[{"type": "resource", "resource": "persuasion", "amount": persuasion}],
    )


def _make_contract(
    cid, completion_type, target=None, required_spice=0,
    rewards=None
):
    if rewards is None:
        rewards = [{"type": "resource", "resource": "solari", "amount": 3}]
    return ContractCard(
        id=str(cid),
        name=f"Contract #{cid}",
        card_type=CardType.CONTRACT,
        type="Contract",
        completion_type=completion_type,
        completion_target=target,
        required_spice=required_spice,
        rewards=rewards,
    )


def setup_game(extra_contracts=None):
    """
    Build a minimal two-player game with a contract row.
    Returns (game, player1, player2, contract_manager).
    """
    p1 = Player(
        player_id="p1", name="Alice",
        leader=_make_leader("Alice"),
        color="blue",
        deck=Deck(cards=[_make_imperium_card(f"d{i}", f"Card {i}") for i in range(10)]),
        hand=Deck(), discard_pile=Deck(),
        solari=10, water=2, spice=0,
    )
    p2 = Player(
        player_id="p2", name="Bob",
        leader=_make_leader("Bob"),
        color="red",
        deck=Deck(cards=[_make_imperium_card(f"e{i}", f"Card {i}") for i in range(10)]),
        hand=Deck(), discard_pile=Deck(),
        solari=5, water=1, spice=0,
    )

    board = Board()
    board.spaces = [
        BoardSpace(id="Arrakeen", name="Arrakeen", agent_icon="city",
                   effects=[{"type": "resource", "resource": "solari", "amount": 1}]),
        BoardSpace(id="Spice_Refinery", name="Spice Refinery", agent_icon="spice",
                   effects=[{"type": "resource", "resource": "spice", "amount": 2}]),
    ]
    board.imperium_row = [_make_imperium_card(f"row{i}", f"Row Card {i}", cost=2+i) for i in range(5)]
    board.imperium_deck = [_make_imperium_card(f"dk{i}", f"Deck {i}") for i in range(10)]
    board.intrigue_deck = []
    board.reserve_prepare_the_way = []
    board.reserve_spice_must_flow = []

    # Build the contract deck: 2 fixed + extras
    immediate_c = _make_contract(90, "immediate", rewards=[{"type": "resource", "resource": "solari", "amount": 2}])
    location_c  = _make_contract(91, "location", target="Arrakeen",
                                  rewards=[{"type": "resource", "resource": "water", "amount": 1}])
    harvest_c   = _make_contract(92, "harvest", required_spice=5,
                                  rewards=[{"type": "resource", "resource": "spice", "amount": 3}])
    acquire_c   = _make_contract(93, "acquire_card", target="Row Card 3",
                                  rewards=[{"type": "victory_point", "amount": 1}])
    extra_immediate = _make_contract(94, "immediate",
                                      rewards=[{"type": "resource", "resource": "solari", "amount": 1}])

    contracts = [immediate_c, location_c, harvest_c, acquire_c, extra_immediate]
    if extra_contracts:
        contracts.extend(extra_contracts)

    board.contract_deck = contracts
    board.contract_row = []
    board.refill_contract_row()   # fills 2 from deck

    game = Game(
        players=[p1, p2],
        board=board,
        current_player_index=0,
        current_phase=GamePhase.PLAYER_TURNS,
    )

    contract_manager = ContractManager(game)
    deck_manager = DeckManager(game)
    phase_manager = PhaseManager(game, deck_manager=deck_manager)

    return game, p1, p2, contract_manager, deck_manager, phase_manager


# ───────────────── contract row initialisation ────────────────

def test_contract_row_initialises_with_two_contracts():
    game, p1, *_ = setup_game()
    assert len(game.board.contract_row) == 2, "Contract row should start with 2 contracts"


def test_contract_row_refills_after_acquisition():
    game, p1, _, cm, *_ = setup_game()
    first = game.board.contract_row[0]
    cm.acquire_contract(p1.player_id, first)
    assert len(game.board.contract_row) == 2, "Row should always have 2 contracts"


# ─────────────── immediate contract ───────────────────────────

def test_immediate_contract_completes_on_acquisition():
    """Immediate contract: moves straight to completed and rewards are applied."""
    game, p1, _, cm, *_ = setup_game()

    # Force an immediate contract into position 0
    imm = _make_contract(1, "immediate",
                          rewards=[{"type": "resource", "resource": "solari", "amount": 5}])
    game.board.contract_row = [imm]
    game.board.refill_contract_row()

    solari_before = p1.solari
    result = cm.acquire_contract(p1.player_id, imm)

    assert result["success"] is True
    assert result["completed"] is True
    assert imm not in p1.contracts_active, "Immediate contract should NOT be in active"
    assert imm in p1.contracts_completed, "Immediate contract should be in completed"
    assert p1.solari == solari_before + 5, "Solari reward should be applied immediately"


def test_immediate_contract_not_acquired_twice():
    """Same contract cannot be acquired again once taken from the row."""
    game, p1, _, cm, *_ = setup_game()
    contract = game.board.contract_row[0]
    cm.acquire_contract(p1.player_id, contract)

    result = cm.acquire_contract(p1.player_id, contract)
    assert result["success"] is False, "Second acquisition of same contract must fail"


# ─────────────── location contract ────────────────────────────

def test_location_contract_activates_and_stays_active():
    """Location contract: acquisition moves it to active (not completed)."""
    game, p1, _, cm, *_ = setup_game()

    loc_c = _make_contract(2, "location", target="Arrakeen",
                            rewards=[{"type": "resource", "resource": "water", "amount": 1}])
    game.board.contract_row = [loc_c]
    game.board.refill_contract_row()

    result = cm.acquire_contract(p1.player_id, loc_c)

    assert result["success"] is True
    assert result["completed"] is False
    assert loc_c in p1.contracts_active
    assert loc_c not in p1.contracts_completed


def test_location_contract_completes_on_visiting_target():
    """Location contract: completes (and rewards fire) when agent is placed at the target."""
    game, p1, _, cm, deck_manager, phase_manager = setup_game()

    loc_c = _make_contract(3, "location", target="Arrakeen",
                            rewards=[{"type": "resource", "resource": "water", "amount": 2}])
    game.board.contract_row = [loc_c]
    game.board.refill_contract_row()

    # Place agent at Arrakeen — action_executor calls check_location_contracts
    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    # Accept contract via the executor's own contract_manager (same game state)
    action_exec.contract_manager.acquire_contract(p1.player_id, loc_c)
    assert loc_c in p1.contracts_active
    deck_manager.draw_starting_hand(p1.player_id)
    card = p1.hand.cards[0]
    location = next(s for s in game.board.spaces if s.id == "Arrakeen")

    water_before = p1.water
    result = action_exec.execute_place_agent(
        PlaceAgentAction(
            player_id=p1.player_id,
            card=card,
            location=location,
            placement_type="city",
            troops_to_deploy=0,
        )
    )

    assert result["success"] is True
    assert loc_c not in p1.contracts_active, "Contract should no longer be active"
    assert loc_c in p1.contracts_completed, "Contract should now be completed"
    assert p1.water == water_before + 2, "Water reward should be applied"


def test_location_contract_does_not_complete_on_wrong_location():
    """Location contract is NOT completed when agent visits a different location."""
    game, p1, _, cm, deck_manager, phase_manager = setup_game()

    loc_c = _make_contract(4, "location", target="Arrakeen",
                            rewards=[{"type": "resource", "resource": "water", "amount": 1}])
    game.board.contract_row = [loc_c]
    game.board.refill_contract_row()

    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    action_exec.contract_manager.acquire_contract(p1.player_id, loc_c)
    deck_manager.draw_starting_hand(p1.player_id)
    card = p1.hand.cards[0]
    wrong_location = next(s for s in game.board.spaces if s.id == "Spice_Refinery")

    action_exec.execute_place_agent(
        PlaceAgentAction(
            player_id=p1.player_id,
            card=card,
            location=wrong_location,
            placement_type="spice",
            troops_to_deploy=0,
        )
    )

    assert loc_c in p1.contracts_active, "Contract still active after wrong location"
    assert loc_c not in p1.contracts_completed


# ─────────────── harvest contract ─────────────────────────────

def test_harvest_contract_activates_and_stays_active():
    """Harvest contract goes to active; not immediately completed."""
    game, p1, _, cm, *_ = setup_game()

    harv = _make_contract(5, "harvest", required_spice=5,
                           rewards=[{"type": "resource", "resource": "solari", "amount": 4}])
    game.board.contract_row = [harv]
    game.board.refill_contract_row()

    result = cm.acquire_contract(p1.player_id, harv)
    assert result["success"] is True
    assert result["completed"] is False
    assert harv in p1.contracts_active


def test_harvest_contract_completes_at_threshold():
    """Harvest contract completes once total_spice_harvested >= required_spice."""
    game, p1, _, cm, *_ = setup_game()

    harv = _make_contract(6, "harvest", required_spice=5,
                           rewards=[{"type": "resource", "resource": "solari", "amount": 4}])
    game.board.contract_row = [harv]
    game.board.refill_contract_row()
    cm.acquire_contract(p1.player_id, harv)

    # Harvest just below threshold — should NOT complete
    cm.update_spice_harvest(p1.player_id, 4)
    assert harv in p1.contracts_active

    # Harvest one more unit — should complete
    solari_before = p1.solari
    cm.update_spice_harvest(p1.player_id, 1)

    assert harv not in p1.contracts_active, "Contract should be completed after reaching threshold"
    assert harv in p1.contracts_completed
    assert p1.solari == solari_before + 4, "Solari reward should be applied on completion"


def test_harvest_contract_tracks_cumulative_spice():
    """total_spice_harvested accumulates across multiple calls."""
    game, p1, _, cm, *_ = setup_game()
    harv = _make_contract(7, "harvest", required_spice=10,
                           rewards=[{"type": "resource", "resource": "water", "amount": 1}])
    game.board.contract_row = [harv]
    game.board.refill_contract_row()
    cm.acquire_contract(p1.player_id, harv)

    for _ in range(9):
        cm.update_spice_harvest(p1.player_id, 1)
    assert harv in p1.contracts_active  # not yet

    cm.update_spice_harvest(p1.player_id, 1)  # 10th unit
    assert harv in p1.contracts_completed


# ─────────────── acquire-card contract ────────────────────────

def test_acquire_card_contract_activates():
    game, p1, _, cm, *_ = setup_game()
    aq = _make_contract(8, "acquire_card", target="Row Card 3",
                         rewards=[{"type": "victory_point", "amount": 1}])
    game.board.contract_row = [aq]
    game.board.refill_contract_row()

    result = cm.acquire_contract(p1.player_id, aq)
    assert result["success"] is True
    assert aq in p1.contracts_active


def test_acquire_card_contract_completes_on_buying_target():
    """Acquire-card contract completes when the named card is purchased."""
    game, p1, _, cm, deck_manager, phase_manager = setup_game()

    target_name = "Row Card 3"
    aq = _make_contract(9, "acquire_card", target=target_name,
                         rewards=[{"type": "victory_point", "amount": 1}])
    game.board.contract_row = [aq]
    game.board.refill_contract_row()

    # Put the target card in the imperium row
    target_card = _make_imperium_card("target_card", target_name, cost=2)
    game.board.imperium_row.insert(0, target_card)

    # Set player up for acquisition
    p1.has_revealed_this_round = True
    p1.temp_persuasion = 10

    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    action_exec.contract_manager.acquire_contract(p1.player_id, aq)
    vp_before = p1.victory_points

    result = action_exec.execute_acquire_card(
        AcquireCardAction(player_id=p1.player_id, card=target_card, source="row")
    )

    assert result["success"] is True
    assert aq not in p1.contracts_active
    assert aq in p1.contracts_completed
    assert p1.victory_points == vp_before + 1, "VP reward should fire on contract completion"


def test_acquire_card_contract_does_not_complete_on_wrong_card():
    game, p1, _, cm, deck_manager, phase_manager = setup_game()

    aq = _make_contract(10, "acquire_card", target="Row Card 3",
                         rewards=[{"type": "victory_point", "amount": 1}])
    game.board.contract_row = [aq]
    game.board.refill_contract_row()

    # Buy a DIFFERENT card
    other_card = _make_imperium_card("other", "Row Card 99", cost=2)
    game.board.imperium_row.insert(0, other_card)
    p1.has_revealed_this_round = True
    p1.temp_persuasion = 10

    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    action_exec.contract_manager.acquire_contract(p1.player_id, aq)
    action_exec.execute_acquire_card(
        AcquireCardAction(player_id=p1.player_id, card=other_card, source="row")
    )

    assert aq in p1.contracts_active
    assert aq not in p1.contracts_completed


# ─────────────── rewards edge-cases ───────────────────────────

def test_contract_vp_reward():
    game, p1, _, cm, *_ = setup_game()
    vp_contract = _make_contract(11, "immediate",
                                  rewards=[{"type": "victory_point", "amount": 2}])
    game.board.contract_row = [vp_contract]
    game.board.refill_contract_row()

    vp_before = p1.victory_points
    cm.acquire_contract(p1.player_id, vp_contract)
    assert p1.victory_points == vp_before + 2


def test_contract_influence_reward():
    game, p1, _, cm, *_ = setup_game()
    inf_contract = _make_contract(12, "immediate",
                                   rewards=[{"type": "influence", "target": "fremen", "amount": 2}])
    game.board.contract_row = [inf_contract]
    game.board.refill_contract_row()

    before = p1.fremen_influence
    cm.acquire_contract(p1.player_id, inf_contract)
    assert p1.fremen_influence == before + 2


def test_contract_troop_reward():
    game, p1, _, cm, *_ = setup_game()
    troop_contract = _make_contract(13, "immediate",
                                     rewards=[{"type": "resource", "resource": "troop", "amount": 2}])
    game.board.contract_row = [troop_contract]
    game.board.refill_contract_row()

    garrison_before = p1.troops_in_garrison
    reserve_before = p1.troops_in_reserve
    cm.acquire_contract(p1.player_id, troop_contract)
    assert p1.troops_in_garrison == garrison_before + 2
    assert p1.troops_in_reserve == reserve_before - 2


# ─────────────── contract row edge cases ──────────────────────

def test_contract_row_depletes_gracefully():
    """When deck runs out the row just stays at whatever it can fill."""
    game, p1, _, cm, *_ = setup_game()
    # Drain the deck so refill can only partially fill the row
    game.board.contract_deck = []
    game.board.contract_row = []
    game.board.refill_contract_row()
    # Should be empty (no crash) rather than 2
    assert len(game.board.contract_row) == 0


def test_cannot_acquire_contract_not_in_row():
    game, p1, _, cm, *_ = setup_game()
    orphan = _make_contract(99, "immediate")
    result = cm.acquire_contract(p1.player_id, orphan)
    assert result["success"] is False
    assert "not in row" in result["error"].lower()


# ─────────────── multi-contract scenarios ─────────────────────

def test_two_contracts_can_be_active_simultaneously():
    game, p1, _, cm, *_ = setup_game()

    c1 = _make_contract(20, "location", target="Arrakeen")
    c2 = _make_contract(21, "harvest", required_spice=10)

    game.board.contract_deck = [c1, c2]
    game.board.contract_row = []
    game.board.refill_contract_row()

    cm.acquire_contract(p1.player_id, c1)
    cm.acquire_contract(p1.player_id, c2)

    assert len(p1.contracts_active) == 2


def test_completing_one_contract_does_not_affect_other():
    game, p1, _, cm, deck_manager, phase_manager = setup_game()

    c1 = _make_contract(22, "location", target="Arrakeen",
                         rewards=[{"type": "resource", "resource": "solari", "amount": 1}])
    c2 = _make_contract(23, "location", target="Spice_Refinery",
                         rewards=[{"type": "resource", "resource": "spice", "amount": 1}])

    game.board.contract_deck = [c1, c2]
    game.board.contract_row = []
    game.board.refill_contract_row()

    # Complete only c1 by visiting Arrakeen
    action_exec = ActionExecutor(game, phase_manager, deck_manager)
    action_exec.contract_manager.acquire_contract(p1.player_id, c1)
    action_exec.contract_manager.acquire_contract(p1.player_id, c2)
    deck_manager.draw_starting_hand(p1.player_id)
    card = p1.hand.cards[0]
    arrakeen = next(s for s in game.board.spaces if s.id == "Arrakeen")

    action_exec.execute_place_agent(
        PlaceAgentAction(
            player_id=p1.player_id, card=card, location=arrakeen,
            placement_type="city", troops_to_deploy=0,
        )
    )

    assert c1 in p1.contracts_completed
    assert c2 in p1.contracts_active  # still pending


# ─────────────── action_generator exposes contracts ───────────

def test_action_generator_exposes_contract_row():
    """action_generator.get_acquisition_options should include contract information."""
    game, p1, _, cm, *_ = setup_game()
    action_gen = ActionGenerator(game)
    p1.has_revealed_this_round = True
    p1.temp_persuasion = 5

    options = action_gen.get_acquisition_options(p1.player_id)

    # The imperium row must always be present
    assert "imperium_row" in options
    # Contract row must also be present
    assert "contract_row" in options or len(game.board.contract_row) == 2
