# Matcher Runner Documentation

## Overview

The `MatcherRunner` orchestrates the complete seating allocation process for an event. It:
1. Fetches all attendees marked as "going" for an event
2. Matches attendees into pairs using the AI matching agent
3. Allocates seats sequentially across tables
4. Updates the database with seat assignments

## Architecture

### Component Flow

```
MatcherRunner.run(event_id)
    │
    ├─► get_event() ─────► Fetch event details
    │
    ├─► get_attendees() ─► Fetch all attendees (going=True)
    │
    ├─► match_pairs() ───┬─► Loop through unallocated attendees
    │                    │
    │                    ├─► get_attendee_data() ─► Fetch facts & opinions
    │                    │
    │                    ├─► agent.find_match() ─► AI matching with exclusions
    │                    │
    │                    └─► Create (attendee1, attendee2) pairs
    │
    └─► allocate_seats() ─► Assign table_no & seat_no sequentially
```

### Key Algorithm: Exclusion-Based Pairing

The matching algorithm uses a **set-based exclusion strategy**:

```python
all_attendee_ids = {1, 2, 3, 4, 5, 6}  # All attendees
unallocated = {1, 2, 3, 4, 5, 6}        # Start with all unallocated

# Iteration 1: Match attendee 1
excluded = all_attendee_ids - unallocated  # {} (empty)
match = agent.find_match(1, exclude_attendee_ids=[])
# Result: 1 matched with 3
unallocated = {2, 4, 5, 6}  # Remove 1 and 3

# Iteration 2: Match attendee 2
excluded = all_attendee_ids - unallocated  # {1, 3}
match = agent.find_match(2, exclude_attendee_ids=[1, 3])
# Result: 2 matched with 5
unallocated = {4, 6}  # Remove 2 and 5

# Iteration 3: Match attendee 4
excluded = all_attendee_ids - unallocated  # {1, 2, 3, 5}
match = agent.find_match(4, exclude_attendee_ids=[1, 2, 3, 5])
# Result: 4 matched with 6
unallocated = {}  # All paired!
```

### Seat Allocation Strategy

Seats are allocated **sequentially** across tables:

```
Event: 3 tables, 4 people per table = 12 seats

Pairs: [(1,2), (3,4), (5,6), (7,8), (9,10), (11,12)]

Allocation:
  Table 0: [1, 2, 3, 4]      (seats 0-3)
  Table 1: [5, 6, 7, 8]      (seats 0-3)
  Table 2: [9, 10, 11, 12]   (seats 0-3)
```

Formula:
- `table_no = seat_index // ppl_per_table`
- `seat_no = seat_index % ppl_per_table`

## Usage

### 1. Command Line (Test Script)

```bash
cd backend
uv run python test_matcher_runner.py
```

**Interactive prompts:**
```
Enter event ID to process: 1
Enable verbose mode? (y/n) [default: y]: y

Running matcher for event 1...
Verbose mode: ON
```

**Output:**
```
============================================================
STARTING MATCHER RUNNER FOR EVENT 1
============================================================
Event: Tech Conference 2025
Chaos Level: 3.5/10
Capacity: 5 tables, 8 per table = 40 total seats
Attendees going: 20

Matching attendee 1 (20 remaining, 0 excluded)
✓ Matched 1 with 5
  Reasoning: Both enjoy hiking and outdoor activities
  Confidence: 0.87

Matching attendee 2 (18 remaining, 2 excluded)
✓ Matched 2 with 9
  Reasoning: Similar tech interests and work backgrounds
  Confidence: 0.92

...

Matching complete: 10 pairs created
Allocating 20 attendees to seats...
Assigned attendee 1 (Alice) to table 0, seat 0
Assigned attendee 5 (Bob) to table 0, seat 1
...
✓ Seat allocation complete. Assigned 20 attendees to seats.

============================================================
RESULT SUMMARY
============================================================
✓ SUCCESS!
  Event: Tech Conference 2025
  Total attendees: 20
  Pairs created: 10
  Attendees seated: 20
  Unallocated: 0
```

### 2. API Endpoint

**Endpoint:** `POST /api/events/{event_id}/allocate_seats`

