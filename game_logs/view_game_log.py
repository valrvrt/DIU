#!/usr/bin/env python3
"""
Game Log Viewer - Makes JSON game logs human-readable.

Usage:
    python view_game_log.py <log_file.json>
    python view_game_log.py  # Uses most recent log
"""

import json
import sys
from pathlib import Path
from datetime import datetime


def get_all_logs():
    """Get all game log files sorted by modification time (newest first)."""
    log_dir = Path("game_logs")
    if not log_dir.exists():
        print("Error: game_logs directory not found")
        sys.exit(1)

    log_files = list(log_dir.glob("game_*.json"))
    if not log_files:
        print("Error: No game log files found")
        sys.exit(1)

    # Sort by modification time, newest first
    return sorted(log_files, key=lambda f: f.stat().st_mtime, reverse=True)


def find_latest_log():
    """Find the most recent game log file."""
    return get_all_logs()[0]


def choose_log_interactive():
    """Let user choose which log to view."""
    log_files = get_all_logs()

    print("=" * 80)
    print("Available Game Logs (newest first)")
    print("=" * 80)

    for i, log_file in enumerate(log_files, 1):
        # Get file modification time
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        time_str = mtime.strftime("%Y-%m-%d %H:%M:%S")

        # Try to read game info
        try:
            with open(log_file, 'r') as f:
                data = json.load(f)

            game_id = data.get('game_id', '?')
            event_count = data.get('total_events', len(data.get('events', [])))

            # Find player count from setup event
            player_count = '?'
            for event in data.get('events', []):
                if event.get('event_type') == 'game_setup':
                    player_count = event.get('player_count', '?')
                    break

            print(f"{i:2}. [{time_str}] Game {game_id} - {player_count}P - {event_count} events")
        except:
            print(f"{i:2}. [{time_str}] {log_file.name}")

    print("=" * 80)

    while True:
        try:
            choice = input("\nEnter log number to view (or 'q' to quit): ").strip().lower()

            if choice == 'q':
                print("Exiting...")
                sys.exit(0)

            index = int(choice) - 1
            if 0 <= index < len(log_files):
                return log_files[index]
            else:
                print(f"Please enter a number between 1 and {len(log_files)}")
        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)


def format_timestamp(ts):
    """Format timestamp to readable time."""
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except:
        return ts


def display_game_log(log_file):
    """Display game log in human-readable format."""
    with open(log_file, 'r') as f:
        data = json.load(f)

    print("=" * 80)
    print(f"GAME LOG: {data.get('game_id', 'Unknown')}")
    print("=" * 80)
    print(f"Started: {data.get('start_time', 'Unknown')}")
    print(f"Total Events: {data.get('total_events', len(data.get('events', [])))}")
    print()

    # Group events by round and phase
    current_round = 0
    current_phase = None

    for event in data.get('events', []):
        event_type = event.get('event_type')

        # Track round/phase changes
        if event_type == 'phase_transition':
            new_phase = event.get('new_phase', '?')
            old_phase = event.get('old_phase', '?')

            if new_phase == 'begin_round':
                current_round = event.get('round', current_round + 1)
                print()
                print("=" * 80)
                print(f"ROUND {current_round}")
                print("=" * 80)

            current_phase = new_phase
            print(f"\n--- Phase: {new_phase.upper().replace('_', ' ')} ---")

        # Game setup
        elif event_type == 'game_setup':
            print("\n🎮 GAME SETUP")
            print(f"  Players: {event.get('player_count', '?')}")
            print(f"  First Player: {event.get('first_player', '?')}")
            if 'objectives' in event:
                print(f"  Objectives distributed: {len(event['objectives'])}")

        # Player actions
        elif event_type == 'player_action':
            action_type = event.get('action_type', 'unknown')
            player_name = event.get('player_name', event.get('player_id', '?'))
            details = event.get('details', {})

            if action_type == 'place_agent':
                card = details.get('card', '?')
                location = details.get('location', '?')
                print(f"  🎯 {player_name}: Placed agent - {card} → {location}")

            elif action_type == 'reveal':
                persuasion = details.get('total_persuasion', 0)
                cards = details.get('cards_revealed', 0)
                print(f"  🃏 {player_name}: Revealed {cards} cards (persuasion: {persuasion})")

            elif action_type == 'acquire':
                card = details.get('card_acquired', '?')
                cost = details.get('cost', 0)
                print(f"  💰 {player_name}: Acquired {card} (cost: {cost})")

            elif action_type == 'combat':
                print(f"  ⚔️  {player_name}: Combat action")

            else:
                print(f"  ▪ {player_name}: {action_type}")

        # Bot decisions
        elif event_type == 'bot_decision':
            decision_type = event.get('decision_type', '?')
            player_name = event.get('player_name', '?')
            chosen = event.get('chosen', '?')
            # Only show for important decisions
            if decision_type == 'place_agent':
                print(f"  🤖 {player_name} chose: {chosen}")

        # Game state snapshots
        elif event_type == 'game_state_snapshot':
            round_num = event.get('round', '?')
            phase = event.get('phase', '?')
            players = event.get('players', [])

            if phase in ['recall', 'combat']:  # Show state at end of key phases
                print(f"\n  📊 Player Status (Round {round_num}, {phase}):")
                for p in players:
                    resources = p.get('resources', {})
                    print(f"    {p.get('name', '?')}: VP={p.get('vp', 0)} | "
                          f"Solari={resources.get('solari', 0)} "
                          f"Spice={resources.get('spice', 0)} "
                          f"Water={resources.get('water', 0)}")

        # Combat results
        elif event_type == 'combat_resolution':
            print(f"\n  ⚔️  COMBAT RESULTS:")
            winner = event.get('winner')
            if winner:
                print(f"    Winner: {winner.get('name', '?')} ({winner.get('strength', 0)} strength)")
            rankings = event.get('rankings', [])
            if rankings:
                print(f"    Rankings:")
                for i, rank in enumerate(rankings, 1):
                    print(f"      {i}. {rank.get('player_name', '?')} - {rank.get('strength', 0)} strength")

        # Game end
        elif event_type == 'game_end':
            print()
            print("=" * 80)
            print("🏁 GAME OVER")
            print("=" * 80)

            winner_data = event.get('winner')
            if winner_data:
                print(f"\n🏆 Winner: {winner_data.get('name', '?')} with {winner_data.get('vp', 0)} VP")

            final_scores = event.get('final_scores', [])
            if final_scores:
                print(f"\n📊 Final Scores:")
                for score in final_scores:
                    print(f"  {score.get('name', '?')}: {score.get('vp', 0)} VP "
                          f"(Spice: {score.get('spice', 0)})")

    print()
    print("=" * 80)
    print(f"Log file: {log_file}")
    print("=" * 80)


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # File specified via command line
        log_file = Path(sys.argv[1])
        if not log_file.exists():
            print(f"Error: File not found: {log_file}")
            sys.exit(1)
    else:
        # No file specified - show interactive chooser
        log_file = choose_log_interactive()
        print()

    display_game_log(log_file)


if __name__ == "__main__":
    main()
