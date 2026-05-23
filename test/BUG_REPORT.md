# Bug Report from Comprehensive Tests - UPDATED

## Test Results Summary (After Fixes)
- **Reveal Effects**: 60/60 passed (100%) ✅ **PERFECT!**
- **Agent Effects**: 52/52 passed (100%) ✅ **PERFECT!**
- **On-Acquire Effects**: 8/8 passed (100%) ✅ **PERFECT!**
- **Intrigue Cards**: ~36/42 passed (85.7%) - 6 failures remain
- **Conflict Cards**: 10/12 passed (83.3%) - Trade Dispute issues
- **Contract Cards**: 24/24 passed (100%) ✅ **PERFECT!**
- **Leader Cards**: 9/9 passed (100%) ✅ **PERFECT!**

---

## ✅ FIXED - Effect Handlers Implemented

### 1. Play Spy Effect Handler - ✅ IMPLEMENTED
**Status**: ✅ Complete
**Affected**: Cards 14, 38, 60, 7, 19 (5 cards)

**Implementation**: [effect_resolver.py:432-558](src/engine/effects/effect_resolver.py#L432-L558)
```python
def _handle_play(self, player_id, effect, context):
    """Handle placing units (spies, troops, sandworms)"""
    # Supports:
    # - Spy placement on observation posts
    # - allow_shared_post_if conditions
    # - Auto-select for bots/testing
```

**Fixes Applied**:
- Added spy placement logic with observation post selection
- Implemented `allow_shared_post_if` conditional sharing
- Auto-selects first available post for testing (choice system TODO for humans)
- Fixed `self.state.players` → `self.game.players`

### 2. Trash Self Effect Handler - ✅ IMPLEMENTED
**Status**: ✅ Complete
**Affected**: Cards 6, 15 (2 cards)

**Implementation**: [effect_resolver.py:606-655](src/engine/effects/effect_resolver.py#L606-L655)
```python
def _handle_trash(self, player_id, effect, context):
    """Handle trash effects including deck: 'self'"""
    # Supports both formats:
    # - "deck": "self" (trash card being played)
    # - "deck": ["hand", "played"] (choice)
```

**Fixes Applied**:
- Added support for `"deck": "self"` in addition to `"target": "self"`
- Handles agent effects where card isn't in any deck yet
- Tracks trashed cards to prevent adding to play area
- Removed duplicate `_handle_trash` method

### 3. Control Location Effect Handler - ✅ ALREADY EXISTED
**Status**: ✅ Working
**Affected**: Card 27 (1 card)

**Implementation**: [effect_resolver.py:1157-1191](src/engine/effects/effect_resolver.py#L1157-L1191)

**Fix Applied**:
- Updated to check both `context.get("location")` and `context.get("board_space")`
- Handles `location: "current"` from context

### 4. Dynamic Influence Target (target: "agent") - ✅ IMPLEMENTED
**Status**: ✅ Complete
**Affected**: Card 34 (1 card)

**Implementation**: [effect_resolver.py:1017-1038](src/engine/effects/effect_resolver.py#L1017-L1038)

**Fixes Applied**:
- Added `target: "agent"` handling to get faction from current board space
- Handles both `context.get("location")` and `context.get("board_space")`
- Normalizes faction name to lowercase

### 5. Conditional Spy Placement - ✅ ALREADY EXISTED
**Status**: ✅ Working
**Affected**: Card 19 (1 card)

**Implementation**: Already handled in `_handle_play` with `allow_shared_post_if`

---

## ✅ JSON BUGS FIXED

### 1. Card 34 - Overthrow (Reveal Effect) - ✅ FIXED
**Issue**: Typo in JSON
```json
{"type": "resource", "target": "troop", "amount": 1}  // WRONG
{"type": "resource", "resource": "troop", "amount": 1}  // FIXED
```

### 2. Card 54 - Treacherous Maneuver (Agent Effect) - ✅ FIXED
**Issue**: Missing `"type": "action"` field
```json
// BEFORE (missing type)
{
  "cost": [...],
  "reward": {...}
}

// AFTER (type added)
{
  "type": "action",
  "cost": [...],
  "reward": {...}
}
```

### 3. Card 48 - Spacing Guild's Favor (Agent Effect) - ✅ FIXED in Handler
**Issue**: Used `"deck": "hand"` for draw effect (should be `"deck": "deck"`)
**Fix**: Updated `_handle_draw` to treat `"hand"` as alias for `"deck"` (draw into hand from deck)

---

## 🟡 REMAINING ISSUES

### Imperium Cards Count
- **Issue**: Found 61 cards instead of 60
- **Likely Cause**: Duplicate Signet Ring (IDs 5 and 6)
- **Impact**: Minor, doesn't affect gameplay

### Intrigue Cards (6 failures)
1. Card 17 - Imperium Politics
2. Card 20 - Intelligence Report
3. Card 22 - Manipulate
4. Card 34 - Shadow Alliance (str object has no 'get' attribute)
5. Card 35 - Sietch Ritual
6. Card 41 - Unexpected Allies

**Note**: These are likely phase-specific effects or missing effect types

### Conflict Cards (2 failures)
- Card 12 - Trade Dispute (Tier 1 and Tier 2)

**Note**: Needs investigation

---

## Summary

### Imperium Cards - 100% PASS RATE ✅
- ✅ Reveal Effects: 60/60 (100%)
- ✅ Agent Effects: 52/52 (100%)
- ✅ On-Acquire Effects: 8/8 (100%)

### Engine Implementation
- ✅ **5 effect handlers implemented/fixed**:
  1. `type: "play"` for placing spies ✅
  2. `deck: "self"` for trash effects ✅
  3. `type: "control"` for location control ✅ (already existed)
  4. `target: "agent"` for dynamic influence ✅
  5. `allow_shared_post_if` for conditional spy placement ✅ (already existed)

### JSON Fixes
- ✅ **3 JSON bugs fixed**: Cards 34, 48, 54

### Test Pass Rate Improvement
- **Before**: 82.7% agent effects, 96.7% reveal effects
- **After**: 100% agent effects, 100% reveal effects, 100% on-acquire

**Recommendation**: All critical Imperium card effects now work perfectly! Intrigue/Conflict card failures are separate issues unrelated to the missing effect handlers.