**Parameters:**
- `event_id` (path): ID of the event
- `verbose` (query, optional): Enable verbose logging (default: false)

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/events/1/allocate_seats?verbose=true"
```

**Success Response (200):**
```json
{
  "success": true,
  "event_id": 1,
  "event_name": "Tech Conference 2025",
  "attendees_count": 20,
  "pairs_created": 10,
  "attendees_seated": 20,
  "attendees_unallocated": 0
}
```

**Error Response (400):**
```json
{
  "detail": "Need at least 2 attendees for pairing"
}
```

### 3. Python API

```python
import asyncio
from app.matcher_runner import MatcherRunner

async def allocate_event_seats():
    runner = MatcherRunner(verbose=True)
    result = await runner.run(event_id=1)
    
    if result["success"]:
        print(f"✓ Seated {result['attendees_seated']} attendees")
    else:
        print(f"✗ Error: {result['error']}")

asyncio.run(allocate_event_seats())
```

## API Reference

### MatcherRunner

#### `__init__(verbose: bool = False)`
Initialize the matcher runner.

**Args:**
- `verbose`: Enable verbose logging for agent operations

#### `async run(event_id: int) -> dict`
Run the complete matching and allocation process.

**Args:**
- `event_id`: ID of the event to process

**Returns:**
```python
{
    "success": bool,
    "event_id": int,
    "event_name": str,
    "attendees_count": int,
    "pairs_created": int,
    "attendees_seated": int,
    "attendees_unallocated": int
}
```

**On Error:**
```python
{
    "success": False,
    "error": str,
    "attendees_count": int,  # May be present
    "pairs_created": int     # May be present
}
```

#### `async match_pairs(event_id, chaos_level, session) -> List[Tuple[int, int]]`
Match all attendees into pairs using the AI agent.

**Returns:** List of `(attendee_id_1, attendee_id_2)` tuples

#### `async allocate_seats(pairs, event, session) -> None`
Allocate seats to pairs sequentially and update database.

## Error Handling

### Event Not Found
```python
{
    "success": False,
    "error": "Event 999 not found"
}
```

### Insufficient Attendees
```python
{
    "success": False,
    "error": "Need at least 2 attendees for pairing",
    "attendees_count": 1
}
```

### No Pairs Created
```python
{
    "success": False,
    "error": "No pairs could be created",
    "attendees_count": 10,
    "pairs_created": 0
}
```

### Attendee Missing Data
**Behavior:** Skipped with warning, continues with others
```
WARNING: Attendee 42 has no facts or opinions. Skipping.
```

### Invalid Match Returned
**Behavior:** Skip current attendee, log error, continue
```
ERROR: Agent returned invalid match: 99 (not in unallocated set)
```

### Capacity Exceeded
**Behavior:** Seats as many as possible, logs warning
```
WARNING: Not enough capacity! Need 50 seats, have 40
ERROR: Ran out of tables! Cannot seat attendee 45
```

## Performance Characteristics

### Time Complexity
- **Pairing:** O(n) attendees × O(m) vector search
  - n = number of attendees
  - m = average vector DB query time (~50-100ms)
  - Total: ~1-2 seconds per attendee = 20-40 seconds for 20 attendees

- **Seat Allocation:** O(n) database updates
  - Linear with number of attendees
  - Bulk commit: ~100-500ms for 20 attendees

**Total Runtime:** ~20-40 seconds for 20 attendees (with verbose mode)

### API Rate Limits
Each pairing requires:
- 1 embedding API call (for query)
- 2-3 Gemini LLM calls (agent reasoning + structured output)

**Total:** ~3-4 API calls per pair = 30-40 calls for 10 pairs

**Recommendation:** For events with >10 pairs (20+ attendees), ensure:
- Gemini API paid tier (no 10 req/min limit)
- Or add delays between matches

### Database Queries
- **Per attendee match:** 
  - 1 fact fetch query
  - 1 opinion fetch query
  - 1 vector similarity search
  
- **Seat allocation:**
  - 1 UPDATE per attendee
  - 1 COMMIT for all updates (bulk)

**Total:** ~3n + 2 queries for n attendees

## Edge Cases

### Odd Number of Attendees
```python
# 5 attendees: pairs = [(1,2), (3,4)], unallocated = [5]
{
    "attendees_count": 5,
    "pairs_created": 2,
    "attendees_seated": 4,
    "attendees_unallocated": 1  # ← One person unpaired
}
```

### Single Attendee
```python
{
    "success": False,
    "error": "Need at least 2 attendees for pairing",
    "attendees_count": 1
}
```

### All Attendees Already Seated
**Behavior:** Overwrites existing seat assignments

### No Attendees Marked as "Going"
```python
{
    "success": False,
    "error": "Need at least 2 attendees for pairing",
    "attendees_count": 0
}
```

## Configuration

### Event Settings
From `Event` model:
- `chaos_temp`: Matching strategy (0=harmony, 10=chaos)
- `total_tables`: Number of tables available
- `ppl_per_table`: Seats per table

### Attendee Filtering
Only attendees with `going=True` are matched.

To change filter criteria, modify:
```python
# In MatcherRunner.get_attendees()
query = (
    select(EventAttendee)
    .where(EventAttendee.event_id == event_id)
    .where(EventAttendee.going == True)  # ← Modify this
)
```

## Logging

### Log Levels

**INFO:** High-level progress
```
INFO: Starting pairing for 20 attendees
INFO: Matching attendee 1 (20 remaining, 0 excluded)
INFO: ✓ Matched 1 with 5
INFO: Matching complete: 10 pairs created
```

**DEBUG:** Detailed operations (from agent with verbose=True)
```
DEBUG: Searching similar attendees for query: Loves hiking
DEBUG: Found 8 similar attendees
```

**WARNING:** Non-fatal issues
```
WARNING: Attendee 42 has no facts or opinions. Skipping.
WARNING: Odd number of attendees. [5] will be unallocated.
WARNING: Not enough capacity! Need 50 seats, have 40
```

**ERROR:** Failures that skip operations
```
ERROR: Agent returned invalid match: 99 (not in unallocated set)
ERROR: Attendee 123 not found in database
ERROR: Ran out of tables! Cannot seat attendee 45
```

## Testing

### Manual Test
```bash
cd backend
uv run python test_matcher_runner.py
```

### Integration Test
```python
import pytest
from app.matcher_runner import MatcherRunner

