# DUNE Imperium Uprising - Game Engine Architecture

## Overview

This document explains how the game engine works: turn management, action handling, effect resolution, and player decision-making.

---

## 🏗️ Core Architecture Patterns

### **1. State Machine for Game Phases**

The game progresses through phases in a strict order:

```
SETUP → [BEGIN_ROUND → PLAYER_TURNS → COMBAT → MAKERS → RECALL] → GAME_OVER
         └─────────────── Repeat until win condition ──────────────┘
```

**Implementation**: `GamePhaseManager` controls phase transitions.

### **2. Command Pattern for Actions**

All player actions are represented as Command objects:
- **Encapsulates** what the player wants to do
- **Validates** if the action is legal
- **Executes** the action and updates game state
- **Can be serialized** for replay/undo

### **3. Observer Pattern for Reactive Events**

Game events trigger listeners:
- **Influence threshold crossed** → Award VP / Award bonus / Transfer alliance
- **Card acquired** → Trigger on-acquire effects
- **Agent placed** → Gain influence / Trigger location effects
- **Combat resolved** → Distribute rewards

---

## 📊 Game State Structure

```python
Game
├── phase: GamePhase (BEGIN_ROUND, PLAYER_TURNS, etc.)
├── round: int
├── players: List[Player]
├── current_player_index: int
├── first_player_index: int
├── board: Board
└── event_queue: List[Event]  # Pending effects to resolve
```

**Key Principle**: The game state is the **single source of truth**. All queries check the current state.

---

## 🎮 Turn System

### **Phase 1: Begin Round**

```python
def begin_round(game: Game):
    1. Reveal next conflict card from deck
    2. Each player draws 5 cards to hand
    3. Set phase to PLAYER_TURNS
    4. Reset current_player to first_player
```

### **Phase 2: Player Turns** (The Complex One)

Players take turns in clockwise order. Each player can take:
- **Agent Turns**: Play a card + place an agent (repeat until out of agents)
- **Reveal Turn**: Reveal remaining hand + acquire cards (once, then done)

**Critical Rule**: Once a player takes a Reveal turn, they're done for the round.

```python
while any player hasn't revealed:
    current_player = players[current_player_index]

    if current_player.has_revealed:
        advance_to_next_player()
        continue

    # Player chooses: Agent Turn or Reveal Turn
    action = await get_player_action(current_player)

    if action is AgentTurnAction:
        execute_agent_turn(action)
        # Player stays active

    elif action is RevealTurnAction:
        execute_reveal_turn(action)
        current_player.has_revealed = True
        advance_to_next_player()
```

---

## 🎯 Action System

### **Action Types**

```python
@dataclass
class Action:
    """Base class for all player actions"""
    player_id: str
    timestamp: float

@dataclass
class PlaceAgentAction(Action):
    """Play a card and place an agent"""
    card_id: str  # Card being played
    location_id: str  # Board space
    agent_icon_used: str  # Which icon from card (if multiple)
    spy_infiltrate: bool = False  # Using spy to infiltrate?
    spy_gather_info: bool = False  # Recalling spy for card draw?

@dataclass
class RevealAction(Action):
    """Reveal hand and acquire cards"""
    cards_in_hand: List[str]  # Card IDs being revealed
    acquisitions: List[AcquireCardAction]  # Cards to buy (in order)

@dataclass
class AcquireCardAction(Action):
    """Acquire a card during reveal turn"""
    card_id: str
    source: str  # "imperium_row", "reserve_prepare", "reserve_spice"

@dataclass
class DeployTroopsAction(Action):
    """Deploy troops during agent turn at combat space"""
    num_troops_from_recruitment: int  # From this turn's effects
    num_troops_from_garrison: int  # From garrison (max 2)

@dataclass
class PlayIntrigueAction(Action):
    """Play an intrigue card"""
    intrigue_card_id: str
    phase: IntriguePhase  # PLOT, COMBAT, or END_GAME

@dataclass
class PassAction(Action):
    """Pass during combat intrigue phase"""
    pass
```

---

## ✅ Action Validation

Before executing an action, validate it:

