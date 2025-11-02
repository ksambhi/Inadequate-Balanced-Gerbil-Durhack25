# Agent Search Limit Fix

## Problem
The agent was making more than 3 search queries, exceeding the intended limit.

## Root Cause
The `_should_continue()` logic was checking if the LLM called tools BEFORE checking the search attempt limit. This meant:
1. LLM calls a tool
2. Check passes → "continue"  
3. Tool executes (search_attempts increments to 3)
4. LLM calls another tool
5. Check passes → "continue" again (bypass limit!)
6. Tool executes (search_attempts becomes 4+)

## Solution

### 1. Reordered the logic in `_should_continue()`

```python
def _should_continue(self, state: MatchingAgentState) -> str:
    search_attempts = state.get("search_attempts", 0)
    
    # HARD LIMIT: Check attempts FIRST
    if search_attempts >= 3:
        return "finalize"
    
    # Then check if LLM wants to call tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "continue"
    
    # ... rest of logic
```

**Key Change**: The search attempt limit is now checked **BEFORE** allowing tool execution.

### 2. Updated the prompt

Added explicit instructions:
```
IMPORTANT: You can make a MAXIMUM of 3 searches total.
After your search returns results, DO NOT call tools again.
Let the system finalize the match.
```

## Behavior Now

- **Search 1**: Agent makes first query
- **Search 2**: If no results, agent tries different query
- **Search 3**: If still no results, agent tries final query
- **After 3 searches**: System FORCES finalization regardless of what LLM wants

### Example Flow

```
Attempt 1: Search for "loves hiking" → 0 results
Attempt 2: Search for "software engineer" → 0 results  
Attempt 3: Search for "Python developer" → 2 results found
→ FINALIZE with best of 2 candidates

OR

Attempt 1: Search query → 0 results
Attempt 2: Search query → 0 results
Attempt 3: Search query → 0 results
→ FINALIZE with no match (attendee_id=-1)
```

## Testing

Run the demo to verify:
```bash
cd backend
uv run python create_and_run_event.py
```

Watch the logs for:
```
→ Executing tools (attempt 1/3)...
→ Executing tools (attempt 2/3)...
→ Executing tools (attempt 3/3)...
✓ Hit 3 search limit with X candidates, finalizing...
```

The agent will never go beyond attempt 3.
