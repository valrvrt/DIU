"""
COMPREHENSIVE CARD TEST RUNNER
================================

This script runs the complete integration test suite for ALL cards in DUNE Imperium Uprising.

It tests:
- 60 Imperium cards (reveal, agent, on_acquire effects)
- 30+ Intrigue cards (plot, combat, endgame phases)
- 10 Conflict cards (1st, 2nd, 3rd place rewards)
- 6+ Contract cards (reward resolution)
- 8+ Leader cards (signet abilities)

Total: ~100+ cards with multiple effects each = 200+ individual tests

Usage:
    python test/comprehensive/run_comprehensive_tests.py

Output:
    - Detailed test results for each card
    - Summary statistics
    - List of any failing cards
"""

import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest


def run_comprehensive_tests():
    """Run all comprehensive card integration tests."""

    print("="*80)
    print("DUNE IMPERIUM UPRISING - COMPREHENSIVE CARD INTEGRATION TESTS")
    print("="*80)
    print()
    print("This test suite validates EVERY SINGLE CARD in the game by:")
    print("  1. Setting up a real game with board spaces and components")
    print("  2. Playing each card (placing agent or revealing)")
    print("  3. Resolving all card effects through the effect resolver")
    print("  4. Validating correct rewards and costs")
    print()
    print("Starting tests...")
    print("="*80)
    print()

    start_time = time.time()

    # Run pytest with specific configuration
    test_file = Path(__file__).parent / "test_complete_card_integration.py"

    # pytest arguments for detailed output
    args = [
        str(test_file),
        "-v",                    # Verbose
        "-s",                    # Show print statements
        "--tb=short",            # Short traceback format
        "--color=yes",           # Colored output
        "-W", "ignore::DeprecationWarning",  # Ignore deprecation warnings
    ]

    # Run tests
    exit_code = pytest.main(args)

    end_time = time.time()
    duration = end_time - start_time

    print()
    print("="*80)
    print(f"COMPREHENSIVE TEST SUITE COMPLETED IN {duration:.2f} seconds")
    print("="*80)

    if exit_code == 0:
        print()
        print("✅ ALL TESTS PASSED!")
        print()
        print("Every card in DUNE Imperium Uprising has been tested and works correctly:")
        print("  ✓ All Imperium cards (reveal, agent, on_acquire effects)")
        print("  ✓ All Intrigue cards (plot, combat, endgame phases)")
        print("  ✓ All Conflict cards (1st, 2nd, 3rd place rewards)")
        print("  ✓ All Contract cards (reward resolution)")
        print("  ✓ All Leader cards (signet abilities)")
        print()
        print("The game engine correctly handles all card effects and game state changes.")
        print()
    else:
        print()
        print("❌ SOME TESTS FAILED")
        print()
        print("Please review the output above to see which cards failed.")
        print("Failed tests indicate:")
        print("  - Card effect is not implemented correctly")
        print("  - Effect handler is missing")
        print("  - Card data format is incorrect")
        print()

    return exit_code


if __name__ == "__main__":
    exit_code = run_comprehensive_tests()
    sys.exit(exit_code)
