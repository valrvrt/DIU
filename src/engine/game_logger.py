"""
Game Logger - Comprehensive logging system for game analysis.

Logs all actions, effects, phase transitions, and decisions to a JSON file
for post-game review and debugging.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class GameLogger:
    """
    Logs all game events to a structured JSON file.

    Each event is timestamped and categorized for easy analysis.
    """

    def __init__(self, game_id: str = None, output_dir: str = "game_logs"):
        """
        Initialize the game logger.

        Args:
            game_id: Unique identifier for this game (auto-generated if None)
            output_dir: Directory to save log files
        """
        if game_id is None:
            game_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.game_id = game_id
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.log_file = self.output_dir / f"game_{game_id}.json"

        # In-memory log entries
        self.entries: List[Dict[str, Any]] = []

        # Initialize log file
        self._write_header()

    def _write_header(self):
        """Write initial game metadata."""
        self.log({
            "event_type": "game_start",
            "game_id": self.game_id,
            "timestamp": datetime.now().isoformat()
        })

    def log(self, event: Dict[str, Any]):
        """
        Log an event.

        Args:
            event: Event data (must include 'event_type')
        """
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.now().isoformat()

        # Add to in-memory log
        self.entries.append(event)

        # Append to file (incremental write for crash safety)
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump({
                "game_id": self.game_id,
                "events": self.entries
            }, f, indent=2, default=str)

    # ==================== CONVENIENCE METHODS ====================

    def log_phase_transition(self, old_phase: str, new_phase: str, round_num: int):
        """Log a phase transition."""
        self.log({
            "event_type": "phase_transition",
            "old_phase": old_phase,
            "new_phase": new_phase,
            "round": round_num
        })

    def log_player_action(self, player_id: str, player_name: str, action_type: str, details: Dict[str, Any]):
        """Log a player action."""
        self.log({
            "event_type": "player_action",
            "player_id": player_id,
            "player_name": player_name,
            "action_type": action_type,
            "details": details
        })

    def log_effect_resolution(self, player_id: str, effects: List[Dict[str, Any]], context: Dict[str, Any]):
        """Log effect resolution."""
        self.log({
            "event_type": "effect_resolution",
            "player_id": player_id,
            "effects": effects,
            "context": context
        })

    def log_combat_result(self, rankings: Dict[int, List[str]], winner: str = None, conflict_name: str = None):
        """Log combat results."""
        self.log({
            "event_type": "combat_result",
            "conflict_name": conflict_name,
            "rankings": rankings,
            "winner": winner
        })

    def log_resource_change(self, player_id: str, player_name: str, resource: str, old_value: int, new_value: int, reason: str):
        """Log resource changes."""
        self.log({
            "event_type": "resource_change",
            "player_id": player_id,
            "player_name": player_name,
            "resource": resource,
            "old_value": old_value,
            "new_value": new_value,
            "change": new_value - old_value,
            "reason": reason
        })

    def log_vp_gain(self, player_id: str, player_name: str, amount: int, source: str, details: Dict[str, Any] = None):
        """Log victory point gains."""
        self.log({
            "event_type": "vp_gain",
            "player_id": player_id,
            "player_name": player_name,
            "amount": amount,
            "source": source,
            "details": details or {}
        })

    def log_alliance_change(self, player_id: str, player_name: str, faction: str, gained: bool):
        """Log alliance gains/losses."""
        self.log({
            "event_type": "alliance_change",
            "player_id": player_id,
            "player_name": player_name,
            "faction": faction,
            "gained": gained
        })

    def log_card_acquisition(self, player_id: str, player_name: str, card_name: str, cost: int, source: str):
        """Log card acquisitions."""
        self.log({
            "event_type": "card_acquisition",
            "player_id": player_id,
            "player_name": player_name,
            "card_name": card_name,
            "cost": cost,
            "source": source
        })

    def log_game_state_snapshot(self, round_num: int, phase: str, players_state: List[Dict[str, Any]]):
        """Log complete game state snapshot."""
        self.log({
            "event_type": "game_state_snapshot",
            "round": round_num,
            "phase": phase,
            "players": players_state
        })

    def log_game_end(self, winner: Dict[str, Any], final_scores: List[Dict[str, Any]]):
        """Log game end with final results."""
        self.log({
            "event_type": "game_end",
            "winner": winner,
            "final_scores": final_scores
        })

    def log_bot_decision(self, player_id: str, player_name: str, decision_type: str, options: List[Any], chosen: Any, reasoning: str = None):
        """Log bot AI decisions."""
        self.log({
            "event_type": "bot_decision",
            "player_id": player_id,
            "player_name": player_name,
            "decision_type": decision_type,
            "options": options,
            "chosen": chosen,
            "reasoning": reasoning
        })

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the logged game.

        Returns:
            Summary statistics
        """
        total_events = len(self.entries)
        event_counts = {}

        for entry in self.entries:
            event_type = entry.get("event_type", "unknown")
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        return {
            "game_id": self.game_id,
            "total_events": total_events,
            "event_counts": event_counts,
            "log_file": str(self.log_file)
        }

    def print_summary(self):
        """Print a human-readable summary."""
        summary = self.get_summary()

        print("\n" + "="*70)
        print("GAME LOG SUMMARY")
        print("="*70)
        print(f"Game ID: {summary['game_id']}")
        print(f"Total Events: {summary['total_events']}")
        print(f"Log File: {summary['log_file']}")
        print("\nEvent Breakdown:")
        for event_type, count in sorted(summary['event_counts'].items()):
            print(f"  {event_type}: {count}")
        print("="*70)