```python
class ActionValidator:
    def validate_place_agent(self, game: Game, action: PlaceAgentAction) -> tuple[bool, str]:
        """Returns (is_valid, error_message)"""

        player = game.get_player(action.player_id)
        card = player.get_card_by_id(action.card_id)
        location = game.board.get_space_by_id(action.location_id)

        # Check 1: Player has agents available
        if player.available_agents == 0:
            return False, "No agents available"

        # Check 2: Card is in player's hand
        if card not in player.hand.cards:
            return False, "Card not in hand"

        # Check 3: Card has required agent icon
        if not action.spy_infiltrate:  # Normal placement
            if action.agent_icon_used not in card.agent_icons:
                return False, f"Card doesn't have {action.agent_icon_used} icon"

            if action.agent_icon_used != location.agent_icon:
                return False, f"Icon mismatch: {action.agent_icon_used} != {location.agent_icon}"

        else:  # Spy infiltration
            spy_posts = game.board.get_observation_posts_for_player(player.player_id)
            can_infiltrate = any(
                location.id in post.connected_locations
                for post in spy_posts
            )
            if not can_infiltrate:
                return False, "No spy connected to this location"

        # Check 4: Location not occupied (unless infiltrating)
        if location.occupied_by is not None and not action.spy_infiltrate:
            return False, "Location already occupied"

        # Check 5: Can pay location cost
        if not player.can_pay_cost(location.cost):
            return False, f"Cannot afford cost: {location.cost}"

        # Check 6: Meet influence requirement
        if location.required_influence:
            faction = list(location.required_influence.keys())[0]
            required = location.required_influence[faction]
            current = player.get_influence(faction)
            if current < required:
                return False, f"Need {required} {faction} influence (have {current})"

        return True, "Valid"
```

---

## ⚡ Action Execution

Once validated, execute the action:

```python
class ActionExecutor:
    def execute_place_agent(self, game: Game, action: PlaceAgentAction):
        """Execute an agent placement action"""

        player = game.get_player(action.player_id)
        card = player.get_card_by_id(action.card_id)
        location = game.board.get_space_by_id(action.location_id)

        # 1. Pay location cost
        player.pay_cost(location.cost)

        # 2. Remove agent from player
        player.available_agents -= 1
        player.placed_agents.append(location.id)

        # 3. Occupy location
        location.occupied_by = player.player_id

        # 4. Recall spy if infiltrating or gathering info
        if action.spy_infiltrate:
            game.recall_spy_from_post_connected_to(location.id, player.player_id)
        if action.spy_gather_info:
            game.recall_spy_from_post_connected_to(location.id, player.player_id)
            player.draw_card()  # Draw a card for gathering info

        # 5. Move card from hand to play area
        player.hand.remove(card)
        player.cards_played_this_turn.append(card)

        # 6. Gain faction influence if applicable
        if location.faction:
            player.gain_influence(location.faction, 1)

        # 7. Resolve card agent effects
        effect_executor = EffectExecutor(game)
        effect_executor.resolve_effects(card.agent_effects, player.player_id)

        # 8. Resolve location effects
        effect_executor.resolve_effects(location.effects, player.player_id)

        # 9. Apply control bonus if someone controls this location
        if location.controlled_by and location.controlled_by != player.player_id:
            controller = game.get_player(location.controlled_by)
            effect_executor.resolve_effects(location.control_bonus, controller.player_id)

        # 10. If combat space, prompt for troop deployment
        if location.is_combat_space:
            max_from_garrison = 2
            troops_gained_this_turn = self.count_troop_effects_this_turn(player)
            # This would trigger a deployment prompt in the UI
            game.pending_action = DeployTroopsPrompt(
                player_id=player.player_id,
                max_from_recruitment=troops_gained_this_turn,
                max_from_garrison=min(player.troops_in_garrison, max_from_garrison)
            )
```

---

## 🎲 Effect Resolution System

Effects are the core of the game. They come from:
- **Cards** (agent effects, reveal effects, on-acquire effects)
- **Board locations** (effects when agent placed)
- **Intrigue cards**
- **Leader abilities**
- **Conflict rewards**

### **Effect Representation**

Effects are stored as dictionaries:

```python
effects = {
    "solari": 2,  # Gain 2 Solari
    "spice": 1,   # Gain 1 Spice
    "water": -1,  # Lose 1 Water (cost)
    "persuasion": 3,  # Gain 3 Persuasion
    "draw": 1,  # Draw 1 card
    "recruit_troops": 2,  # Recruit 2 troops to garrison
    "emperor_influence": 1,  # Gain 1 Emperor influence
    "intrigue_card": 1,  # Draw 1 Intrigue card
    "place_spy": 1,  # Place 1 spy
    "swords": 2,  # Add 2 swords (combat strength)
}
```

### **Effect Executor**

```python
class EffectExecutor:
    def __init__(self, game: Game):
        self.game = game
        self.event_bus = EventBus()

    def resolve_effects(self, effects: dict[str, int], player_id: str):
        """Resolve a dictionary of effects for a player"""

        player = self.game.get_player(player_id)

        for effect_type, amount in effects.items():
            self.resolve_single_effect(effect_type, amount, player)

    def resolve_single_effect(self, effect_type: str, amount: int, player: Player):
        """Resolve a single effect"""

        # Resources
        if effect_type == "solari":
            player.solari += amount
            self.event_bus.emit(ResourceGainedEvent(player.player_id, "solari", amount))

        elif effect_type == "spice":
            player.spice += amount
            self.event_bus.emit(ResourceGainedEvent(player.player_id, "spice", amount))

        elif effect_type == "water":
            player.water += amount
            self.event_bus.emit(ResourceGainedEvent(player.player_id, "water", amount))

        # Persuasion (only matters during reveal turn)
        elif effect_type == "persuasion":
            player.temp_persuasion += amount  # Temporary, cleared after reveal

        # Card draws
        elif effect_type == "draw":
            for _ in range(amount):
                player.draw_card()

        # Troops
        elif effect_type == "recruit_troops":
            player.recruit_troops(amount)

        # Influence
        elif effect_type.endswith("_influence"):
            faction = effect_type.replace("_influence", "")
            old_influence = player.get_influence(faction)
            player.gain_influence(faction, amount)
            new_influence = player.get_influence(faction)

            # Emit event for threshold checking
            self.event_bus.emit(InfluenceChangedEvent(
                player.player_id, faction, old_influence, new_influence
            ))

        # Intrigue
        elif effect_type == "intrigue_card":
            for _ in range(amount):
                card = self.game.board.intrigue_deck.draw()
                if card:
                    player.intrigue_cards.add_card(card)

        # Spies
        elif effect_type == "place_spy":
            # This triggers a prompt for the player to choose where to place spy
            self.game.pending_action = PlaceSpyPrompt(player.player_id, amount)

        # Swords (combat)
        elif effect_type == "swords":
            player.temp_swords += amount  # Added during reveal, cleared after combat

        # Victory points
        elif effect_type == "victory_points":
            player.victory_points += amount
            self.event_bus.emit(VictoryPointsChangedEvent(player.player_id, amount))
```

---

## 🎭 Event System & Reactive Effects

Some effects trigger other effects:

### **Event Types**

```python
@dataclass
class GameEvent:
    timestamp: float

@dataclass
class InfluenceChangedEvent(GameEvent):
    player_id: str
    faction: str
    old_value: int
    new_value: int

@dataclass
class CardAcquiredEvent(GameEvent):
    player_id: str
    card_id: str

@dataclass
class AgentPlacedEvent(GameEvent):
    player_id: str
    location_id: str
```

### **Event Listeners**

