# Expeditions Specification - Design Decisions

**Date:** 2025-12-08
**Status:** All critical decisions finalized for v1

This document consolidates all design decisions made for the Expeditions feature. For detailed analysis and rationale, see SPEC_REVIEW.md.

---

## Core Model

**Expeditions are non-linear graphs of route segments.** Routes are reusable path libraries that you navigate between via links. Links connect identical systems (same system_id) across routes. The path through the graph is pre-determined and unambiguous (no branching).

**Example navigation:**
- Route A: `[A0...A20(Sol)...A35(Colonia)...A50]`
- Route B: `[B0...B2(Sol)...B4(Colonia)...B10]`
- Links (unidirectional):
  - Link 1: Sol@A20 → Sol@B2
  - Link 2: Colonia@B4 → Colonia@A35
- Valid path: `A[0-20] → B[2-4] → A[35-50]`

---

## 1. Expedition State & Progress Tracking

**Decision:** Track complete jump history, not "completed routes."

```python
expedition_state = {
    # Complete jump history (all jumps while expedition active)
    "jump_history": [
        {
            "timestamp": "2025-12-08T10:00:00Z",
            "system_name": "Sol",
            "system_id": 12345,
            "on_route": True,        # System exists in route
            "expected": True,        # Was next expected jump
            "route_id": "uuid_A",
            "route_jump_index": 20,
            "link_traversed": "link_1"  # If link was taken
        },
        {
            "system_name": "Alpha Centauri",  # Deviation for fuel
            "system_id": 54321,
            "on_route": False,
            "expected": False,
            # ...
        }
    ],

    # Derived statistics
    "stats": {
        "total_jumps": 50,
        "on_route_jumps": 45,
        "deviation_jumps": 5,
    }
}
```

**Progress calculation:** `current_baked_index / len(baked_route)` (only for active/completed/ended expeditions).

**Last tracked position:** Computed from jump_history, not stored separately.

- **Get last tracked position:** Return last entry in jump_history (or expedition start if no jumps yet). May be off-route (route_id = None). Note: This is the last position tracked by EDXD while expedition was active, not necessarily the player's actual current position.

- **Get last on-route position:** Search backwards through jump_history for last entry where on_route = True. Used for checking if new jumps are on the planned route. Falls back to expedition start if no on-route jumps exist yet. Needed to handle consecutive deviations where last tracked position has no route_id.

**Baked route index:** Once expedition is active, current position in baked_route is tracked as `current_baked_index`. This points to the last completed jump in the baked route.

---

## Baked Route

**Concept:** When an expedition transitions from `planned` to `active`, the complete path through the graph is pre-computed and stored as a flat array. This eliminates the need for graph traversal during travel.

**When baking occurs:** During `planned` → `active` transition.

**Structure:**
```python
"baked_route": [
    {
        "route_id": "uuid_A",
        "jump_index": 0,
        "system_name": "Sol",
        "system_id": 12345,
    },
    # ... route A jumps 1-20
    {
        "route_id": "uuid_A",
        "jump_index": 20,
        "system_name": "Waypoint System",
        "system_id": 99999,
        "link_id": "link_1",  # Optional: marks transition point
    },
    # Now on route B (via link_1)
    {
        "route_id": "uuid_B",
        "jump_index": 5,
        "system_name": "Next System",
        "system_id": 88888,
    },
    # ... continues to end of path
]
```

