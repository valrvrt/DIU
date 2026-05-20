# Game Log Viewer

Quick tool to read JSON game logs in human-readable format.

## Usage

```bash
# Interactive mode - choose from list of games
python view_game_log.py

# View specific log file directly
python view_game_log.py game_logs/game_20260520_232409.json
```

### Interactive Mode

When run without arguments, you'll see a menu like:

```
================================================================================
Available Game Logs (newest first)
================================================================================
 1. [2026-05-20 23:24:31] Game 20260520_232409 - 4P - 150 events
 2. [2026-05-20 23:23:10] Game 20260520_232248 - 3P - 129 events
 3. [2026-05-20 23:22:39] Game 20260520_232218 - 3P - 128 events
...
================================================================================

Enter log number to view (or 'q' to quit):
```

Just type the number of the game you want to view, or 'q' to quit!

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

- **Interactive selection** - Browse and choose from all available games
- **Chronological display** - Events shown by round and phase
- **Clear visual separators** - Easy to follow game flow
- **Player actions with context** - See exactly what happened
- **Resource tracking** - Monitor player resources at key phases
- **Game metadata** - Shows player count and event count in list
- **Sorted by recency** - Newest games first
