# Game Log Viewer

Quick tool to read JSON game logs in human-readable format.

## Usage

```bash
# View most recent game log
python view_game_log.py

# View specific log file
python view_game_log.py game_logs/game_20260520_232409.json
```

## Output Example

```
================================================================================
GAME LOG: 20260520_232409
================================================================================

ROUND 1
================================================================================

--- Phase: PLAYER TURNS ---
  🎯 Bot 1: Placed agent - Dune, la Planète des Sables → Desert Tactics
  🤖 Bot 2 chose: Dune, la Planète des Sables -> Fremkit
  🃏 Bot 3: Revealed 5 cards (persuasion: 3)

--- Phase: COMBAT ---
  ⚔️  COMBAT RESULTS:
    Winner: Bot 1 (5 strength)

--- Phase: RECALL ---
  📊 Player Status:
    Bot 1: VP=1 | Solari=2 Spice=0 Water=1
```

## Icons Used

- 🎯 Agent placement
- 🃏 Card reveal
- 💰 Card acquisition
- ⚔️  Combat
- 🤖 Bot decision
- 📊 Player status
- 🏁 Game over
- 🏆 Winner

## Features

- Chronological display by round and phase
- Clear visual separators
- Player actions with context
- Resource tracking
- Auto-finds latest log if no file specified
