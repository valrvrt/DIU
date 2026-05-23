# Interactive Agent Placement - Step-by-Step Guide

## The New Way: Interactive & Realistic

Agent placement now works **exactly like the real game** with full player control at each step.

---

## The Flow (5 Steps)

### Step 1: Choose Your Card

```bash
god> /hand
YOUR HAND
  1. Leadership
  2. Desert Power
  3. Hidden Missive

god> /play 1
```

**What Happens:**
- Shows card's agent icon
- Shows card's agent effects
- Shows ALL valid board spaces for this card
- Each space shows its effects

**Example Output:**
```
🎴 Selected card: Leadership
Agent icon: agent

Card agent effects:
  [1] Gain 2 persuasion
  [2] Gain 1 swords

================================================================================
AVAILABLE BOARD SPACES
================================================================================

  [ 5] Foldspace
      Location effects:
        [1] Gain 5 solari
        [2] Gain 1 spacing_guild influence

  [10] Conspiracy
      Location effects:
        [1] Draw 1 card(s) from intrigue
        [2] Gain 1 emperor influence

Type: /go <space_id> to place your agent
================================================================================
```

---

### Step 2: Choose Your Location

```bash
god> /go 5
```

**What Happens:**
- Shows ALL effects from card + location
- Asks you to choose resolution order
- Or use `/auto` for default order

**Example Output:**
```
🎯 Placing agent at: Foldspace
   Using card: Leadership
--------------------------------------------------------------------------------

📋 All available effects:
  [1] [CARD    ] Gain 2 persuasion
  [2] [CARD    ] Gain 1 swords
  [3] [LOCATION] Gain 5 solari
  [4] [LOCATION] Gain 1 spacing_guild influence

================================================================================
Choose effect resolution order:
  /order 1,2,3,4  - Resolve in this order
  /auto           - Auto-resolve in default order
================================================================================
```

---

### Step 3: Choose Effect Order

**Option A: Custom Order**
```bash
god> /order 3,1,4,2
```
Resolves: Location solari → Card persuasion → Location influence → Card swords

**Option B: Auto Order**
```bash
god> /auto
```
Resolves effects in the order shown (1, 2, 3, 4)

**What Happens:**
- Effects resolve in your chosen order
- Each effect shows if it succeeded
- If combat space, asks about troop deployment
- Otherwise, finalizes placement

**Example Output:**
```
📊 Resolving effects in your chosen order:
--------------------------------------------------------------------------------

[1] Resolving: [LOCATION] Gain 5 solari
    ✓ Resolved

[2] Resolving: [CARD] Gain 2 persuasion
    ✓ Resolved

[3] Resolving: [LOCATION] Gain 1 spacing_guild influence
    ✓ Resolved

[4] Resolving: [CARD] Gain 1 swords
    ✓ Resolved
```

---

### Step 4: Deploy Troops (Combat Spaces Only)

If the space is a combat space (⚔️), you'll see:

```
================================================================================
⚔️  COMBAT SPACE - TROOP DEPLOYMENT
================================================================================

You have 20 troops in garrison
Currently in conflict: 0 troops

How many troops do you want to deploy?
  /deploy <amount>  - Deploy troops
  /deploy 0         - Deploy no troops
================================================================================
```

**Your Choice:**
```bash
god> /deploy 5
```

---

### Step 5: Completion (Automatic)

**Output:**
```
================================================================================
✅ AGENT PLACEMENT COMPLETE
================================================================================

🎴 Card played: Leadership
🎯 Location: Foldspace
📊 Effects resolved: 4
⚔️  Troops deployed: 0

📊 Resources:
  Solari: 1004
  Spice:  999
  Water:  999
  VP:     0
  ...
```

---

## Complete Example: Combat Turn

