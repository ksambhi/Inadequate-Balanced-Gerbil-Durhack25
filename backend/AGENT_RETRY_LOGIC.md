# Agent Retry Logic

## Overview

The matching agent now tries up to **3 different search queries** if it doesn't get any candidates back from the database. This ensures better matching success rates, especially when:
- The initial query is too specific
- There are many excluded attendees
- The event has diverse attendees with varied interests

## Changes Made

### 1. Added `search_attempts` to State

```python
class MatchingAgentState(MessagesState):
    # ... existing fields ...
    search_count: int          # Total searches executed
    search_attempts: int       # Number of unique query attempts (max 3)
    candidates: List[Dict]     # Accumulated candidates
```

### 2. Updated Agent Prompt

The agent now knows which attempt it's on and adjusts strategy:

- **Attempt 1**: Use the most prominent fact/opinion
- **Attempt 2**: Try a different fact or opinion  
- **Attempt 3**: Use a broader or more general query

### 3. Enhanced `_should_continue()` Logic

```python
def _should_continue(self, state: MatchingAgentState) -> str:
    # If no candidates and haven't tried 3 times yet, try again
    if not has_candidates and search_attempts < 3:
        return "continue"
    
    # If we have candidates OR tried 3 times, finalize
    if has_candidates or search_attempts >= 3:
        return "finalize"
```

### 4. Updated `_finalize_node()` for No Matches

When no candidates are found after 3 attempts:

```python
result = MatchResult(
    attendee_id=-1,
    reasoning="No suitable matches found after 3 search attempts",
    confidence=0.0
)
```

## Example Flow

### Scenario: Finding match for attendee with niche interests

**Attempt 1**: "Loves obscure indie films"
- Result: 0 candidates
- Action: Continue

**Attempt 2**: "Works as a cinematographer"  
- Result: 0 candidates
- Action: Continue

**Attempt 3**: "Enjoys creative arts"
- Result: 3 candidates found!
- Action: Finalize with best match

### Scenario: No matches after 3 attempts

**Attempt 1**: Very specific query → 0 results  
**Attempt 2**: Different angle → 0 results  
**Attempt 3**: Broad query → 0 results  
**Result**: Returns `attendee_id=-1` with explanation

## Rate Limit Compliance

With up to 3 attempts per attendee and a maximum of 10 API queries allowed:
- 3 queries per match attempt
- Safe for matching 2-3 attendees before hitting limits
- Each query uses a different strategy to maximize success

## Benefits

✅ **Better matching success**: Multiple strategies increase chances of finding compatible pairs  
✅ **Handles edge cases**: Works with diverse or niche attendee profiles  
✅ **Graceful failure**: Returns clear "no match" result instead of failing  
✅ **Efficient**: Stops early if candidates found on first or second attempt  
✅ **Verbose logging**: Tracks all attempts for debugging

## Testing

Run the demo script to see retry logic in action:

```bash
cd backend
uv run python create_and_run_event.py
```

Watch for log messages like:
```
No candidates found. Retrying (1/3 attempts)
Search attempts: 2/3, Total candidates: 0
✓ Found 3 candidates, finalizing...
```