```python
class InfluenceThresholdListener:
    def on_influence_changed(self, event: InfluenceChangedEvent):
        """React to influence changes"""

        player = game.get_player(event.player_id)

        # Check if crossed 2 influence threshold (gain/lose VP)
        if event.old_value < 2 and event.new_value >= 2:
            player.victory_points += 1
            print(f"{player.name} reached 2 {event.faction} influence: +1 VP")

        elif event.old_value >= 2 and event.new_value < 2:
            player.victory_points -= 1
            print(f"{player.name} fell below 2 {event.faction} influence: -1 VP")

        # Check if crossed 4 influence threshold (one-time bonus)
        if event.old_value < 4 and event.new_value >= 4:
            bonus = FACTION_BONUSES[event.faction]
            effect_executor.resolve_effects(bonus, player.player_id)
            print(f"{player.name} reached 4 {event.faction} influence: Bonus!")

            # Check for alliance
            current_alliance_holder = game.get_alliance_holder(event.faction)
            if current_alliance_holder is None:
                # First to 4 - gain alliance
                player.gain_alliance(event.faction)
                player.victory_points += 1
                print(f"{player.name} gains {event.faction} alliance!")

            elif current_alliance_holder.get_influence(event.faction) < event.new_value:
                # Surpassed current holder - steal alliance
                current_alliance_holder.lose_alliance(event.faction)
                current_alliance_holder.victory_points -= 1
                player.gain_alliance(event.faction)
                player.victory_points += 1
                print(f"{player.name} steals {event.faction} alliance from {current_alliance_holder.name}!")
```

---

## 🤖 Player Decision Points

The game needs to prompt players for decisions at various points:

### **Decision Types**

```python
@dataclass
class Decision:
    """Base class for player decisions"""
    player_id: str
    decision_type: str

@dataclass
class ChooseActionDecision(Decision):
    """Choose between Agent Turn or Reveal Turn"""
    can_take_agent_turn: bool
    available_agents: int

@dataclass
class ChooseCardToPlayDecision(Decision):
    """Choose which card to play for agent turn"""
    available_cards: List[ImperiumCard]

@dataclass
class ChooseLocationDecision(Decision):
    """Choose where to place agent"""
    card_played: ImperiumCard
    available_locations: List[BoardSpace]  # Pre-filtered for valid placements

@dataclass
class ChooseCardsToAcquireDecision(Decision):
    """Choose which cards to acquire during reveal turn"""
    available_persuasion: int
    imperium_row: List[ImperiumCard]
    reserve_piles: dict[str, ImperiumCard]

@dataclass
class ChooseTroopDeploymentDecision(Decision):
    """Choose how many troops to deploy"""
    max_from_recruitment: int
    max_from_garrison: int

@dataclass
class ChooseInfluenceFactionDecision(Decision):
    """Choose which faction to gain influence with"""
    num_choices: int  # How many factions to choose
    available_factions: List[str]

@dataclass
class PlaceSpyDecision(Decision):
    """Choose where to place a spy"""
    available_posts: List[ObservationPost]
```

### **Decision Resolution Flow**

```python
# In the game loop
while game.phase == GamePhase.PLAYER_TURNS:
    current_player = game.get_current_player()

    if current_player.has_revealed:
        game.advance_to_next_player()
        continue

    # Step 1: Ask player what kind of turn they want
    decision = ChooseActionDecision(
        player_id=current_player.player_id,
        can_take_agent_turn=current_player.available_agents > 0
    )

    response = await game_interface.get_player_decision(decision)

    if response.choice == "agent_turn":
        # Step 2: Ask which card to play
        decision = ChooseCardToPlayDecision(
            player_id=current_player.player_id,
            available_cards=current_player.hand.cards
        )
        response = await game_interface.get_player_decision(decision)
        card_to_play = response.chosen_card

        # Step 3: Ask where to place agent
        valid_locations = validator.get_valid_locations_for_card(game, card_to_play)
        decision = ChooseLocationDecision(
            player_id=current_player.player_id,
            card_played=card_to_play,
            available_locations=valid_locations
        )
        response = await game_interface.get_player_decision(decision)
        location = response.chosen_location

        # Step 4: Execute action
        action = PlaceAgentAction(
            player_id=current_player.player_id,
            card_id=card_to_play.id,
            location_id=location.id,
            agent_icon_used=response.icon_used
        )
        executor.execute_place_agent(game, action)

        # Step 5: Handle any pending sub-decisions (troop deployment, spy placement, etc.)
        while game.pending_decision:
            sub_decision = game.pending_decision
            sub_response = await game_interface.get_player_decision(sub_decision)
            executor.execute_sub_action(game, sub_response)

    elif response.choice == "reveal_turn":
        # ... reveal turn logic
        current_player.has_revealed = True
        game.advance_to_next_player()
```

---

