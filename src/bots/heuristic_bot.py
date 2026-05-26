"""
Heuristic Bot - Scores every legal action and picks the best.

Scoring philosophy:
- Resources are converted to a common "value" unit (water/spice/solari/troop/etc.)
- Influence is worth more when close to an alliance/perk milestone
- Direct victory points dominate everything in the late game
- Combat spaces score higher when the current conflict reward is strong
- Spy-infiltrated spaces get a "gather intel" bonus on top of normal value
- Faction-matched spaces score higher (synergy with leader/deck)
"""

import random
from typing import Optional, List, Tuple, Dict, Any

from .base_bot import BaseBot
from ..models.card import ImperiumCard, IntrigueCard
from ..models.boardspace import BoardSpace
from ..engine.actions.action_executor import PlaceAgentAction


# Base value of each resource type, in "VP-equivalent" units.
RESOURCE_VALUE = {
    "victory_point": 10.0,
    "water": 3.0,
    "spice": 2.0,
    "solari": 1.0,
    "troop": 1.5,
    "persuasion": 1.0,
    "sword": 1.2,
    "agent": 8.0,        # extra agent is huge
    "intrigue": 2.0,
}

# Drawing a card from your own deck.
DRAW_DECK_VALUE = 1.0
DRAW_INTRIGUE_VALUE = 2.0
TRASH_VALUE = 0.8          # trashing a starter card is good but not huge

# Influence: every 2 ticks gives some payoff (resource at 1, signet at 3, alliance at 4).
INFLUENCE_TICK_VALUE = 1.8

# Strategy weights.
FACTION_SYNERGY_BONUS = 1.5
CONTRACT_COMPLETION_BONUS = 6.0
SPY_GATHER_INTEL_BONUS = 2.0
COMBAT_SPACE_WEIGHT = 1.0


