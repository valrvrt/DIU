"""Debug why bots always reveal."""

from src.engine.core.game_setup import GameSetup
from src.engine.actions.action_generator import ActionGenerator

# Create game
game, setup_info = GameSetup.create_game(player_count=3, human_player_name="Test")

# Get first player
player = game.players[0]

print(f"Player: {player.name}")
print(f"Hand cards: {len(player.hand.cards)}")
for i, card in enumerate(player.hand.cards):
    print(f"  {i+1}. {card.name} (id: {card.id})")

print(f"\nAgents available: {player.agents_available}")
print(f"Has revealed: {player.has_revealed_this_round}")

# Check if we can get playable cards
action_gen = ActionGenerator(game, setup_info["phase_manager"])
playable = action_gen.get_playable_imperium_cards(player.player_id)

print(f"\nPlayable cards: {len(playable)}")
for card in playable:
    print(f"  - {card.name}")
    locations = action_gen.get_valid_locations_for_card(player.player_id, card)
    print(f"    Valid locations: {len(locations)}")
    for loc, ptype in locations[:3]:  # Show first 3
        print(f"      * {loc.name} ({ptype})")