@pytest.mark.asyncio
async def test_matcher_runner():
    runner = MatcherRunner(verbose=False)
    result = await runner.run(event_id=1)
    
    assert result["success"] is True
    assert result["pairs_created"] > 0
    assert result["attendees_seated"] == result["pairs_created"] * 2
```

### API Test
```bash
# Start server
cd backend
uv run uvicorn app.main:app --reload

# Test endpoint
curl -X POST "http://localhost:8000/api/events/1/allocate_seats?verbose=false"
```

## Troubleshooting

### "No match found for attendee X"
**Cause:** Agent couldn't find suitable match (all others excluded or low similarity)

**Solution:** 
- Check if attendee has facts/opinions
- Verify other attendees have data
- Lower `min_similarity` threshold in matcher.py

### "Agent returned invalid match"
**Cause:** Agent returned ID not in unallocated set (bug in agent logic)

**Solution:**
- Check agent's structured output validation
- Ensure exclusion list passed correctly
- Review agent logs with verbose=True

### Rate Limit Errors
**Cause:** Too many API calls to Gemini

**Solution:**
- Use paid API tier
- Add delays: `await asyncio.sleep(1)` between matches
- Reduce attendee count for testing

### Database Lock Errors
**Cause:** Concurrent modifications to same records

**Solution:**
- Run matcher runner sequentially (not parallel)
- Use proper transaction isolation

## Future Enhancements

1. **Batch Matching:** Match multiple pairs in parallel (with rate limiting)
2. **Undo/Redo:** Save previous allocations before overwriting
3. **Partial Allocation:** Resume from existing pairs
4. **Custom Strategies:** Support different seating patterns (e.g., alternating tables)
5. **Constraints:** Honor special requests (sit together, sit apart)
6. **Optimization:** Re-arrange pairs to maximize table fill rate

## Files

- `/backend/app/matcher_runner.py` - Main implementation
- `/backend/test_matcher_runner.py` - Test script
- `/backend/app/routers/events.py` - API endpoint (`/allocate_seats`)