## 🗡️ Combat Resolution

Combat happens in Phase 3 after all players have revealed.

```python
def resolve_combat(game: Game):
    """Phase 3: Combat"""

    # Step 1: Calculate initial strength for all players
    for player in game.players:
        strength = 0

        if player.troops_in_conflict > 0:
            strength += player.troops_in_conflict * 2  # 2 per troop
            strength += player.sandworms_in_conflict * 3  # 3 per sandworm
            strength += player.temp_swords  # From reveal turn
        else:
            strength = 0  # Must have at least 1 troop

        player.combat_strength = strength

    # Step 2: Combat Intrigue phase (players can play Combat Intrigue cards)
    combat_intrigue_round(game)

    # Step 3: Determine rankings
    rankings = sorted(game.players, key=lambda p: p.combat_strength, reverse=True)

    # Step 4: Distribute rewards
    conflict = game.board.current_conflict

    # Handle ties
    if rankings[0].combat_strength == rankings[1].combat_strength:
        # Tie for first - both get 2nd place reward
        for player in [rankings[0], rankings[1]]:
            if player.combat_strength > 0:
                grant_reward(player, conflict.rewards[1])  # 2nd place reward
    else:
        # Winner gets 1st place reward + conflict card
        winner = rankings[0]
        if winner.combat_strength > 0:
            grant_reward(winner, conflict.rewards[0])
            winner.conflict_cards_won.append(conflict)
            check_battle_icon_pair(winner)

        # 2nd place
        if rankings[1].combat_strength > 0:
            grant_reward(rankings[1], conflict.rewards[1])

        # 3rd place (if applicable)
        if len(rankings) >= 3 and rankings[2].combat_strength > 0:
            grant_reward(rankings[2], conflict.rewards[2])

    # Step 5: Return troops to reserve (not garrison!)
    for player in game.players:
        player.troops_in_reserve += player.troops_in_conflict
        player.troops_in_conflict = 0
        player.sandworms_in_conflict = 0
        player.temp_swords = 0

    # Step 6: Move to next phase
    game.phase = GamePhase.MAKERS
```

---

## 📈 Key Design Principles

1. **Separation of Concerns**
   - Models: Data structures only
   - Validators: Check if actions are legal
   - Executors: Perform actions and update state
   - Event system: React to state changes

2. **Single Source of Truth**
   - Game state object contains all information
   - No derived state stored redundantly
   - Calculations done on-demand (e.g., combat_strength as property)

3. **Explicit State Transitions**
   - Phase changes are explicit
   - Action execution updates state atomically
   - Events are emitted after state changes

4. **Testability**
   - Each component can be unit tested independently
   - Deterministic behavior (use seed for randomness)
   - Actions can be serialized and replayed

---

## 🚀 Next Steps for Implementation

1. **Create Game model** (if not done)
2. **Create GamePhaseManager** - handles phase transitions
3. **Create Action classes** - all action types
4. **Create ActionValidator** - validation logic
5. **Create ActionExecutor** - execution logic
6. **Create EffectExecutor** - effect resolution
7. **Create EventBus** - event system
8. **Create Decision interfaces** - player prompts
9. **Test with simple scenarios** - place agent, reveal, combat

---

## 🎯 Recommended Implementation Order

**Week 1: Core Loop**
- Game model + setup
- Phase manager (basic transitions)
- Begin Round phase implementation

**Week 2: Agent Turns**
- PlaceAgentAction + validation + execution
- Effect executor (basic effects: resources, draw, troops)
- Test: Place agent, gain resources

**Week 3: Reveal Turn + Combat**
- RevealAction + card acquisition
- Persuasion system
- Combat resolution (basic, no intrigue)

**Week 4: Advanced Features**
- Spy system
- Sandworms + Maker locations
- Influence thresholds + events
- Combat intrigue

**Week 5: Leader Abilities**
- Leader ability framework
- Signet ring activation
- Passive ability triggers

---

This architecture gives you a clean, testable, extensible system for implementing the full game. Focus on getting the basic loop working first (Begin Round → Agent Turn → Reveal Turn → Combat → Recall), then layer on complexity.

Ready to start implementing? Which part would you like to tackle first?
