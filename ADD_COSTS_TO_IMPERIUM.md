# CRITICAL: Add Costs to imperium.JSON

Every imperium card (except starters) needs a "cost" field added.

## Reference Costs (from Dune Imperium board game):

### Cost 3:
- Bene Gesserit Operative
- Branching Paths
- Calculus of Power
- Most basic faction cards

### Cost 4-5:
- Captured Mentat: 5
- More powerful cards

## How to Fix:

Edit data/imperium.JSON and add cost to each card:

```json
{
  "id": 7,
  "name": "Bene Gesserit Operative",
  "cost": 3,  // ADD THIS LINE
  "agent_icon": "bene_gesserit",
  "amount": 3,
  ...
}
```

**DO NOT** add cost to starter cards (they already have "starting_deck": true)

## Starter Cards (skip these):
1. Reconnaissance
2. Convincing Argument
3. Dagger
4. Diplomacy
5. Dune, the Desert Planet
6. Seek Allies
7. Signet Ring

## Market Cards (need cost):
8. Bene Gesserit Operative
9. Branching Paths
10. Calculus of Power
11. Captured Mentat

Add appropriate costs (3-8) based on card power.
