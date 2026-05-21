# Project Structure

## Overview

This document describes the organization of the DUNE: Imperium Uprising codebase.

## Directory Structure

```
DUNE Imperium Uprising/
├── data/                          # JSON game data
│   ├── conflicts.JSON             # Combat scenarios
│   ├── contracts.JSON             # Contract cards
│   ├── leaders.JSON               # Leader cards
│   ├── observation_posts.json    # Spy network locations
│   └── spaces.JSON               # Board spaces
│
├── src/
│   ├── models/                   # 📦 Data Models
│   │   ├── board.py              # Game board state
│   │   ├── boardspace.py         # Board location definitions
│   │   ├── card.py               # Card types (Imperium, Intrigue)
│   │   ├── deck.py               # Deck/hand management
│   │   ├── game.py               # Root game state
│   │   ├── leader.py             # Leader card model
│   │   └── player.py             # Player state
│   │
│   ├── loaders/                  # 📥 Data Loaders
│   │   ├── board_loader.py       # Load board spaces from JSON
│   │   └── card_loader.py        # Load cards from JSON
│   │
│   ├── engine/
│   │   ├── core/                 # 🎮 Core Game Systems
│   │   │   ├── game_setup.py     # Initialize new games
│   │   │   ├── game_state.py     # Query game state
│   │   │   └── game_logger.py    # Logging utilities
│   │   │
│   │   ├── actions/              # 🎯 Action System
│   │   │   ├── action_executor.py   # Execute player actions
│   │   │   └── action_generator.py  # Generate valid actions
│   │   │
│   │   ├── effects/              # ✨ Effect Resolution
│   │   │   └── effect_resolver.py   # Resolve all card/location effects
│   │   │
│   │   └── managers/             # 🔧 Game Phase Managers
│   │       ├── phase_manager.py        # Phase transitions
│   │       ├── combat_manager.py       # Combat resolution
│   │       ├── makers_manager.py       # MAKERS phase (spice)
│   │       ├── influence_manager.py    # Faction influence tracking
│   │       ├── victory_point_manager.py # VP tracking
│   │       ├── contract_manager.py     # Contract completion
│   │       └── deck_manager.py         # Deck shuffling
│   │
│   └── enum/                     # 🏷️ Enumerations
│       └── enums.py              # Game phase constants
│
├── test/                         # 🧪 Test Suite
│   └── test_*.py                 # Unit & integration tests
│
├── play_game.py                  # 🎮 Main Game UI
└── STRUCTURE.md                  # 📖 This file
```

## Module Purposes

### 📦 Models (`src/models/`)
Pure data classes representing game entities. No business logic.

- **game.py** - Root game container
- **player.py** - Player resources, cards, influence
- **board.py** - Board state (spaces, conflicts, contracts)
- **card.py** - Card definitions
- **deck.py** - Card collections (deck, hand, discard)

### 📥 Loaders (`src/loaders/`)
Convert JSON data files into Python model objects.

- **board_loader.py** - `load_board_spaces()`, `load_observation_posts()`
- **card_loader.py** - `load_imperium_cards()`, `load_intrigue_cards()`

### 🎮 Core (`src/engine/core/`)
Fundamental game initialization and state management.

- **game_setup.py** - `GameSetup.create_game()` - Initialize new games
- **game_state.py** - `GameState` - Query player/board state
- **game_logger.py** - Logging utilities

### 🎯 Actions (`src/engine/actions/`)
Player action handling (what players can do and how it's executed).

- **action_generator.py** - `ActionGenerator.get_valid_actions()` - Determine legal moves
- **action_executor.py** - `ActionExecutor.execute_*()` - Execute player actions

### ✨ Effects (`src/engine/effects/`)
Universal effect resolution system.

- **effect_resolver.py** - `EffectResolver.resolve_effects()` - Process all card/location effects

**Handles**: resources, draw, influence, trash, steal, recall, accept, play, choices, conditionals

### 🔧 Managers (`src/engine/managers/`)
Specialized systems for game phases and mechanics.

- **phase_manager.py** - Phase transitions (PLOT → REVEAL → COMBAT → MAKERS → RECALL → END)
- **combat_manager.py** - Combat resolution, rankings, rewards
- **makers_manager.py** - MAKERS phase (spice accumulation on maker spaces)
- **influence_manager.py** - Faction influence, alliances, VP bonuses
- **victory_point_manager.py** - VP tracking and win conditions
- **contract_manager.py** - Contract completion detection
- **deck_manager.py** - Deck shuffling (discard → deck)

## Data Flow

```
JSON Files (data/)
    ↓
Loaders (src/loaders/)
    ↓
Models (src/models/)
    ↓
Game Setup (engine/core/)
    ↓
Action Generator (engine/actions/) ← determines valid moves
    ↓
Action Executor (engine/actions/) → executes move
    ↓
Effect Resolver (engine/effects/) → resolves card/location effects
    ↓
Managers (engine/managers/) → handle phase-specific logic
    ↓
Game State (engine/core/) → queries for UI
    ↓
play_game.py → displays to player
```

## Key Principles

1. **Models are data-only** - No business logic in models
2. **Single source of truth** - All effects go through EffectResolver
3. **Managers are specialized** - Each handles one aspect (combat, influence, etc.)
4. **JSON drives behavior** - Game rules in JSON, not hardcoded
5. **Clear separation** - Actions vs Effects vs Managers

## Finding Your Way

**Want to modify...**
- Game setup? → `engine/core/game_setup.py`
- Valid actions? → `engine/actions/action_generator.py`
- Action execution? → `engine/actions/action_executor.py`
- Effect resolution? → `engine/effects/effect_resolver.py`
- Combat rules? → `engine/managers/combat_manager.py`
- Phase transitions? → `engine/managers/phase_manager.py`
- Faction influence? → `engine/managers/influence_manager.py`
- MAKERS phase? → `engine/managers/makers_manager.py`
- Data models? → `models/`
- JSON loading? → `loaders/`

**Testing?** → Check `test/test_*.py` files
**Playing?** → Run `python3 play_game.py`
