# Critical Bugs Found During Testing

## 1. ❌ Card Costs Show as 0
**Issue**: All imperium cards show Cost: 0 in acquisition phase
**Root Cause**: imperium.JSON is missing "cost" field for market cards
**Fix**: Need to add cost field to each card in imperium.JSON

Example:
```json
{
  "id": 7,
  "name": "Bene Gesserit Operative",
  "cost": 3,  // ADD THIS
  "agent_icon": "bene_gesserit",
  ...
}
```

## 2. ❌ Card Acquisition Fails
**Issue**: "✗ Failed: Unknown source: imperium_row"
**Root Cause**: AcquireCardAction expects different source format
**Fix**: Check action_executor.py to see what source format is expected

## 3. ❌ No Agents Available After Round 1
**Issue**: All cards show ✗ (not playable) in round 2
**Root Cause**: Agents might not be properly recalled, OR board spaces not reset
**Fix**: Check if board spaces are being cleared between rounds

## 4. ❌ No Effect Feedback
**Issue**: Player places agent but doesn't see what they gained
**Fix**: Add effect resolution feedback to human turn display:
```
✓ Placed agent at Fremkit!
  → Drew 1 card (now 6 cards in hand)
  → Gained 1 Fremen influence (now 1/4 for alliance)
```

## 5. ❌ No Auto-Reveal
**Issue**: Player with 0 agents still asked to choose action
**Fix**: Auto-reveal if agents_available == 0

## 6. ❌ Missing Combat Info
**Issue**: No combat strength display, no troop deployment choice
**Fix**:
- Add combat tracker to UI
- Ask about troop deployment when placing on combat space

## 7. ❌ No Reveal Preview
**Issue**: Player doesn't know what revealing will give
**Fix**: Show persuasion/swords totals before revealing

## 8. ⚠️ Steal Intrigue - Incomplete
**Current**: Basic steal implemented
**Missing**: Player choice (which opponent to steal from)
**Fix**: Add player selection when multiple opponents have 4+ intrigue cards

## 9. ⚠️ Council Seat - Not Tracked
**Current**: council_seat effect exists
**Missing**: Persistent tracking on player
**Fix**: Add `has_council_seat` boolean to Player model

## 10. ⚠️ Recall Agent - Needs Clarification
**Current**: Recall effect exists
**Issue**: "Recall agent from previous turn" - need to track where agents were placed
**Fix**: Track agent placements per turn, allow recall from previous locations

## Priority Order

### Critical (Blocks Gameplay):
1. Fix card costs (imperium.JSON needs cost field)
2. Fix card acquisition error
3. Fix agents not available in round 2

### High (Poor UX):
4. Add effect feedback
5. Auto-reveal when no agents
6. Show combat info

### Medium (Missing Mechanics):
7. Combat troop deployment
8. Reveal preview
9. Steal player choice

### Low (Advanced Features):
10. Council seat tracking
11. Recall from previous turn

## Quick Wins

The fastest fixes:
1. Add costs to imperium.JSON (manual data entry)
2. Fix source parameter in acquisition (code fix)
3. Add effect feedback text (UI improvement)