**How it's built:**
1. Start at expedition start point (route_id + jump_index)
2. Follow jumps in sequence within that route
3. When reaching a system with an outgoing link, follow the link to next route
4. **Cycle detection:** Track visited (route_id, jump_index) pairs. If about to add a jump that's already in the baked route, we've detected a loop:
   - Stop baking at this point (don't add the duplicate)
   - Store `baked_loop_back_index` = index of first occurrence of this system in baked route
   - This creates a circular path
5. Continue until no more jumps and no outgoing links, OR cycle detected
6. Result: flat array of all jumps in order (may be circular if loop detected)

**Benefits:**
- ✅ **Next expected system:** `baked_route[current_baked_index + 1]` (wraps to `baked_loop_back_index` if at end and loop exists)
- ✅ **Progress calculation:** `current_baked_index / len(baked_route)` (for circular routes, progress cycles)
- ✅ **No graph traversal:** Just array indexing
- ✅ **No link checking during travel:** Path is pre-determined
- ✅ **Simpler deviation detection:** Compare jump against next expected system
- ✅ **Clear completion condition:** `current_baked_index == len(baked_route) - 1` AND `baked_loop_back_index is None` (non-circular only)

**Only exists when:** `status` is `active`, `completed`, or `ended`. Not present in `planned` state.

---

## 2. Journal Integration - Auto-Copy (KILLER FEATURE)

**Decision:** Auto-advance position and copy next system to clipboard after every FSDJump.

**Core workflow:**
1. User jumps (FSDJump event)
2. EDXD updates expedition state
3. **Auto-copies next system name to clipboard**
4. User pastes into galaxy map (no alt-tab)

**Auto-copy behavior:**
- ✅ Copy immediately after FSDJump (likely timing, may refine)
- ✅ Copy next expected system **even during deviations**
- ✅ Auto-switch routes at links (seamless, no prompts)
- ✅ Stop copying when expedition complete (no next jump)

**Expedition start field:**
```python
"start": {
    "route_id": "uuid_A",
    "system_name": "Colonia",
    "system_id": 12345,
    "jump_index": 35,  # Cache
}
```
Allows starting at any jump in any route, not just route[0].

---

## 3. Ship Build Dependency

**Decision:** Store plotter parameters with route. Trust user to not change ship mid-expedition.

**Route parameters (Spansh-specific):**
```python
"plotter": "spansh",
"plotter_parameters": {
    # FSD-specific (derived from Loadout event + Spansh data)
    "optimal_mass": "1894.099976",
    "max_fuel_per_jump": "5.2",
    "fuel_multiplier": "0.013",
    "fuel_power": "2.45",
    "tank_size": "16.0",
    "base_mass": "317.350006",
    "range_boost": "10.5",
    "internal_tank_size": "0.5",
    "supercharge_multiplier": "4",

    # Route options
    "source": "Hypio Bluae BA-Q d5-2793",
    "destination": "Beagle Point",
    "use_supercharge": "1",
    "algorithm": "optimistic",
    # ... other Spansh params
}
```

**Ship changes:** Consider impossible for v1 (exploration use case). No validation, no warnings. Different plotters will have different parameter structures.

---

## 4. Route Validation

**Decision:** Minimal validation. Trust plotter, trust user.

**What gets validated:**
- ✅ **Links only** (when creating/editing):
  - System ID matches in both routes
  - No multiple outgoing links from same (route_id, jump_index)
  - Cycle detection (warn user if creating loop)

**What does NOT get validated:**
- ❌ Fuel requirements
- ❌ Jump range feasibility
- ❌ Distance consistency
- ❌ Permit requirements

**Cycle detection logic:**
- When creating a link: simulate following the path from the link's 'to' position
- Follow each jump and link in sequence, tracking visited positions
- If path returns to the link's 'from' position: cycle detected
- Warn user: "This creates a loop. Continue?"
- Circular routes allowed (farming routes, patrol routes) but user must acknowledge the warning

---

## 5. Deviation Handling

**Decision:** Track all jumps, mark deviations. No recovery logic.

**On FSDJump processing:**

1. **Get expected next system:**
   - If `current_baked_index + 1 < len(baked_route)`: use `baked_route[current_baked_index + 1]`
   - Else if `baked_loop_back_index is not None`: use `baked_route[baked_loop_back_index]` (circular route wraps around)
   - Else: No next system (non-circular route complete)
2. **Check if jump is expected:** Compare `system_id` with expected system
3. **Record jump in history:**
   - Store timestamp, system name/id
   - Flag: on_route (true if matches baked route)
   - Flag: expected (true if matches next expected system)
   - Store route_id and jump_index from baked route if on-route, else None
4. **Update position if on-route:**
   - If `current_baked_index + 1 < len(baked_route)`: Increment `current_baked_index`
   - Else if `baked_loop_back_index is not None`: Set `current_baked_index = baked_loop_back_index` (loop back)
   - Else: Route complete (triggers `active` → `completed` transition)
5. **Copy next expected system to clipboard:** Get next expected system using same logic as step 1 (even during deviations)

**Benefits:** Complete historical record, no complex recovery, user stays in control.

---

## 6. Save Format

**Decision:** Structured JSON files in `APP_DIR/expeditions/`.

```
APP_DIR/
  expeditions/
    index.json              # Active expedition + list of all
    {expedition_id}.json    # Individual expeditions
    routes/
      {route_id}.json       # Individual routes
```

**index.json:**
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
    },
    {
      "id": "uuid_789",
      "name": "Sag A* Trip",
      "created_at": "2025-12-01T08:00:00Z",
      "last_updated": "2025-12-01T08:00:00Z",
      "status": "planned"
    }
  ]
}
```

**Note:** `active_expedition_id` points to the ONE active expedition (null if none active). Only expeditions with `status: "active"` can be in this field.

**Save frequency:** After every FSDJump (~40+ seconds between jumps, I/O not a concern).

**Multi-session:** State already saved from last jump. On launch, load active expedition and check for position mismatch (see below).

### Missing Jumps Detection (App Not Running)

**Edge case:** User travels while EDXD is not running.

**On app startup (or first FSDJump after startup):**

1. **Compare positions:** Get player's actual current system from Status.json (or wait for first FSDJump). Compare with last tracked position (last entry in jump_history).

2. **If position unchanged:** Continue normally.

3. **If position changed:**
   - Check if player's actual current system exists anywhere in expedition path
   - **If on expedition path:**
     - Prompt user: "You traveled while offline. Fill jump history from planned route?"
     - If yes: Add synthetic entries for all planned jumps between last tracked position and player's actual position
     - If no: Mark gap in history, continue from player's actual position
   - **If off expedition path:**
     - Warn user: "Your actual position is off-route. Continuing as detour."
     - Next FSDJump will be recorded as deviation

**Synthetic jump entries:**
- Flag with `synthetic: true` to distinguish from actual tracked jumps
- Set `timestamp: null` (unknown when jumps occurred)
- Copy system info from planned route
- Mark as `on_route: true` and `expected: true`

**Alternative (simpler):** Don't fill history, just mark gap and continue from player's actual position.

---

## 7. Route Transitions

**Decision:** Context-dependent behavior.

**While TRAVELING (expedition active):**
- Seamless auto-switching at links
- No prompts, no user interaction
- Copy next system from new route immediately

**While EDITING (creating expedition):**
- Explicit route transitions in UI
- Visual indicators of links
- Preview path before starting

**Link traversal logic:**
- Check if last tracked position has an outgoing link (only if currently on-route, not during deviations)
- If link exists: seamlessly switch to linked route (new route_id and jump_index recorded in jump_history)
- Copy next expected system from new route to clipboard
- No user prompts or confirmations during travel

---

## 8. Route Mutability

**Decision:** Routes are immutable.

**Why:**
- "Typo in destination" = Can't happen (plotter validates at generation)
- "Regenerate with different ship" = Need new route/expedition anyway
- "Add a detour":
  - While planning: Create new route for detour, link it to main route
  - While traveling (active): Just take it, deviation tracking handles return to route

**Benefits:**
- No cache invalidation
- No expedition corruption
- No versioning complexity
- Routes are reproducible snapshots

**If user wants changes:** Generate new route, create new expedition (or add to existing expedition as new route).

---

## Link Structure

Links connect **identical systems** (same physical system in both routes).

```python
link = {
    "id": "link_1",

    # Connection point (source of truth)
    "system_name": "Sol",    # Display
    "system_id": 12345,      # MUST match in both routes

    # Link endpoints
    "from": {
        "route_id": "uuid_A",
        "jump_index": 20,    # Cache: where Sol appears in Route A
    },
    "to": {
        "route_id": "uuid_B",
        "jump_index": 5,     # Cache: where Sol appears in Route B
    }
}
```

**Jump index caching:** The `jump_index` values are cached lookups for performance. When using a link, verify `routes[route_id].jumps[jump_index].system_id == link.system_id`. If mismatch, search route for system_id and update jump_index. If system not found, link is broken.

**Links are unidirectional (one-way).** Each link has a "from" and a "to". To create a circular route (A→B→A), you need **two separate links**: one from A to B, and another from B back to A. Circular routes trigger cycle detection warnings.

---

## Route Structure

```python
route = {
    "id": "uuid_A",
    "name": "Bubble → Beagle Point",

    # Plotter info
    "plotter": "spansh",
    "plotter_parameters": { /* see section 3 */ },
    "plotter_metadata": {
        "job_id": "abc123",
        "api_version": "v2.3",
    },

    # Jumps
    "jumps": [
        {
            "system_name": "Sol",
            "system_id": 12345,
            "scoopable": True,
            "distance": 0,  # From previous (0 for first)
            "fuel_in_tank": 16.0,  # Optional
            "fuel_used": 0,         # Optional
            "overcharge": False,    # Optional
            "position": {"x": 0, "y": 0, "z": 0},  # Optional
            # ... other optional fields
        }
    ],

    # Metadata
    "created_at": "2025-12-08T10:00:00Z",
}
```

---

## Expedition Structure

```python
expedition = {
    "id": "uuid_123",
    "name": "Trip to Beagle Point",
    "created_at": "2025-12-08T10:00:00Z",
    "last_updated": "2025-12-08T15:30:00Z",
    "status": "active",  # planned | active | completed | ended

    # Start point (can be mid-route)
    "start": {
        "route_id": "uuid_A",
        "system_name": "Colonia",
        "system_id": 12345,
        "jump_index": 35, # Cache: Must we validated. Just like links.
    },

    # All routes in this expedition (library)
    "routes": ["uuid_A", "uuid_B", "uuid_C"],

    # Links between routes
    "links": [
        {
            "id": "link_1",
            "system_name": "Sol",
            "system_id": 12345,
            "from": {"route_id": "uuid_A", "jump_index": 20},
            "to": {"route_id": "uuid_B", "jump_index": 5},
        }
    ],

    # Baked route (only exists when active/completed/ended)
    "baked_route": [ /* see Baked Route section */ ],
    "current_baked_index": 0,  # Index in baked_route of last completed jump
    "baked_loop_back_index": None,  # Index to jump back to when reaching end (None for non-circular routes)

    # Complete jump history (last tracked position computed from last entry)
    "jump_history": [ /* see section 1 */ ],

    # Statistics
    "stats": { /* see section 1 */ },
}
```

---

## Expedition State Machine

**States:**
- `planned` - Expedition is being designed, not started yet. Fully mutable (can edit routes, links, start point).
- `active` - Expedition is in progress. Immutable structure (routes/links locked), jump history actively recording. Only ONE active expedition allowed at a time.
- `completed` - Expedition reached its end (no next jump available). Immutable historical record.
- `ended` - Expedition manually stopped before completion. Immutable historical record.

**State Transitions:**

`planned` → `active`:
- Trigger: User clicks "Start Expedition"
- Action:
  - **Bake the route:** Pre-compute complete path through graph, store as `baked_route`
  - **Detect cycles:** If path loops back, store `baked_loop_back_index` (see Baked Route section)
  - Lock expedition structure (no more editing routes/links)
  - Initialize `current_baked_index` to -1 (no jumps completed yet)
  - Start tracking jumps in history
  - If not at start position: first jump marked as deviation (missing jumps detection handles this)
- If another expedition is already active: prompt user "Stop current expedition and start this one?"

`active` → `completed`:
- Trigger: Auto-detect when `current_baked_index == len(baked_route) - 1` AND `baked_loop_back_index is None` (reached end of non-circular path)
- Action: Set status to completed, archive expedition
- Stop auto-copy to clipboard
- Show "Expedition Complete" notification
- **Note:** Circular routes (with `baked_loop_back_index` set) never auto-complete - must be manually ended

`active` → `ended`:
- Trigger: Manual "Stop Expedition" button
- Action: Show confirmation dialog: "Stop expedition? Progress will be saved but you cannot resume."
- Set status to ended, archive expedition
- Stop auto-copy to clipboard

**No reverse transitions:** Once `active`, `completed`, or `ended`, cannot return to `planned` or `active`. These are permanent historical records.

**Multi-expedition rules:**
- Multiple `planned` expeditions: ✅ Allowed (can plan several trips)
- Multiple `active` expeditions: ❌ Only ONE active at a time
- Multiple `completed`/`ended` expeditions: ✅ Unlimited (historical archive)
- Starting new expedition when one is active: Prompt to stop current first

**Immutability:**
- `planned`: Fully mutable (add/remove routes, edit links, change start point, etc.)
- `active`/`completed`/`ended`: Immutable (preserves historical record, no editing allowed)

**Special cases:**
- **Circular routes:** Detected during baking via `baked_loop_back_index`. When reaching end of baked route, position wraps back to loop start and continues infinitely. Never auto-complete - must be manually ended.
- **Clone feature (nice to have, not v1):** Allow copying any expedition → new `planned` copy with fresh ID.

---

## Edge Cases - Decided

**1. System appears multiple times in route:**
- Valid. Each occurrence can have different link.
- Link identified by: `(system_id, from_route_id, from_jump_index, to_route_id, to_jump_index)`
- Validation: system_id must match at both jump indices

**2. Circular links (A→B→A):**
- Allowed but warn user
- Cycle detection on link creation
- Valid use cases: farming, patrol routes

**3. Links from/to middle of route:**
- Fully supported
- Links specify exact jump_index
- UI shows "Starting Route B at jump 25/100"

**4. Multiple links from same position:**
- NOT ALLOWED (enforced by validation)
- Path must be unambiguous

**5. Unlinked routes:**
- Allowed (routes are a library)
- Can add routes without links (alternative paths, emergency reroutes)

**6. Empty routes / Single-jump routes:**
- **Empty routes (0 jumps):** NOT ALLOWED - useless and require extra handling
- **Single-jump routes (1 jump):** Allowed (valid edge case, e.g., waypoint markers)

---

## Key Decisions Summary

| Question | Decision |
|----------|----------|
| **Expedition states?** | planned, active, completed, ended |
| **Expedition mutability?** | Mutable in planned, immutable after |
| **Multiple active expeditions?** | One only (multiple planned/completed allowed) |
| **Ship changes mid-expedition?** | Consider impossible for v1 |
| **Route validation?** | Links only, trust plotter for everything else |
| **Deviation handling?** | Track all jumps, mark deviations, no recovery |
| **Auto-copy timing?** | Immediately after FSDJump (may refine) |
| **Route transitions?** | Seamless during travel, explicit during editing |
| **Manual route switching?** | Editing only (not during travel) |
| **Save frequency?** | After every FSDJump |
| **Multi-session?** | Auto-handled by save frequency |
| **Route mutability?** | Immutable (always) |
| **Circular routes?** | Allow with warning |
| **Expedition complete?** | No next jump available (auto-transition to completed) |

---

## v1 Scope

**In scope:**
- Spansh plotter only
- Expedition state machine (planned/active/completed/ended)
- Single active expedition (multiple planned/completed allowed)
- Immutable routes (always)
- Mutable expeditions (only in planned state)
- Basic link validation
- Complete jump tracking
- Auto-copy to clipboard
- JSON file storage
- Deviation tracking

**Out of scope (future):**
- Multiple plotter support
- Multi-device sync
- Expedition cloning (nice to have)
- Route editing/versioning
- Ship change detection
- Advanced validation (fuel, range, permits)
- Emergency route recovery
- Galaxy update handling

---

## Implementation Notes

**Thread safety:** Use existing Model pattern (`with self.lock:`)

**Journal integration:** Extend JournalController with expedition logic

**Clipboard:** Use existing `EDXD/utils/clipboard.py`

**File I/O:** Use pathlib.Path, follow existing APP_DIR pattern

**Error handling:** Use existing log_context() pattern

**Constants:** Define in globals.py:
- `EXPEDITIONS_DIR = APP_DIR / "expeditions"`
- `ROUTES_DIR = EXPEDITIONS_DIR / "routes"`
- `EXPEDITIONS_INDEX = EXPEDITIONS_DIR / "index.json"`

---

## Open Questions (Low Priority for v1)

**Q11: Galaxy updates handling**
- Star class changes (very rare)
- New permits (occasional)
- **v1 approach:** Don't handle. If route breaks, user generates new route.

---

## Reference

For detailed analysis, edge cases, and full rationale for each decision, see `SPEC_REVIEW.md`.