```bash
# 1. Choose card
god> /spawn long live the fighters
god> /play 1

🎴 Selected card: Long Live the Fighters
Agent icon: fremen

Card agent effects:
  [1] Gain 1 troop

AVAILABLE BOARD SPACES:
  [ 1] Fremkit ⚔️
      Location effects:
        [1] Draw 1 card(s) from deck
        [2] Gain 1 fremen influence

  [ 2] Desert Tactics ⚔️  (Cost: 1 water)
      Location effects:
        [1] Gain 1 troop
        [2] Trash 1 card(s)
        [3] Gain 1 fremen influence

# 2. Choose location
god> /go 1

📋 All available effects:
  [1] [CARD    ] Gain 1 troop
  [2] [LOCATION] Draw 1 card(s) from deck
  [3] [LOCATION] Gain 1 fremen influence

# 3. I want card draw first, then troops, then influence
god> /order 2,1,3

📊 Resolving effects in your chosen order:
[1] Resolving: [LOCATION] Draw 1 card(s) from deck
    ✓ Resolved
[2] Resolving: [CARD] Gain 1 troop
    ✓ Resolved
[3] Resolving: [LOCATION] Gain 1 fremen influence
    ✓ Resolved

# 4. Deploy troops
⚔️  COMBAT SPACE - TROOP DEPLOYMENT

You have 21 troops in garrison
Currently in conflict: 0 troops

god> /deploy 5

# 5. Done!
✅ AGENT PLACEMENT COMPLETE

🎴 Card played: Long Live the Fighters
🎯 Location: Fremkit
📊 Effects resolved: 3
⚔️  Troops deployed: 5
```

---

## Example: Multiple Effects with Strategy

### Scenario: Want persuasion before drawing

```bash
god> /spawn hidden missive
god> /play 1

Card agent effects:
  [1] Draw 1 card(s) from deck
  [2] Gain 1 troop

god> /go 3  # Secrets

📋 All available effects:
  [1] [CARD    ] Draw 1 card(s) from deck
  [2] [CARD    ] Gain 1 troop
  [3] [LOCATION] Draw 1 card(s) from intrigue
  [4] [LOCATION] Steal 1 card(s) from intrigue
  [5] [LOCATION] Gain 1 bene_gesserit influence

# I want troops first (might help with card conditions)
# Then steal before drawing (get opponent's good card)
# Then draws, then influence
god> /order 2,4,1,3,5

📊 Resolving effects in your chosen order:
[1] Resolving: [CARD] Gain 1 troop
    ✓ Resolved
[2] Resolving: [LOCATION] Steal 1 card(s) from intrigue
    ✓ Resolved
[3] Resolving: [CARD] Draw 1 card(s) from deck
    ✓ Resolved
[4] Resolving: [LOCATION] Draw 1 card(s) from intrigue
    ✓ Resolved
[5] Resolving: [LOCATION] Gain 1 bene_gesserit influence
    ✓ Resolved

✅ AGENT PLACEMENT COMPLETE
```

---

## Why This Matters

### Real Game Rules
- ✅ You choose card first
- ✅ You see valid spaces based on agent icon
- ✅ You choose effect resolution order
- ✅ You decide troop deployment
- ✅ Costs paid automatically

### Strategic Depth
- Order matters for cards with conditions
- Troop deployment affects combat math
- Resource gains can enable other actions
- Card draws might give you better options

### Full Control
- See all effects before committing
- Choose optimal resolution order
- Decide exact troop deployment
- Experiment with different strategies

---

## Quick Commands Reference

```bash
/play <card#>      # Step 1: Choose card
/go <space#>       # Step 2: Choose space
/order 1,2,3,...   # Step 3: Custom order
/auto              # Step 3: Auto order
/deploy <amount>   # Step 4: Deploy troops
```

---

## Tips

### See All Options First
```bash
/play 1            # See all valid spaces
# Review options before choosing
/go 5              # Pick the best one
```

### Use Auto for Simple Placements
```bash
/play 1
/go 5
/auto              # Quick resolution
```

### Strategic Ordering
```bash
# Get resources before drawing (might need them)
/order 3,1,2

# Get influence before troops (alliance bonus?)
/order 4,1,2,3
```

### Test Different Approaches
```bash
# Try one way
/play 1
/go 5
/order 1,2,3

# Reset and try another
/clear
/play 1
/go 10
/order 3,2,1
```

---

## Old Commands Still Work

### Quick Resource Management
```bash
/give spice 10
/take water 5
/inf fremen 2
```

### Reveal & Combat
```bash
/reveal            # Reveal hand
/deploy 5          # Manual troop deployment
/retreat 2         # Retreat troops
/combat            # Calculate strength
```

### Board View
```bash
/board             # All spaces
/board fremen      # Filter by faction
```

---

**This is how the real game works!** 🎮

Every decision matters. Every order counts. Test strategies, learn combos, master the game!
