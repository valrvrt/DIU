"""
Improved play_game.py with better human interface.
This replaces the _human_turn methods with a comprehensive UI.
"""

# Copy the imports and bot/display classes from play_game.py, then add these methods to GameLoop:

def _human_turn(self, player_id: str):
    """Handle human player input with full information."""
    player = next(p for p in self.game.players if p.player_id == player_id)
    action_gen = self.managers["action_generator"]
    action_exec = self.managers["action_executor"]

    print(f"\n" + "="*70)
    print(f"👤 {player.name}'S TURN")
    print("="*70)

    if player.has_revealed_this_round:
        self._human_acquisition_phase(player_id, player, action_gen, action_exec)
    else:
        self._human_agent_phase(player_id, player, action_gen, action_exec)

def _human_agent_phase(self, player_id: str, player, action_gen, action_exec):
    """Handle human agent placement phase."""
    # Show hand
    print(f"\n📋 YOUR HAND ({len(player.hand.cards)} cards):")
    playable_cards = action_gen.get_playable_imperium_cards(player_id)

    for i, card in enumerate(player.hand.cards):
        playable = "✓" if card in playable_cards else "✗"
        agent_icons = ", ".join(card.agent_icons) if hasattr(card, 'agent_icons') and card.agent_icons else "none"
        print(f"  [{i+1}] {playable} {card.name} (icons: {agent_icons})")

    print(f"\n⚙️  AGENTS: {player.agents_available}/{player.total_available_agents} available")
    print(f"💰 RESOURCES: Solari:{player.solari} Spice:{player.spice} Water:{player.water}")

    print("\nOptions:")
    print("  [1-5] - Play card number")
    print("  [R]   - Reveal hand and end agent phase")
    print("  [skip] - Let bot play this turn")

    choice = input("\nYour choice: ").strip().lower()

    if choice == "skip":
        result = self.bot.take_turn(player_id, self.game)
        return

    if choice == "r":
        from src.engine.actions import RevealAction
        action = RevealAction(player_id=player_id)
        result = action_exec.execute_reveal(action)
        if result.get("success"):
            print(f"\n✓ Revealed hand! Persuasion: {result.get('total_persuasion', 0)}")
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(player.hand.cards):
            card = player.hand.cards[idx]
            if card not in playable_cards:
                print(f"\n✗ {card.name} cannot be played (no matching agent icons or no agents left)")
                self._human_agent_phase(player_id, player, action_gen, action_exec)
                return

            # Show valid locations
            locations = action_gen.get_valid_locations_for_card(player_id, card)
            if not locations:
                print(f"\n✗ No valid locations for {card.name}")
                self._human_agent_phase(player_id, player, action_gen, action_exec)
                return

            print(f"\n📍 Valid locations for {card.name}:")
            for i, (loc, ptype) in enumerate(locations):
                cost_str = ""
                if hasattr(loc, 'cost') and loc.cost:
                    costs = []
                    for c in loc.cost if isinstance(loc.cost, list) else []:
                        if isinstance(c, dict) and c.get("type") == "resource":
                            costs.append(f"{c['amount']} {c['resource']}")
                    cost_str = f" (cost: {', '.join(costs)})" if costs else ""

                print(f"  [{i+1}] {loc.name}{cost_str}")

            loc_choice = input("Choose location (number or 'back'): ").strip()
            if loc_choice == "back":
                self._human_agent_phase(player_id, player, action_gen, action_exec)
                return

            try:
                loc_idx = int(loc_choice) - 1
                if 0 <= loc_idx < len(locations):
                    location, placement_type = locations[loc_idx]

                    from src.engine.actions import PlaceAgentAction
                    action = PlaceAgentAction(
                        player_id=player_id,
                        card=card,
                        location=location,
                        placement_type=placement_type,
                        troops_to_deploy=0
                    )
                    result = action_exec.execute_place_agent(action)

                    if result.get("success"):
                        print(f"\n✓ Placed agent at {location.name}!")
                    else:
                        print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")
                else:
                    print("\n✗ Invalid location number")
                    self._human_agent_phase(player_id, player, action_gen, action_exec)
            except ValueError:
                print("\n✗ Invalid input")
                self._human_agent_phase(player_id, player, action_gen, action_exec)
        else:
            print("\n✗ Invalid card number")
            self._human_agent_phase(player_id, player, action_gen, action_exec)
    except ValueError:
        print("\n✗ Invalid input")
        self._human_agent_phase(player_id, player, action_gen, action_exec)

def _human_acquisition_phase(self, player_id: str, player, action_gen, action_exec):
    """Handle human card acquisition phase."""
    options = action_gen.get_acquisition_options(player_id)
    total_persuasion = options.get("total_persuasion", 0)

    print(f"\n💎 PERSUASION: {total_persuasion}")
    print(f"\n🛒 AVAILABLE CARDS:")

    affordable_cards = []
    imperium_row = options.get("imperium_row", [])

    for i, card in enumerate(imperium_row):
        affordable = card.cost <= total_persuasion
        marker = "✓" if affordable else "✗"
        print(f"  [{i+1}] {marker} {card.name} (Cost: {card.cost})")
        if affordable:
            affordable_cards.append((i, card, "imperium_row"))

    print("\nOptions:")
    if affordable_cards:
        print("  [1-6] - Buy card number")
    print("  [pass] - Pass (done buying)")
    print("  [skip] - Let bot decide")

    choice = input("\nYour choice: ").strip().lower()

    if choice == "pass":
        print("\n✓ Passed on buying cards")
        return

    if choice == "skip":
        result = self.bot._try_acquire_card(player_id, player.name)
        return

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(imperium_row):
            card = imperium_row[idx]
            if card.cost > total_persuasion:
                print(f"\n✗ Cannot afford {card.name} (need {card.cost}, have {total_persuasion})")
                self._human_acquisition_phase(player_id, player, action_gen, action_exec)
                return

            from src.engine.actions import AcquireCardAction
            action = AcquireCardAction(
                player_id=player_id,
                card=card,
                source="imperium_row"
            )
            result = action_exec.execute_acquire_card(action)

            if result.get("success"):
                print(f"\n✓ Acquired {card.name}!")
            else:
                print(f"\n✗ Failed: {result.get('error', 'Unknown error')}")
        else:
            print("\n✗ Invalid card number")
            self._human_acquisition_phase(player_id, player, action_gen, action_exec)
    except ValueError:
        print("\n✗ Invalid input")
        self._human_acquisition_phase(player_id, player, action_gen, action_exec)
