# Expeditions Specification Review

**Date:** 2025-12-08
**Reviewer:** Claude Code Analysis

This document identifies missing elements, edge cases, and architectural concerns in the Expeditions specification.

---

## Critical Missing Elements

### 1. Expedition State/Progress Tracking

**Problem:** No mechanism to track where the user currently is in the expedition.

**Important Context:** Expeditions are non-linear graphs where you navigate between routes via links. You can:
- Jump from Route A jump 20 → Route B jump 5 (via link)
- Continue B5 → B10
- Jump from Route B jump 10 → Route A jump 22 (via link)
- Continue A22 → A40 (end)

**Key Insight:** You don't "complete" routes sequentially. Routes are reusable path segments that you navigate between. You might visit parts of the same route multiple times, or only use portions of routes.

**Example Pattern (Spansh exact-plotter style):**
- Main route: Sagittarius A* → Sol (500 jumps)
- Detour routes: Short excursions that branch off and rejoin main route
- Your path: Main[1-50] → Detour1[complete] → Main[100-150] → Detour2[10-20] → Main[200-end]

**Missing:**
- Current position (route ID + jump index)
- Path history through the graph (which links you've traversed)
- Total stats along YOUR actual path (not sum of all routes)
- Which link to take next (if multiple options)
- Elapsed time vs estimated remaining time

**Suggested Addition:**
```python
expedition_state = {
    # Current position
    "current_route_id": "uuid_A",
    "current_jump_index": 22,
    "current_system": {
        "name": "Sol",
        "id": 12345,
    },

    # Path history (the actual path taken through the graph)
    "path_history": [
        {
            "route_id": "uuid_A",
            "entry_jump": 0,      # Started at A0
            "exit_jump": 20,      # Exited at A20
            "link_id": "link_1",  # Used link_1 to leave
        },
        {
            "route_id": "uuid_B",
            "entry_jump": 5,      # Entered at B5 (from link_1)
            "exit_jump": 10,      # Exited at B10
            "link_id": "link_2",  # Used link_2 to leave
        },
        {
            "route_id": "uuid_A",
            "entry_jump": 22,     # Entered at A22 (from link_2)
            "exit_jump": None,    # Currently here, not exited yet
            "link_id": None,
        }
    ],

    # Aggregate stats along YOUR path
    "stats": {
        "total_jumps_completed": 42,
        "total_distance_ly": 15234.5,
        "neutron_boosts_used": 8,
        "refuel_stops": 12,
    },

    # Timing
    "started_at": "2025-12-08T10:00:00Z",
    "paused_at": None,  # If paused
    "resumed_at": None,
    "estimated_remaining_jumps": 85,  # Based on path from current position

    # Next decision point (if at a link)
    "at_link": False,  # True if current system has multiple link options
    "available_links": [],  # List of link IDs you can take from current position
}
```

**Progress Calculation:**
Progress is NOT "completed routes / total routes". Instead:
1. Calculate total jumps along the intended path through the graph
2. Track jumps completed along that path
3. Progress = jumps_completed / total_jumps_on_path

**Example:**
- Path: A[0-20] → B[5-10] → A[22-40]
- Total jumps: 20 + 5 + 18 = 43 jumps
- Completed: Currently at A22, so 20 + 5 + 0 = 25 jumps
- Progress: 25/43 = 58%

---

### 2. Integration with Journal Events ⭐ **KILLER FEATURE**

**Problem:** No specification for how expeditions sync with Elite Dangerous journal.

**Critical Feature (User Requirement):**
> "I want the application to automatically copy the next system in our expedition to your clipboard so you don't have to leave the game to get it."

**This is the main point of the feature!** Stay in-game, paste system name into galaxy map, jump, repeat.

**Core Workflow:**
1. User jumps (FSDJump event detected)
2. EDXD updates expedition state (current position advances)
3. **EDXD automatically copies next system name to clipboard**
4. User pastes into galaxy map in-game (no alt-tab needed)
5. Repeat

**Missing Specifications:**

**Auto-Copy Behavior:**
- When to copy? (immediately after FSDJump? On arrival?)
- What to copy? (just system name, or formatted string?)
- What if at link system? (multiple next options)
- What if no next system? (end of route segment)

**Link Detection:**
- When arriving at system with link(s), what happens?
  - Copy next system on current route?
  - Pause and wait for user to choose link?
  - Auto-decide based on planned_path?
  - Show notification in EDXD UI?

**Deviation Handling:**
- If user jumps to system NOT in expedition:
  - Try to find system in any route and auto-switch?
  - Mark as deviation, continue from original position?
  - Stop auto-copying until back on track?

**State Management:**
- Auto-advance position in expedition
- Update path_history
- Track stats (jumps, distance, fuel used)
- Detect link traversals

**Suggested Addition:**
```python
expedition = {
    # ... existing fields ...

    "journal_integration": {
        "auto_advance": True,  # Advance on FSDJump
        "auto_copy_next": True,  # Copy next system to clipboard
        "auto_copy_format": "{system_name}",  # Or custom format

        # Link behavior
        "pause_at_links": True,  # Stop auto-copy, wait for user choice
        "link_notification": True,  # Show UI notification at links

        # Deviation behavior
        "track_deviations": True,
        "auto_recover": False,  # Try to find system in routes

        "last_synced_event": "2025-12-08T10:00:00Z",
        "last_system": "Sol",
        "last_system_id": 12345,
    }
}
```

**Implementation Note (User):**
> "The specific implementation details can be defined later, I'm certain it will be possible, probably trivial."

**Design Decisions (User Answers):**

1. **Copy timing:** ⚠️ **OPEN QUESTION**
   - **Likely:** Option A (immediately after FSDJump) - no practical difference from arrival
   - **Note:** Might be smarter timing to discover, may become a user setting
   - **Decision:** Leave flexible for now, implement what works best

2. **Link arrival:** ✅ **DECIDED - NO AMBIGUITY ALLOWED**
   - **Critical:** Multiple link options at same system are **NOT ALLOWED** when creating expedition
   - **Reason:** Keep it simple - no branching choices during expedition
   - **Path is unambiguous:** At any system, there's either 0 or 1 link to take
   - **Future:** May allow branching paths later, but not v1
   - **Implication:** No need to pause for user choice, path is pre-determined

3. **End of segment:** ✅ **DECIDED - EXPEDITION COMPLETE**
   - **Definition:** If no next jump (in current route or via link), expedition is complete
   - **Action:** Stop auto-copying, show "Expedition Complete" notification
   - **Clear termination condition**

4. **Manual jumps (deviation):** ⚠️ **TO REVISIT**
   - **Likely:** Option A (ignore, keep copying next system in expedition)
   - **Reason:** User may need to refuel or make detour, but wants to continue path
   - **Note:** Mark as design decision to finalize later
   - **Current suggestion:** Don't auto-switch routes, just note deviation in history

5. **Starting expedition:** ✅ **DECIDED - Option C**
   - Check current location vs start point
   - If at start system: copy next system
   - If not at start: copy start system (need to get there first)
   - Smart detection based on FSDJump events

6. **Multiple expeditions:** ✅ **DECIDED - ONE ACTIVE ONLY**
   - Only one expedition can be active at a time
   - Only one expedition drives auto-copy behavior
   - User can switch active expedition (but only one at a time)

**Clipboard format:** Just system name (simple)

---

### 3. Ship Build Dependency ✅ **DECIDED**

**Problem:** Fuel calculations depend on ship build, but spec doesn't detail where/how ship data is stored.

**User Decisions:**

1. **What gets stored as route parameters:**
   - Route parameters are **both more AND less** than full ship build
   - **Derived from Loadout event** (FSD-specific calculations):
     - `optimal_mass`, `max_fuel_per_jump`, `fuel_multiplier`, `fuel_power`
     - `tank_size`, `base_mass`, `range_boost`
     - `internal_tank_size`, `supercharge_multiplier`
   - **Plus routing preferences** (user choices):
     - `source`, `destination`
     - `use_supercharge`, `use_injections`, `refuel_every_scoopable`
     - `max_time`, `cargo`, `algorithm`, etc.
   - See `/plotter/plot.py` for exact parameter extraction logic

2. **Storage options (for v1):**
   - ✅ **KISS approach (chosen):** Store route parameters as-is
   - Alternative (rejected): Store entire Loadout event (comprehensive but overkill)
   - Alternative (rejected): Complex validation/regeneration (too complex for v1)
   - **User responsibility:** User must understand routes are based on their current ship build

3. **Ship changes mid-expedition:**
   - ✅ **Consider impossible for v1** - exploration use case makes ship switching unlikely
   - No validation, no detection, no warnings
   - **Documentation:** Routes are tied to the ship they were created for
   - **Reality:** Route regeneration with new ship is very complex, far-future feature if at all

**Implementation:**
```python
# In route object (stored as generated by plotter)
"plotter_parameters": {
    # FSD-specific (derived from Loadout + Spansh data)
    "optimal_mass": "1894.099976",
    "max_fuel_per_jump": "5.2",
    "fuel_multiplier": "0.013",
    "fuel_power": "2.45",
    "tank_size": "16.0",
    "base_mass": "317.350006",
    "range_boost": "10.5",
    "internal_tank_size": "0.5",
    "supercharge_multiplier": "4",

    # Route planning options
    "source": "Hypio Bluae BA-Q d5-2793",
    "destination": "Beagle Point",
    "use_supercharge": "1",
    "use_injections": "0",
    "refuel_every_scoopable": "0",
    "max_time": "60",
    "cargo": "0",
    "algorithm": "optimistic",
}

# Optional: Store Loadout event for reference/debugging
"loadout_snapshot": {
    # Full Loadout event from journal (optional)
    "Ship": "diamondbackexplorer",
    "FuelCapacity": {"Main": 16.0, "Reserve": 0.5},
    "UnladenMass": 317.350006,
    # ... rest of Loadout event
    "captured_at": "2025-12-08T10:00:00Z",
}
```

**Why This Works:**
- Routes store exact parameters used to generate them (can be regenerated identically)
- Parameters are self-contained (no need to reference external ship data)
- KISS principle: Don't add complexity for unlikely scenarios
- User documentation makes expectations clear
- Future: Could add validation as enhancement, but not required for v1

**Important Notes:**
- **Plotter-specific parameters:** Parameter structure shown above is **Spansh-specific**
- **v1 scope:** Only Spansh plotter support
- **Future plotters:** Different plotters will have completely different parameter structures
- **Why this matters:** Route validation/regeneration logic must be plotter-aware
- The `plotter` field in route spec is critical for knowing how to interpret `plotter_parameters`

---

### 4. Route Validation ✅ **DECIDED - KISS Approach**

**Problem:** How much validation is needed for v1?

**User Decision: Trust Plotter + Trust User**

**What gets validated:**
- ✅ **Link validation (when editing links only):**
  - System ID matches in both routes: `routes[from.route_id].jumps[from.jump_index].system_id == system_id`
  - System ID matches in both routes: `routes[to.route_id].jumps[to.jump_index].system_id == system_id`
  - **No multiple outgoing links from same position:** Verify no (route_id, jump_index) pair has >1 outgoing link
  - Only validate when creating/editing link, not on every expedition load

**What does NOT get validated:**
- ❌ Fuel validation - Trust plotter calculated it correctly
- ❌ Jump range validation - Trust plotter knows ship capabilities
- ❌ Distance consistency - Trust plotter's calculations
- ❌ Permit requirements - User's responsibility to know their permits

**v1 Philosophy:**
- **Trust the plotter implicitly** - Spansh knows what it's doing
- **Trust the user** - Don't hand-hold or over-validate
- **Validate only critical graph structure** - Links must be structurally valid
- **Keep it simple** - Add validation later if users request it

**Implementation:**
```python
# Link validation (only when editing)
def validate_link(link, routes):
    from_route = routes[link["from"]["route_id"]]
    to_route = routes[link["to"]["route_id"]]

    # Check system IDs match
    from_system_id = from_route["jumps"][link["from"]["jump_index"]]["system_id"]
    to_system_id = to_route["jumps"][link["to"]["jump_index"]]["system_id"]

    if from_system_id != link["system_id"] or to_system_id != link["system_id"]:
        return {"valid": False, "error": "system_id_mismatch"}

    # Check no multiple outgoing links from same position
    position = (link["from"]["route_id"], link["from"]["jump_index"])
    if position in existing_link_positions:
        return {"valid": False, "error": "multiple_outgoing_links"}

    return {"valid": True}
```

**Why This Works:**
- Spansh plotter is trusted, mature software
- Users creating expeditions know their ships and permits
- Over-validation adds complexity with little benefit for v1
- Critical graph structure (links) is validated to prevent broken navigation
- Future: Can add optional validation warnings if users want them

---

### 5. Deviation Handling ✅ **DECIDED - Track Everything**

**Problem:** No specification for what happens when you go off-route.

**User Decision: Track Every Jump, Mark Deviations**

**Approach:**
- **Track ALL jumps** while expedition is active (not just route jumps)
- **Mark each jump** as on-route or deviation
- **Build complete path history** of actual journey taken
- **No special deviation handling** - just comprehensive tracking

**Why This Works:**
- Shows complete actual path taken (valuable for review/statistics)
- Automatically identifies deviations (any jump not matching expected next system)
- No complex recovery logic needed
- User can see "I went off-route here, then got back on track there"
- Useful for exploration logs and sharing expedition experiences

**Implementation:**
```python
expedition_state = {
    # ... existing fields ...

    # Complete jump history during expedition
    "jump_history": [
        {
            "timestamp": "2025-12-08T10:00:00Z",
            "system_name": "Sol",
            "system_id": 12345,
            "on_route": True,
            "expected": True,  # This was the next expected jump
            "route_id": "uuid_A",
            "route_jump_index": 20,
        },
        {
            "timestamp": "2025-12-08T10:05:00Z",
            "system_name": "Alpha Centauri",  # Detour for fuel
            "system_id": 54321,
            "on_route": False,  # NOT in route
            "expected": False,  # Deviation detected
            "route_id": None,
            "route_jump_index": None,
        },
        {
            "timestamp": "2025-12-08T10:10:00Z",
            "system_name": "Barnard's Star",
            "system_id": 67890,
            "on_route": True,
            "expected": False,  # Back on route, but skipped a jump
            "route_id": "uuid_A",
            "route_jump_index": 22,
            "note": "Skipped jump 21",
        },
    ],

    # Statistics derived from jump_history
    "stats": {
        "total_jumps": 50,
        "on_route_jumps": 45,
        "deviation_jumps": 5,
        "route_progress": {
            "expected_jumps_completed": 20,  # In sequence
            "jumps_skipped": 1,
            "current_position": 22,
        }
    }
}
```

**Deviation Detection Logic:**
```python
def on_fsd_jump(expedition, system_name, system_id):
    # Get next expected system
    expected = get_next_expected_system(expedition)

    # Check if this jump matches expected
    is_expected = (system_id == expected["system_id"])

    # Check if this system exists ANYWHERE in current route
    on_route = system_exists_in_current_route(expedition, system_id)

    # Record jump
    expedition["jump_history"].append({
        "timestamp": now(),
        "system_name": system_name,
        "system_id": system_id,
        "on_route": on_route,
        "expected": is_expected,
        "route_id": expedition["current_route_id"] if on_route else None,
        "route_jump_index": get_jump_index(expedition, system_id) if on_route else None,
    })

    # Update position if on route
    if on_route:
        expedition["current_jump_index"] = get_jump_index(expedition, system_id)

    # Copy next system to clipboard (always, even if deviation)
    if expected:
        copy_to_clipboard(expected["next_system_name"])
```

**Auto-Copy Behavior:**
- ✅ **Always copy next expected system** (even during deviations)
- User may detour for fuel/repairs but still wants to continue expedition
- Clipboard always shows "where you should go next to continue route"
- If user wants to continue deviating, they ignore clipboard and plot manually

**UI Display:**
- Show jump history with visual indication of deviations
- "You're currently 2 jumps off-route" notification
- Path visualization: green for on-route, yellow for deviations
- Statistics: "45/50 jumps on-route (90%)"

**Why This Works:**
- Simple logic: Is this system the expected next one? Is it in the route at all?
- Complete historical record of actual journey
- No complex recovery mechanisms needed
- User stays in control - can deviate and return whenever
- Valuable data for post-expedition review and sharing

---

## Edge Cases to Consider

### Link Edge Cases

#### 1. System Appears Multiple Times in a Route

**Scenario:** Sol appears at jump 5 and again at jump 50 in the same Route A.

**Problem:** If Route B also has Sol, which Sol occurrence in Route A does the link connect to?

**Reality:** This is actually valid! Each occurrence can have its own link:
- Link_1: Sol@A5 ↔ Sol@B10
- Link_2: Sol@A50 ↔ Sol@B10 (same Sol in B, different in A)

**Why:** You might approach Sol from different directions in Route A:
- First time (A5): Coming from one direction
- Second time (A50): Coming from another direction
- Route B connects at the same Sol, but you enter from different "sides" of Route A

**Recommendation:**
- **Allow multiple links for the same system at different positions** (different occurrences in same route)
  - Sol@A5 can have link to B
  - Sol@A50 can have link to C
  - These are different route positions, no ambiguity
- **Do NOT allow multiple links from same position** (per design decision)
  - ❌ Sol@A5 cannot have links to both B and C
- **Links specify exact jump index** (the cache)
- **Link is uniquely identified by:** system_id + from_route + from_jump_index + to_route + to_jump_index
- **When at Sol@A5:** UI shows the one link available from this position (if any)
- **When at Sol@A50:** UI shows the different link available from that position (if any)

**Validation:**
- System ID must match at both jump indices: `routes[route_A].jumps[5].system_id == routes[route_B].jumps[10].system_id`
- If route regeneration changes indices, search for system_id and update cache
- If system no longer exists in route, mark link as broken

---

#### 2. Circular Links ✅ **DECIDED - Allow with Warning**

**Scenario:** Route A → Route B → Route A (creates a loop)

**Reality:** Could cause infinite expedition, but some use cases are intentional.

**User Decision:**
- ✅ **Allow circular routes** - Don't block them
- ✅ **Warn user when creating** - Make them aware of the cycle
- ✅ **Cycle detection on link creation** - Simulate path traversal to detect loops
- Optional: Ask user to confirm ("This creates a loop. Continue?")

**Implementation:**
```python
def detect_cycle_on_link_creation(new_link, expedition):
    """
    Simulate following the path from new link's 'to' position.
    Check if we ever return to the 'from' position.
    """
    visited = set()
    current = (new_link["to"]["route_id"], new_link["to"]["jump_index"])
    start = (new_link["from"]["route_id"], new_link["from"]["jump_index"])

    while current not in visited:
        visited.add(current)

        # Follow route to its end or next link
        next_node = get_next_position(current, expedition)

        if next_node == start:
            return True  # Cycle detected!

        if next_node is None:
            return False  # Reached end, no cycle

        current = next_node

    return False  # Path ended without returning to start
```

**Valid Use Cases for Loops:**
- Farming routes (repeated resource gathering)
- Patrol routes (security/escort missions)
- Testing routes (same path multiple times)
- Training routes (practice jumps)

---

#### 3. Links from/to Middle of Route

**Scenario:** Link joins Route B at jump 25, skipping jumps 0-24.

**Problem:** UI and state management implications.

**Questions:**
- How to display "skipped" jumps?
- Should they count toward progress?
- What if skipped jumps had important refuel stops?

**Recommendation:**
- Links explicitly specify start index in target route
- UI shows "Starting Route B at jump 25/100"
- Validate fuel requirements from link point onward

---

#### 4. Multiple Links at Same System - ✅ **NOT ALLOWED (Design Decision)**

**Scenario:**
- System X appears in Route A (jump 10)
- System X also appears in Route B (jump 5)
- System X also appears in Route C (jump 20)

**Question:** Can we have links: A→B and A→C both from System X?

**Decision (User Clarification):**
- **NO** - Multiple link options at same system are **NOT ALLOWED** in v1
- **Reason:** Keep it simple, no branching choices during expedition
- **Path must be unambiguous:** At any system, there's 0 or 1 link to take

**What IS Allowed:**
- Multiple occurrences of same system in one route with different links:
  - Link_1: Sol@A5 → Sol@B10
  - Link_2: Sol@A50 → Sol@C20
  - (Different positions in Route A, so no ambiguity)

**What is NOT Allowed:**
- Multiple links from the same route position:
  - ❌ Link_1: Sol@A5 → Sol@B10
  - ❌ Link_2: Sol@A5 → Sol@C20
  - (Same position in Route A, ambiguous which to take)

**Validation:** Expedition creation must verify no position in any route has multiple outgoing links

---

#### 5. Unlinked Routes (Not an Edge Case!)

**Scenario:** Route exists in expedition but no links lead to it or from it.

**Reality:** This is **perfectly normal** and intentional. Routes are a library of available paths.

**Valid Use Cases:**
- Pre-planned alternative routes ("If I go this way instead...")
- Optional detours you might decide to take
- Emergency reroutes (e.g., fuel emergency, station damage)
- Reference routes (comparison or planning)

**Recommendation:**
- Fully support unlinked routes
- UI distinguishes:
  - **"Active Path"**: Routes currently in your path_history
  - **"Linked Routes"**: Routes you can reach via links
  - **"Available Routes"**: All routes in expedition (including unlinked)
- No validation warnings for unlinked routes
- User can manually switch to any route at any time (not just via links)

---

### Jump Edge Cases

#### 1. Neutron Star Without Scoopable Primary

**Scenario:** System has neutron star for boost, but no scoopable star for fuel.

**Problem:** After boost, you're low on fuel with no refuel option.

**Recommendation:**
- Look ahead for next fuel source
- Flag jump: `neutron_boost_without_fuel: true`
- Validation: Ensure enough fuel to reach next scoopable

---

#### 2. Permit-Locked Systems

**Scenario:** Route passes through Sol, but player doesn't have permit.

**Problem:** Cannot complete route.

**Recommendation:**
```python
# In jump object
"permit_required": "Sol System Permit",  # or null
```

**Validation:**
- Check user's acquired permits (if available)
- Warn on route creation
- Allow route but flag as "Requires Permit"

---

#### 3. Multiple Scoopable Stars in System

**Scenario:** Multi-star system with multiple KGBFOAM stars.

**Problem:** Which star is considered for refueling?

**Recommendation:**
- `scoopable` should be boolean (any scoopable star exists)
- Optionally: `primary_star_class: "K"` for more detail
- Game always arrives at primary star, so that's the refuel point

---

#### 4. Distance to Destination Ambiguity

**Scenario:** "distance to destination" - which destination?

**Problem:** Could mean:
- Distance to route end
- Distance to expedition final destination
- Distance to next waypoint

**Recommendation:**
- Rename to `distance_to_route_end` for clarity
- Add optional `distance_to_expedition_end` if needed

---

#### 5. Fuel in Tank = 0

**Scenario:** Fuel calculation shows 0 fuel before reaching refuel point.

**Problem:** Ship is stranded. Emergency fuel rat scenario.

**Recommendation:**
- Validation error: Route is impossible
- Suggest: Add refuel stops or reduce jump distances

---

#### 6. Overcharge Without Neutron Star

**Scenario:** `overcharge: true` but system has no neutron star or white dwarf.

**Problem:** Cannot actually overcharge FSD.

**Recommendation:**
- Validation: If `overcharge: true`, verify star type
- Add `has_neutron_star` or `star_class` field
- Cross-validate overcharge flag with star type

---

### Route Edge Cases

#### 1. Empty Route

**Scenario:** Route with 0 jumps (you're already at destination).

**Problem:** Valid edge case?

**Recommendation:**
- Allow empty routes
- UI shows "Already at destination"
- Used for expeditions with optional branches

---

#### 2. Single-Jump Route

**Scenario:** Start and end are adjacent systems.

**Problem:** Unusual but valid.

**Recommendation:**
- Allow single-jump routes
- Common for short courier missions or testing

---

#### 3. Route Regeneration

**Scenario:** Ship build changes, need to regenerate route with new parameters.

**Problem:** How to preserve expedition structure and links?

**Recommendation:**
```python
"route_history": [
    {
        "version": 1,
        "created_at": "2025-12-08T10:00:00Z",
        "ship_build": {...},
        "jumps_count": 100,
        "archived": True,
    },
    {
        "version": 2,
        "created_at": "2025-12-08T12:00:00Z",
        "ship_build": {...},  # New build
        "jumps_count": 95,  # Optimized
        "active": True,
    }
]
```

**Process:**
1. Regenerate route with new parameters
2. Attempt to preserve links (match by system ID)
3. Warn user of broken links
4. Archive old route version

---

#### 4. Plotter Failure

**Scenario:** Spansh API is down or returns error.

**Problem:** Cannot create or regenerate route.

**Recommendation:**
- Cache successful route responses
- Graceful degradation: use cached data
- Retry logic with exponential backoff
- Clear error messages to user

---

#### 5. Route Becomes Invalid

**Scenario:**
- System permits revoked
- Systems added/removed from galactic map (rare)
- Background simulation changes star types

**Problem:** Route is no longer completable.

**Recommendation:**
- Add `route_validity` check
- Warn user of invalidated routes
- Suggest regeneration
- Mark as "Needs Regeneration"

---

## Missing Metadata

### Expedition Level

**Critical Addition (User Requirement):**
> "The expedition itself may want to have a field `start` which is almost like a link in that it points to a route and a system in that route (with cache index and all). That way you won't even have to start at the first jump in a route."

**Why This Matters:**
- Expeditions don't have to start at route[0].jumps[0]
- Can start mid-route (e.g., "I'm already at Colonia, start expedition from there")
- Useful for resuming, or when planning from current location

**Suggested Additions:**
```python
expedition = {
    # ... existing fields ...

    # START POINT (User requirement - critical!)
    "start": {
        "route_id": "uuid_A",
        "system_name": "Colonia",  # For display
        "system_id": 12345,        # Source of truth
        "jump_index": 35,          # Cache: where Colonia appears in Route A
        "cache_valid": True,
        "last_validated": "2025-12-08T10:00:00Z",
    },

    # Metadata
    "created_at": "2025-12-08T10:00:00Z",
    "last_updated": "2025-12-08T12:00:00Z",
    "version": 1,  # Schema version for future migration
    "author": "CMDR John Doe",  # Optional, for sharing
    "description": "Exploration trip to Colonia",
    "tags": ["exploration", "long-range", "neutron-highway"],
    "estimated_total_time_hours": 12.5,
    "total_distance_ly": 22000,
    "difficulty_rating": "hard",  # based on neutron jumps, fuel, etc.
    "is_public": False,  # For sharing/importing
}
```

**Start Field Structure:**
- Same structure as link endpoints (route_id + system_id + cached jump_index)
- Allows starting at any jump in any route
- Must be validated same way as links (system_id matches jump_index)
- If cache invalid, search route for system_id

**Use Cases:**
- "Start expedition from my current location"
- "I'm already at Colonia, skip to that point"
- Resuming a partially completed expedition
- Starting from a waypoint rather than origin

---

### Route Level

**Suggested Additions:**
```python
route = {
    # ... existing fields ...
    "created_at": "2025-12-08T10:00:00Z",
    "last_updated": "2025-12-08T10:00:00Z",
    "plotter_version": "spansh-v2.3",  # API version
    "efficiency_rating": 95,  # Spansh efficiency %
    "required_permits": ["Sol System Permit"],
    "neutron_jump_count": 15,
    "white_dwarf_count": 0,  # Dangerous, avoid if possible
    "refuel_stop_count": 8,
    "estimated_time_hours": 3.5,  # Based on avg jump time
    "total_distance_ly": 5000,
}
```

---

### Jump Level

**Suggested Additions:**
```python
jump = {
    # ... existing fields ...
    "star_class": "K",  # O, B, A, F, G, K, M, L, T, Y
    "is_scoopable": True,  # Derived from star_class (KGBFOAM)
    "has_neutron_star": False,
    "has_white_dwarf": False,
    "permit_required": None,  # or "Sol System Permit"
    "arrival_distance_ls": 5.2,  # Light-seconds from main star
    "points_of_interest": [
        {
            "type": "earth_like_world",
            "body_name": "Kepler-442 b",
        }
    ],
}
```

**Why:**
- `star_class` is critical: Only KGBFOAM are scoopable
- Neutron stars are dangerous but useful
- POIs make exploration more interesting

---

## Architectural Concerns

### 1. Graph Structure and Navigation Model

**Problem:** Links describe connections, but navigation semantics are unclear.

**Current Spec:** "which route starts" + links between routes

**Actual Model (based on user clarification):**

Expeditions are **non-linear graphs of route segments**. Routes are reusable path libraries, not sequential steps.

**Real-World Example:**
```
Route A (Main): Sys_A → Sys_B → ... → Sol → ... → Colonia → ... → Beagle_Point
                (A0)    (A1)         (A20)      (A35)         (A50)

Route B (Detour): Sys_X → Sys_Y → Sol → Sys_Z → Colonia
                  (B0)    (B1)    (B2)   (B3)    (B4)

Links:
- Link_1: Sol (appears at A20 and B2)
- Link_2: Colonia (appears at A35 and B4)

Your Path Example:
A[0→20] (reach Sol on Route A)
  --Link_1--> Switch to Route B at Sol (now at B2)
B[2→4] (reach Colonia on Route B)
  --Link_2--> Switch back to Route A at Colonia (now at A35)
A[35→50] (continue to Beagle Point)
```

**CRITICAL: Links Connect IDENTICAL Systems**

From the spec: *"Each link must link identical systems in both routes."*

This means:
- **Links are NOT arbitrary jump points** - they connect the SAME physical system
- **Sol in Route A = Sol in Route B** (same system, different indices in routes)
- **You don't teleport** - you're at the same location, just switching which route you follow
- **Path is continuous** - always jumping between adjacent systems in space

**Key Points:**
1. **Routes are libraries of paths**, not stages
2. **Links connect shared systems** between routes (Sol appears in both routes)
3. **You can revisit the same route** multiple times (A → B → A in example)
4. **You don't complete routes**, you traverse portions of them
5. **Jump indices are cached lookups** - system ID/name is the true connection point

**Navigation Decisions:**

**Question:** How does user determine which link to take?

Option A - Pre-planned path:
```python
expedition = {
    "initial_route_id": "uuid_A",
    "initial_jump_index": 0,

    # Pre-planned path through graph
    "planned_path": [
        {"route_id": "uuid_A", "start_index": 0, "end_index": 20},
        {"route_id": "uuid_B", "start_index": 5, "end_index": 10},
        {"route_id": "uuid_A", "start_index": 22, "end_index": 40},
    ],

    # All available links (user can deviate from plan)
    "links": [...],
}
```

Option B - Runtime decision:
```python
expedition = {
    "initial_route_id": "uuid_A",
    "initial_jump_index": 0,

    # Just define available links, user chooses at runtime
    "links": [
        {
            "id": "link_1",
            "system": {...},
            "from": {"route_id": "uuid_A", "jump_index": 20},
            "to": {"route_id": "uuid_B", "jump_index": 5},
        },
        {
            "id": "link_2",
            "system": {...},
            "from": {"route_id": "uuid_B", "jump_index": 10},
            "to": {"route_id": "uuid_A", "jump_index": 22},
        },
    ],
}
```

**Recommendation:**
- **Support both models**: Pre-planned path + ability to deviate
- Default: Runtime decision (more flexible)
- Optional: User can define intended path for progress tracking
- UI shows available links when at link systems
- Allow deviations: "You're at A20, planned path takes Link_1, but you can also continue on Route A or take other links"

**Progress Tracking:**
- If planned path exists: Progress = position in planned path
- If no planned path: Progress = distance/jumps from start (no percentage)

**Graph Validation:**
- Links must reference valid systems in both routes
- Cycles are allowed (e.g., A → B → A)
- Orphaned routes are allowed (they're just available paths)

---

### 2. Caching vs Live Data

**Problem:** Jump index in links is "cache" - when to invalidate?

**Context from Spec:** *"Each link must link identical systems in both routes."*

**How Links Work:**
1. **System ID is the connection** - Links connect the SAME physical system
2. **Jump index is just a cache** - Quick lookup of where that system appears
3. **Cache can become stale** - Route regeneration may change where system appears

**Issues:**
- Route regeneration changes jump indices
- System might move in jump list
- System might be removed from route entirely

**Recommendation:**
```python
link = {
    # The actual connection point (source of truth)
    "system_name": "Sol",  # For display
    "system_id": 12345,    # MUST match in both routes

    # Cached indices (performance optimization)
    "from": {
        "route_id": "uuid1",
        "jump_index": 42,  # Where Sol appears in Route 1
        "cache_valid": True,
        "last_validated": "2025-12-08T10:00:00Z",
    },
    "to": {
        "route_id": "uuid2",
        "jump_index": 15,  # Where Sol appears in Route 2
        "cache_valid": True,
        "last_validated": "2025-12-08T10:00:00Z",
    }
}
```

**Validation Process:**
1. Check `routes[from.route_id].jumps[from.jump_index].system_id == system_id`
2. Check `routes[to.route_id].jumps[to.jump_index].system_id == system_id`
3. If either mismatch: Search entire route for system_id, update cache
4. If system_id not found in route: Mark link as broken (route changed significantly)

**Cache Invalidation Triggers:**
- Route regenerated with different parameters
- Route manually edited
- On expedition load (validate all links)

---

### 3. Plotter Abstraction (Currently TBD)

**Problem:** Different plotters have different capabilities and formats.

**Concern:** Spansh is only one plotter. Others may exist:
- ED-Router
- Neutron Router
- Custom plotters

**Recommendation:** Define interface now:

```python
from abc import ABC, abstractmethod

class RoutePlotter(ABC):
    @abstractmethod
    def plot_route(self, start: str, end: str, parameters: dict) -> Route:
        """
        Generate a route from start to end system.

        Args:
            start: System name or ID
            end: System name or ID
            parameters: Plotter-specific parameters

        Returns:
            Route object with jumps
        """
        pass

    @abstractmethod
    def get_parameters_schema(self) -> dict:
        """
        Return JSON schema for this plotter's parameters.

        This allows UI to generate parameter input forms.
        """
        pass

    @abstractmethod
    def validate_parameters(self, parameters: dict) -> list:
        """Validate parameters, return list of errors."""
        pass

    @property
    @abstractmethod
    def plotter_name(self) -> str:
        """Return plotter identifier (e.g., 'spansh')."""
        pass
```

**Usage:**
```python
# In route
route = {
    "plotter": "spansh",
    "plotter_parameters": {
        "efficiency": 95,
        "range": 65.2,
        "use_neutrons": True,
    },
    "plotter_metadata": {
        "job_id": "abc123",
        "api_version": "v2.3",
    }
}
```

---

## Data Consistency Issues

### 1. System Name vs ID

**Problem:** System names can change (rare but happens with discoveries).

**Recommendation:**
- System ID is source of truth
- Name is for display only
- Always validate by ID first, name second

---

### 2. Distance Calculation

**Problem:** Each jump has distance from previous. Should sum match total?

**Issue:** Floating point errors accumulate.

**Recommendation:**
```python
route = {
    "total_distance_ly": 5000.0,  # Stored
    "calculated_distance_ly": 4999.8,  # Sum of jump distances
    "distance_variance": 0.2,  # Acceptable if < 1.0 LY
}
```

**Validation:** Warn if variance > 1.0 LY.

---

### 3. Fuel Arithmetic Chain

**Problem:** Fuel calculations must be consistent:
```
fuel_in_tank[i] - fuel_used[i] = fuel_in_tank[i+1]
```

**Recommendation:**
- Validate entire chain on route creation
- Recalculate if ship build changes
- Error if any jump results in negative fuel

---

### 4. Route Transition Mechanics

**Problem:** When jumping from Route A to Route B at a link, what happens?

**Scenario:**
- Route A ends at "Sol"
- Route B starts at "Alpha Centauri"
- Link connects them at "Sol"

**Questions:**
- Do you jump from Sol to Alpha Centauri? (wasteful)
- Or does Route B start at Sol? (link point)

**Recommendation:**
```python
link = {
    "system_name": "Sol",
    "system_id": 12345,
    "from": {
        "route_id": "uuid1",
        "jump_index": 42,  # Last jump of Route A
    },
    "to": {
        "route_id": "uuid2",
        "jump_index": 10,  # Continue from here in Route B
    },
    "transition_type": "direct",  # or "skip_to_index"
}
```

**Behavior:**
- At Sol (Route A, jump 42), expedition transitions to Route B
- Route B continues from jump 10 (also Sol)
- Jumps 0-9 of Route B are skipped
- User is now on Route B

---

## Recommendations

### High Priority (Must Address)

1. **✅ Add expedition state tracking**
   - Current position (route ID + jump index)
   - Progress tracking (completed jumps, distance)
   - Integration with journal events (FSDJump auto-advance)
   - Started/paused timestamps

2. **✅ Define plotter interface**
   - Abstract class for different route planners
   - Parameter schemas for validation
   - Versioning support

3. **✅ Add validation mechanisms**
   - Link validation (systems exist in both routes)
   - Fuel validation (requirements vs capacity)
   - Distance consistency checks
   - Permit requirement checks

4. **✅ Clarify route graph structure**
   - How routes connect (linear vs branching)
   - How to determine next route
   - Handling branches and choices

---

### Medium Priority (Should Address)

5. **📝 Add ship build tracking**
   - Fuel capacity and max jump range
   - Capture from Loadout event
   - Detect changes mid-expedition
   - Invalidate routes if build changes

6. **📝 Add comprehensive route metadata**
   - Creation/update timestamps
   - Danger ratings (neutron/white dwarf counts)
   - Required permits list
   - Estimated completion time

7. **📝 Define deviation handling**
   - Detection of off-route jumps
   - Deviation history tracking
   - Re-routing options
   - Recovery mechanisms

8. **📝 Add route versioning**
   - Track route regeneration
   - Archive old versions
   - Link migration on regeneration

---

### Low Priority (Nice to Have)

9. **💡 Add points of interest**
   - Notable systems (ELW, WW, etc.)
   - Exploration targets
   - Tourist beacons
   - Guardian/Thargoid sites

10. **💡 Add sharing/export functionality**
    - Export expedition to file
    - Import from other commanders
    - Validation on import
    - Public expedition library

11. **💡 Add history tracking**
    - Completed expeditions archive
    - Statistics (total distance, time, jumps)
    - Achievements/milestones

12. **💡 Add emergency features**
    - Fuel rat integration
    - Emergency reroute to nearest scoopable
    - Hull repair detection (damaged stations)

---

## Specific Questions to Answer

These questions should be answered in the specification:

1. **Can routes be edited after creation?** ✅ **DECIDED - Immutable**
   - **Routes are immutable** after creation
   - **Why:**
     - "Typo in destination" = Can't happen (plotter validates systems at generation time)
     - "Regenerate with different ship" = Need new expedition anyway (routes are ship-specific)
     - "Optimize existing route" = Generate new route, create new expedition
     - **"Add a detour"** = Just take it! Jump tracking marks deviation, detects return to route
   - **Benefits of immutability:**
     - No cache invalidation needed (jump indices never change)
     - No expedition corruption (routes can't change under active expeditions)
     - No versioning complexity
     - Routes are snapshots from plotter (reproducible)
   - **If user wants different route:**
     - Generate new route from plotter
     - Create new expedition (or add as new route to existing expedition)
   - **Implementation note:**
     - Route files are write-once
     - Deletion allowed (with warning if used by expeditions)
     - No edit functionality needed

2. **Can you have multiple active expeditions?**
   - Or just one at a time?
   - How to track which is active?
   - Can you pause/resume expeditions?

3. **What happens if you switch ships mid-expedition?**
   - Is expedition invalidated?
   - Prompt to regenerate routes?
   - Allow continuation with warning?

4. **How do you handle route regeneration?**
   - Preserve links (match by system ID)?
   - Warn user of broken links?
   - Archive old route version?

5. **Are routes immutable?** ✅ **DECIDED - Yes (see Q1)**
   - Routes are immutable snapshots from plotter
   - See Q1 for full rationale and benefits

6. **What's the save format?** ✅ **DECIDED - Structured JSON Files**
   - **Format:** JSON files (human-readable, easy to debug/share)
   - **Structure:**
     ```
     APP_DIR/
       expeditions/
         index.json              # List of expeditions + currently active
         {expedition_id}.json    # Individual expedition files
         routes/
           {route_id}.json       # Individual route files
     ```
   - **index.json format:**
     ```json
     {
       "active_expedition_id": "uuid_123",
       "expeditions": [
         {
           "id": "uuid_123",
           "name": "Trip to Beagle Point",
           "created_at": "2025-12-08T10:00:00Z",
           "last_updated": "2025-12-08T15:30:00Z",
           "status": "active"
         },
         {
           "id": "uuid_456",
           "name": "Colonia Loop",
           "created_at": "2025-11-01T08:00:00Z",
           "last_updated": "2025-11-01T08:00:00Z",
           "status": "completed"
         }
       ]
     }
     ```
   - **Why this structure:**
     - Separate files = easy to share individual expeditions
     - Routes in subdirectory = can be shared/reused across expeditions
     - index.json = quick lookup of available expeditions without loading all files
     - Active expedition tracked globally = only one can be active

7. **How do route transitions work?** ✅ **DECIDED - Context-Dependent**
   - **While TRAVELING (expedition active):** Seamless auto-switching
     - Arrive at link system → automatically switch to linked route
     - No prompts, no user interaction needed
     - Copy next system from new route to clipboard immediately
     - Path is pre-determined, no decisions to make
     - **Why:** User is in-game, wants minimal friction, stay immersed
   - **While EDITING (creating/modifying expedition):** Explicit and obvious
     - Route transitions clearly shown in UI
     - Visual indicators: "Link from Route A (jump 20) → Route B (jump 5)"
     - Preview path: "You'll follow: A[0-20] → B[5-10] → A[22-40]"
     - Clear understanding of structure being created
     - **Why:** User needs to understand what they're building
   - **Implementation:**
     ```python
     def on_fsd_jump_during_expedition(system_id):
         # Check if this system has a link
         link = get_outgoing_link(current_route_id, current_jump_index)

         if link:
             # Seamlessly switch to linked route
             expedition["current_route_id"] = link["to"]["route_id"]
             expedition["current_jump_index"] = link["to"]["jump_index"]

             # Optional: Log transition for history
             expedition["jump_history"][-1]["link_traversed"] = link["id"]

         # Copy next system to clipboard
         next_system = get_next_expected_system(expedition)
         copy_to_clipboard(next_system["name"])
     ```

8. **Can user manually switch routes without links?** ✅ **DECIDED - Editing Only**
   - **While traveling:** No manual switching (follow pre-defined path)
   - **While editing:** Full flexibility to create/modify links
   - **Rationale:**
     - Traveling: Path is determined, stay on track
     - Editing: User has complete control over expedition structure
   - **Special case (future enhancement):** "Emergency jump to route" if lost/stranded
     - Not v1 feature, but could add later
     - "You're off-route. Jump to nearest system in Route B?"

9. **How to handle "Continue on current route" vs "Take link"?** ✅ **DECIDED - No Choice Needed**
   - **This scenario cannot happen** due to previous design decisions:
     - No multiple outgoing links from same position (Decision #2)
     - Path is pre-determined and unambiguous (Decision #7)
   - **Example:**
     - ❌ Invalid: A20 has link to B5 AND continues to A21 (ambiguous)
     - ✅ Valid: A20 has link to B5, A20 is end of segment (unambiguous)
     - ✅ Valid: A20 continues to A21, no link (unambiguous)
   - **During editing:** User creates links that define clear path
   - **During traveling:** Auto-follow the only available path
   - **Result:** No user prompts needed, seamless navigation

10. **What's the update frequency for expedition state?** ✅ **DECIDED - After Every FSDJump**
    - **Save to disk after every FSDJump event** processed
    - **Why this works:**
      - Jumps take ~40+ seconds even when speedrunning (hyperspace animation, star arrival, etc.)
      - I/O is not a performance concern with this frequency
      - Maximum data loss = current jump in progress (minimal)
      - No complex buffering or delayed writes needed
    - **Implementation:**
      ```python
      def on_fsd_jump(system_name, system_id):
          # Update expedition state
          update_expedition_state(system_name, system_id)

          # Save to disk immediately
          save_expedition_to_file(expedition)

          # Copy next system to clipboard
          copy_next_system_to_clipboard(expedition)
      ```
    - **Benefits:**
      - Simple implementation (no queues, no timers)
      - Reliable (state always saved before next jump)
      - App crash = lose at most current jump
      - Closing app = no special handling needed

11. **How to handle expeditions across game updates?**
    - Galaxy map changes
    - Star class changes
    - New permits added

12. **What about multi-session expeditions?** ✅ **DECIDED - Handled by Q10**
    - **No special handling needed** due to save-after-every-jump (Q10)
    - **On app close:**
      - State already saved to disk from last FSDJump
      - No additional save needed
    - **On app launch:**
      - Load `index.json` to get active expedition ID
      - Load active expedition file
      - Continue from last saved position
      - UI shows: "Resume Expedition: Trip to Beagle Point"
    - **Multi-device sync:** Not v1 feature
      - Could manually copy expedition files between devices
      - Future: Cloud sync, but not priority
    - **Edge case - journal progressed while app closed:**
      - User made jumps without EDXD running
      - On next FSDJump after launch, expedition will update
      - Jump history may have gaps, but position updates correctly
      - Optional future enhancement: Scan journal for missed jumps on startup

13. **What defines "expedition complete"?** ✅ **DECIDED**
    - **Answer:** If there's no next jump (in current route or via link), expedition is complete
    - **Clear termination:** No next system = done
    - **Action:** Stop auto-copy, show "Expedition Complete" notification
    - **No ambiguity:** Path is pre-determined, so reaching the end is unambiguous

14. **How are links bidirectional or unidirectional?** ✅ **DECIDED - Allow Cycles, Warn User**
    - **Real question:** How to handle circular routes (A → B → A)?
    - **Answer:** Allow circular routes, but notify user (maybe ask to undo)
    - **Implementation:** Simulate path traversal when creating link to detect cycles
    - **Cycle detection:** Follow all possible paths from new link, check if any revisit same (route_id, jump_index) node
    - **User experience:**
      - "Warning: This link creates a circular route. You could loop infinitely. Continue?"
      - Show preview of circular path: "A[0-20] → B[5-10] → A[22-40] → (back to A20)"
    - **Why allow it:** Some expeditions intentionally loop (farming routes, patrol routes)
    - **Why warn:** User should be aware they're creating potential infinite loop

---

## Conclusion

The specification provides a solid foundation for the expeditions feature, but needs significant expansion in the following areas:

**🔑 Key Insight (User Clarification):**
Expeditions are **non-linear graphs of route segments**, not sequential route lists. Routes are reusable path libraries that you navigate between via links. The same route can be visited multiple times, and you traverse portions of routes rather than completing them. This fundamentally changes state tracking, progress calculation, and UI design.

**Critical Gaps:**
1. **State management and progress tracking** - Requires path history, not "completed routes"
2. **Navigation semantics** - Auto vs manual link traversal, route switching behavior
3. **Expedition completion criteria** - What defines "done" in a potentially infinite graph?
4. **Journal event integration** - Auto-advance + link detection
5. **Ship build dependency tracking** - Capture from Loadout, validate routes
6. **Comprehensive validation** - Links, fuel, distances, permits
7. **Plotter interface definition** - Abstract different route planners

**Edge Cases:**
1. Circular links (A → B → A) - Valid and expected
2. Unlinked routes - Valid, they're available path options
3. Multiple links at same route position - **NOT ALLOWED** (design decision for v1)
4. Same system appearing multiple times - Valid, each occurrence can have different link
5. Fuel/range validation across route transitions
6. Route regeneration and link migration
7. Deviation detection and recovery - Keep copying next system (likely approach)

**Data Consistency:**
1. System ID as source of truth
2. Fuel arithmetic validation across transitions
3. Distance calculation consistency
4. Route transition mechanics (which jumps are skipped?)
5. Link bidirectionality

Addressing these concerns will result in a robust, user-friendly expedition system that handles real-world usage scenarios and edge cases gracefully.