class HeuristicBot(BaseBot):
    """
    Scoring-based bot. Picks the highest-scoring legal action at every decision point.
    """

    def __init__(self, player, managers, noise: float = 0.05):
        super().__init__(player, managers)
        self.game = managers.get("game")
        self.noise = noise  # small random jitter to avoid identical play

    # ----------------------------------------------------------------- public

    def decide_agent_action(self) -> Optional[PlaceAgentAction]:
        """Pick the highest-scoring (card, location, troops) placement."""
        playable_cards = self.get_playable_cards()
        if not playable_cards:
            return None

        best_action = None
        best_score = float("-inf")

        for card in playable_cards:
            locations = self.get_valid_locations_for_card(card)
            for location, placement_type in locations:
                score = self._score_placement(card, location, placement_type)
                # Skip placements with strongly negative net value unless we have to.
                if score > best_score:
                    best_score = score
                    troops = self._decide_troops_for_placement(location, placement_type)
                    best_action = PlaceAgentAction(
                        player_id=self.player.player_id,
                        card=card,
                        location=location,
                        placement_type=placement_type,
                        troops_to_deploy=troops,
                    )

        # If every option is awful AND we haven't run out of agents yet,
        # consider revealing instead. Threshold is small + negative.
        if best_action is None:
            return None
        if best_score < -3.0 and self.player.agents_available > 1:
            return None
        return best_action

    def decide_card_to_acquire(self, available_cards: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """Buy the highest-value card we can afford."""
        persuasion = getattr(self.player, "temp_persuasion", 0)
        affordable = [c for c in available_cards if c.cost <= persuasion]
        if not affordable:
            return None

        scored = [(self._score_card_acquisition(c), c) for c in affordable]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_card = scored[0]
        # Don't buy actively bad cards just because we can.
        if best_score < 1.0:
            return None
        return best_card

    def decide_intrigue_to_play(self, available_intrigues: List[IntrigueCard]) -> Optional[IntrigueCard]:
        """
        Play combat intrigues if they would change our ranking.
        Otherwise hold them.
        """
        if not available_intrigues:
            return None

        my_strength = self._estimate_combat_strength(self.player)
        opponents = [p for p in self.game.players if p.player_id != self.player.player_id]
        # Strongest opponent currently in combat.
        opp_strengths = [self._estimate_combat_strength(p) for p in opponents]
        max_opp = max(opp_strengths) if opp_strengths else 0

        # If we're winning by a lot, no need to spend intrigues.
        if my_strength > max_opp + 4:
            return None
        # If we're losing by too much, an intrigue won't save us either.
        if my_strength + 6 < max_opp:
            return None

        # Otherwise play one — pick first available combat intrigue.
        return available_intrigues[0]

    def decide_troops_to_deploy(self, max_troops: int) -> int:
        """
        Deploy enough troops to either be competitive in this conflict
        or save them for later.
        """
        if max_troops == 0:
            return 0

        conflict = getattr(self.game.board, "current_conflict", None)
        reward_value = self._score_conflict_rewards(conflict)

        # Reference: opponents' visible troop+sword strength right now.
        opponents = [p for p in self.game.players if p.player_id != self.player.player_id]
        opp_strengths = [self._estimate_combat_strength(p) for p in opponents]
        max_opp = max(opp_strengths) if opp_strengths else 0
        my_current = self._estimate_combat_strength(self.player)

        # We want to reach roughly max_opp + 2 strength.
        needed_strength = max_opp + 2 - my_current
        if needed_strength <= 0:
            # We already lead. Defend with 1 if reward is worth it, else save.
            return 1 if reward_value >= 4 and max_troops >= 1 else 0

        # Each troop adds 2 strength.
        wanted_troops = (needed_strength + 1) // 2

        # Cap by reward worth: low-reward conflicts aren't worth all-in.
        if reward_value < 2:
            wanted_troops = min(wanted_troops, 1)
        elif reward_value < 5:
            wanted_troops = min(wanted_troops, 3)

        return max(0, min(wanted_troops, max_troops))

    def decide_card_to_discard(self, hand: List[ImperiumCard]) -> Optional[ImperiumCard]:
        """Discard the lowest-value card."""
        if not hand:
            return None
        return min(hand, key=lambda c: self._score_card_in_hand(c))

    def should_reveal(self) -> bool:
        action = self.decide_agent_action()
        return action is None

    # ---------------------------------------------------------------- scoring

    def _score_effects(self, effects, context: Optional[Dict[str, Any]] = None) -> float:
        """Score a list of effect dicts (same shape as JSON: type, resource, amount...)."""
        if not effects:
            return 0.0
        if isinstance(effects, dict):
            # Single effect object passed directly
            return self._score_single_effect(effects, context or {})
        total = 0.0
        for e in effects:
            if isinstance(e, list):
                total += self._score_effects(e, context)
            elif isinstance(e, dict):
                total += self._score_single_effect(e, context or {})
        return total

    def _score_single_effect(self, e: dict, context: Dict[str, Any]) -> float:
        etype = e.get("type")
        amount = e.get("amount", 1)

        if etype == "resource":
            r = e.get("resource", "")
            base = RESOURCE_VALUE.get(r, 0.5)
            # Late-game spice/solari is less useful; water always useful.
            return base * amount

        if etype == "victory_point":
            return RESOURCE_VALUE["victory_point"] * amount

        if etype == "influence":
            target = e.get("target", "")
            return self._score_influence_gain(target, amount)

        if etype == "draw":
            deck = e.get("deck", "deck")
            if deck == "intrigue":
                return DRAW_INTRIGUE_VALUE * amount
            return DRAW_DECK_VALUE * amount

        if etype == "trash":
            # Only useful if we still have starter junk to trash.
            return TRASH_VALUE * amount

        if etype == "recall":
            # Recall agent — usually quite strong (extra placement this round).
            unit = e.get("unit", "agent")
            return 4.0 if unit == "agent" else 1.0

        if etype == "choice":
            # Use the best option among the choice list.
            best = 0.0
            for opt in e.get("options", []):
                reward = opt.get("reward", [])
                cost = opt.get("cost", [])
                opt_val = self._score_effects(reward, context) - self._score_effects(cost, context)
                best = max(best, opt_val)
            return best

        if etype == "conditional":
            # Score reward if condition is met, else 0 (we won't know without lots of state).
            return self._score_effects(e.get("reward", []), context) * 0.5

        if etype == "spy":
            # Placing a spy: future value (gather intel + infiltrate options).
            return 2.5 * amount

        # Unknown — assume neutral.
        return 0.0

    def _score_influence_gain(self, faction: str, amount: int) -> float:
        """Influence is worth more when you're close to a milestone (signet at 3, alliance at 4)."""
        attr_map = {
            "fremen": "fremen_influence",
            "bene_gesserit": "bene_gesserit_influence",
            "spacing_guild": "spacing_guild_influence",
            "emperor": "emperor_influence",
        }
        attr = attr_map.get(faction)
        if not attr:
            return INFLUENCE_TICK_VALUE * amount

        current = getattr(self.player, attr, 0)
        new_val = min(current + amount, 4)
        gained_ticks = new_val - current
        if gained_ticks <= 0:
            return 0.0

        value = 0.0
        for i in range(current + 1, new_val + 1):
            # Milestone bonuses
            if i == 1:
                value += INFLUENCE_TICK_VALUE      # +1 resource
            elif i == 2:
                value += INFLUENCE_TICK_VALUE + 0.5
            elif i == 3:
                value += INFLUENCE_TICK_VALUE + 2.0  # signet ring perk
            elif i == 4:
                value += INFLUENCE_TICK_VALUE + 4.0  # alliance (+ ongoing VP)
        return value

    def _score_placement(self, card: ImperiumCard, location: BoardSpace, placement_type: str) -> float:
        """Score placing an agent at `location` using `card`."""
        # Base value: rewards minus cost.
        reward_val = self._score_effects(location.reward)
        cost_val = self._score_effects(location.cost)

        # Combat space: add expected combat reward (we'll fight if rewards are good).
        if location.is_combat_space:
            conflict = getattr(self.game.board, "current_conflict", None)
            expected = self._expected_combat_value(conflict)
            reward_val += expected * COMBAT_SPACE_WEIGHT

        # Critical location control bonus (Arrakeen, Spice Refinery, Imperial Basin).
        if getattr(location, "is_critical_location", False):
            reward_val += 1.5
            if location.controlled_by != self.player.player_id:
                reward_val += 2.0  # take control

        # Faction synergy: leader matches space's faction.
        if location.faction:
            leader_factions = self._leader_factions()
            if location.faction.lower() in leader_factions:
                reward_val += FACTION_SYNERGY_BONUS

        # Card's agent effects also trigger when placing.
        agent_effects = getattr(card, "agent_effects", [])
        if isinstance(agent_effects, list):
            reward_val += self._score_effects(agent_effects)

        # Maker space (spice accumulation).
        if getattr(location, "is_maker_space", False):
            reward_val += getattr(location, "spice_bonus", 0) * RESOURCE_VALUE["spice"] * 0.8

        # Spy gather intel: if we have a spy on this space, normal placement triggers
        # a free intrigue draw. Big bonus.
        if placement_type != "spy_infiltrate":
            spies_placed = getattr(self.player, "spies_placed", [])
            if str(location.id) in [str(x) for x in spies_placed]:
                reward_val += SPY_GATHER_INTEL_BONUS

        # Spy infiltrate: lets us share a space, but consumes a spy.
        if placement_type == "spy_infiltrate":
            reward_val -= 1.0  # spy is a finite resource

        # Contract completion check.
        if self._would_complete_location_contract(location):
            reward_val += CONTRACT_COMPLETION_BONUS

        # Tiny noise to avoid identical games.
        if self.noise:
            reward_val += random.uniform(-self.noise, self.noise) * 5

        return reward_val - cost_val

    def _score_card_acquisition(self, card: ImperiumCard) -> float:
        """Score acquiring `card` into the deck."""
        reveal = getattr(card, "reveal_effects", []) or []
        agent_eff = getattr(card, "agent_effects", []) or []
        on_acquire = getattr(card, "on_acquire_effects", []) or []

        reveal_val = self._score_effects(reveal)
        agent_val = self._score_effects(agent_eff) * 0.7  # only triggers when used as agent
        acquire_val = self._score_effects(on_acquire) * 1.2  # immediate

        # Persuasion-yielding cards loop back into more buying power.
        for e in reveal:
            if e.get("type") == "resource" and e.get("resource") == "persuasion":
                reveal_val += 0.3 * e.get("amount", 1)

        # Faction synergy bonus.
        factions = getattr(card, "factions", []) or []
        leader_factions = self._leader_factions()
        if any(f.lower() in leader_factions for f in factions):
            reveal_val += FACTION_SYNERGY_BONUS

        # Agent icons broaden where we can play — small bonus per icon.
        agent_icons = getattr(card, "agent_icons", []) or []
        icon_bonus = 0.4 * len(agent_icons)

        # Cost penalty: cheaper effective value matters.
        cost_penalty = card.cost * 0.6

        total = reveal_val + agent_val + acquire_val + icon_bonus - cost_penalty

        if self.noise:
            total += random.uniform(-self.noise, self.noise) * 3
        return total

    def _score_card_in_hand(self, card: ImperiumCard) -> float:
        """Score a card we already have (used for discard decisions: lower = discard first)."""
        reveal = getattr(card, "reveal_effects", []) or []
        agent_eff = getattr(card, "agent_effects", []) or []
        return self._score_effects(reveal) + self._score_effects(agent_eff) * 0.5

    def _score_conflict_rewards(self, conflict) -> float:
        """Approximate value of finishing 1st in this conflict."""
        if not conflict:
            return 0.0
        rewards = getattr(conflict, "rewards", {}) or {}
        first = rewards.get("1") or rewards.get(1) or []
        return self._score_effects(first)

    def _expected_combat_value(self, conflict) -> float:
        """
        Expected VP-equivalent value from going into combat right now.
        Weighted by how strong our position is.
        """
        if not conflict:
            return 0.0
        rewards = getattr(conflict, "rewards", {}) or {}
        first = self._score_effects(rewards.get("1") or rewards.get(1) or [])
        second = self._score_effects(rewards.get("2") or rewards.get(2) or [])

        my_strength = self._estimate_combat_strength(self.player)
        opponents = [p for p in self.game.players if p.player_id != self.player.player_id]
        opp_strengths = [self._estimate_combat_strength(p) for p in opponents]
        max_opp = max(opp_strengths) if opp_strengths else 0

        if my_strength == 0 and max_opp == 0:
            # Nobody in conflict yet; assume we could place to be near 1st.
            return first * 0.4
        if my_strength >= max_opp:
            return first * 0.7 + second * 0.2
        if my_strength + 4 >= max_opp:
            return first * 0.3 + second * 0.5
        return second * 0.3

    def _estimate_combat_strength(self, player) -> int:
        troops = getattr(player, "troops_in_conflict", 0)
        sandworms = getattr(player, "sandworms_in_conflict", 0)
        swords = getattr(player, "temp_swords", 0)
        return troops * 2 + sandworms * 3 + swords

    def _decide_troops_for_placement(self, location: BoardSpace, placement_type: str) -> int:
        """When placing at a combat space, decide how many troops to send along."""
        if placement_type == "spy_infiltrate":
            return 0
        if not location.is_combat_space:
            return 0
        garrison = getattr(self.player, "troops_in_garrison", 0)
        if garrison <= 0:
            return 0

        conflict = getattr(self.game.board, "current_conflict", None)
        reward_val = self._score_conflict_rewards(conflict)
        if reward_val < 2:
            return 0 if garrison < 3 else 1
        if reward_val < 5:
            return min(2, garrison)
        return min(3, garrison)

    # --------------------------------------------------------------- helpers

    def _leader_factions(self) -> List[str]:
        """Factions the player's leader pushes — used for synergy scoring."""
        leader = getattr(self.player, "leader", None)
        if not leader:
            return []
        # Heuristic: read the leader's ring/signet faction icons if present.
        ring = getattr(leader, "ring", None) or {}
        if isinstance(ring, dict):
            return [k.lower() for k in ring.keys() if isinstance(k, str)]
        return []

    def _would_complete_location_contract(self, location: BoardSpace) -> bool:
        """Check if placing at `location` would complete any active contract."""
        for contract in getattr(self.player, "contracts_active", []):
            if contract.completion_type != "location":
                continue
            target = (contract.completion_target or "").lower()
            if not target:
                continue
            loc_name = (location.name or "").lower()
            loc_id = str(getattr(location, "id", "")).lower()
            if target == loc_name or target == loc_id or target in loc_name:
                return True
        return False
