# Comprehensive Card Integration Tests

## Overview

This test suite provides **complete integration testing** for every single card in DUNE Imperium Uprising. Unlike unit tests that test individual components in isolation, these tests validate that cards work correctly in real gameplay scenarios with a fully set up game board.

## What This Tests

### 🃏 Imperium Cards (60 cards)
- **Reveal Effects**: Resources, persuasion, swords, card draws
- **Agent Effects**: Effects when placing an agent at a board location
- **On-Acquire Effects**: Effects when buying the card from the imperium row

### 🎭 Intrigue Cards (30+ cards)
- **Plot Phase Effects**: Effects during the plot phase
- **Combat Phase Effects**: Effects during combat
- **Endgame Effects**: Victory point conditions

### ⚔️ Conflict Cards (10 cards)
- **1st Place Rewards**: Top combat position rewards
- **2nd Place Rewards**: Second position rewards
- **3rd Place Rewards**: Third position rewards

### 📜 Contract Cards (6+ cards)
- **Reward Resolution**: Effects when contract completes
- **Check Validation**: Contract completion conditions

### 👑 Leader Cards (8+ cards)
- **Signet Abilities**: Each leader's unique signet power

## How It Works

Each test follows this pattern:

```python
1. Set up a complete game with GameSetup.create_game()
   - Creates players with starting decks
   - Initializes board spaces
   - Sets up imperium row, conflict deck, intrigue deck, etc.

2. Load card data from JSON files
   - imperium.JSON
   - intrigue.JSON
   - conflicts.JSON
   - contracts.JSON
   - leaders.JSON

3. For each card:
   a. Snapshot player state (resources, troops, influence, etc.)
   b. Resolve card effects through EffectResolver
   c. Snapshot player state again
   d. Calculate changes and verify correctness

4. Report results:
   - ✓ Pass: Effect resolved successfully
   - ✗ Fail: Effect failed or threw exception
```

## Running the Tests

### Quick Start

```bash
# From project root
python test/comprehensive/run_comprehensive_tests.py
```

### Using pytest directly

```bash
# Run all comprehensive tests
pytest test/comprehensive/test_complete_card_integration.py -v -s

# Run specific test class
pytest test/comprehensive/test_complete_card_integration.py::TestAllImperiumCards -v -s

# Run specific test method
pytest test/comprehensive/test_complete_card_integration.py::TestAllImperiumCards::test_all_reveal_effects -v -s
```

### Test Output

The tests produce detailed output showing:

```
===============================================================================
TESTING ALL IMPERIUM CARD REVEAL EFFECTS
===============================================================================
  [ 1] Reconnaissance                           ✓ (no changes)
  [ 2] Convincing Argument                      ✓ (no changes)
  [ 3] Dagger                                   ✓ (no changes)
  [ 4] Diplomacy                                ✓ (no changes)
  [ 5] Dune, the Desert Planet                 ✓ (no changes)
  [ 6] Seek Allies                              ✓ (no changes)
  [ 7] Bene Gesserit Operative                  ✓ (intrigue_cards:+1)
  [ 8] Branching Paths                          ✓ (spice:+2)
  ...

Results: 60/60 passed
```

## Test Structure

```
test/comprehensive/
├── README.md                           # This file
├── run_comprehensive_tests.py          # Test runner script
└── test_complete_card_integration.py   # Main test file
    ├── TestHelper                      # Helper utilities
    ├── TestAllImperiumCards            # Imperium card tests
    ├── TestAllIntrigueCards            # Intrigue card tests
    ├── TestAllConflictCards            # Conflict card tests
    ├── TestAllContractCards            # Contract card tests
    └── TestAllLeaderCards              # Leader card tests
```

## Understanding Test Results

### ✓ Passed Tests
A test passes when:
- The effect resolves without exceptions
- Result has `success: True` OR `choices_required` (for choice effects)
- Player state changes appropriately (shown in parentheses)

### ✗ Failed Tests
A test fails when:
- Effect throws an exception
- Result has `success: False` and no choices required
- Card data is malformed
- Effect handler is not implemented

### Common Failure Reasons

1. **Missing Effect Handler**: Effect type not registered in EffectResolver
2. **Incorrect Card Data**: JSON format doesn't match expected structure
3. **Missing Dependencies**: Effect requires game state that wasn't set up
4. **Logic Error**: Bug in effect handler implementation

## Extending the Tests

### Adding New Card Type Tests

```python
class TestNewCardType:
    """Test every NewCardType card in the game."""

    @pytest.fixture
    def card_data(self):
        """Load all cards of this type."""
        return TestHelper.load_card_data("newcardtype.JSON")

    def test_all_effects(self, card_data):
        """Test all effects for this card type."""
        for card in card_data:
            game, player, state, resolver = TestHelper.setup_test_game()
            # ... test logic
```

### Adding Custom Assertions

```python
# Snapshot states
before = TestHelper.snapshot_player_state(player)
result = resolver.resolve_effects(player_id, effects, context)
after = TestHelper.snapshot_player_state(player)

# Custom assertions
changes = TestHelper.compare_states(before, after)
assert changes['solari'] == 5, "Expected to gain 5 solari"
assert changes['spice'] == -2, "Expected to spend 2 spice"
```

## Benefits of This Test Suite

1. **Comprehensive Coverage**: Tests every card in the game
2. **Real Game Scenarios**: Uses actual game setup, not mocks
3. **Catches Integration Issues**: Finds problems that unit tests miss
4. **Regression Prevention**: Ensures changes don't break existing cards
5. **Documentation**: Test output shows what each card does
6. **Fast Feedback**: Runs in seconds, suitable for CI/CD

## Continuous Integration

This test suite is designed to run in CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Run Comprehensive Card Tests
  run: python test/comprehensive/run_comprehensive_tests.py
```

## Troubleshooting

### "Module not found" errors
```bash
# Make sure to run from project root
cd /path/to/DUNE\ Imperium\ Uprising
python test/comprehensive/run_comprehensive_tests.py
```

### Test takes too long
```bash
# Run specific test class
pytest test/comprehensive/test_complete_card_integration.py::TestAllImperiumCards -v
```

### Need more detail on failures
```bash
# Use full traceback
pytest test/comprehensive/test_complete_card_integration.py -v -s --tb=long
```

## Future Enhancements

Potential additions to this test suite:

- [ ] Board space effect testing
- [ ] Full turn flow integration tests
- [ ] Multi-player interaction tests
- [ ] Combat resolution tests
- [ ] Alliance and influence milestone tests
- [ ] Endgame condition tests
- [ ] Performance benchmarking

## Contributing

When adding new cards to the game:

1. Add card data to appropriate JSON file
2. Run this test suite to verify it works
3. Fix any failures before committing
4. Ensure all tests pass in CI

## License

Part of the DUNE Imperium Uprising project.
