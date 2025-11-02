# Event ID Filtering for Matching

## Problem
The matching agent was searching across ALL attendees in the database, potentially matching people from different events together.

## Solution
Added `event_id` filtering throughout the matching pipeline to ensure attendees are only matched with others from the same event.

## Changes Made

### 1. Updated `MatchingAgentState` (matching_agent.py)
```python
class MatchingAgentState(MessagesState):
    attendee_id: int
    event_id: int  # NEW: Filter matches to same event only
    facts: List[str]
    opinions: List[Dict[str, str]]
    chaos_level: float
    exclude_attendee_ids: List[int]
    # ... internal state
```

### 2. Updated Search Tools (matching_agent.py)
Both `search_similar_attendees` and `search_opposite_attendees` now accept `event_id`:

```python
@tool
async def search_similar_attendees(
    query_text: str,
    attendee_id: int,
    event_id: int,  # NEW parameter
    exclude_attendee_ids: List[int],
    limit: int = 10
) -> List[Dict[str, Any]]:
    # Passes event_id to vector_db.search_similar()
```

### 3. Updated Tools Node (matching_agent.py)
Auto-injects `event_id` into tool arguments:

```python
async def _tools_node(self, state: MatchingAgentState) -> Dict[str, Any]:
    for tool_call in last_message.tool_calls:
        tool_args = tool_call["args"].copy()
        
        # Inject event_id and exclude_attendee_ids
        tool_args["event_id"] = state.get("event_id")
        tool_args["exclude_attendee_ids"] = state.get("exclude_attendee_ids", [])
```

### 4. Updated find_match() Method (matching_agent.py)
Now requires `event_id` parameter:

```python
async def find_match(
    self,
    attendee_id: int,
    event_id: int,  # NEW required parameter
    facts: List[str],
    opinions: List[Dict[str, str]],
    chaos_level: float,
    exclude_attendee_ids: Optional[List[int]] = None
) -> MatchResult:
```

### 5. Updated VectorDB.search_similar() (matcher.py)
Joins with `EventAttendee` table and filters by event:

```python
async def search_similar(
    self,
    query_embedding: List[float],
    limit: int = 10,
    event_id: Optional[int] = None,  # NEW parameter
    exclude_attendee_id: Optional[int] = None,
    exclude_attendee_ids: Optional[List[int]] = None,
    min_similarity: float = 0.0
) -> List[Tuple[int, str, float]]:
    
    from app.models import EventAttendee
    
    query = select(
        FactModel.attendee_id,
        FactModel.fact,
        (1 - FactModel.embedding.cosine_distance(query_embedding)).label('similarity')
    ).join(
        EventAttendee,
        FactModel.attendee_id == EventAttendee.id
    )
    
    # Filter by event_id if provided
    if event_id is not None:
        query = query.where(EventAttendee.event_id == event_id)
```

### 6. Updated VectorDB.search_opposite() (matcher.py)
Same changes as `search_similar()`:

```python
async def search_opposite(
    self,
    query_embedding: List[float],
    limit: int = 10,
    event_id: Optional[int] = None,  # NEW parameter
    exclude_attendee_id: Optional[int] = None,
    exclude_attendee_ids: Optional[List[int]] = None
) -> List[Tuple[int, str, float]]:
    # Same JOIN and WHERE clause as search_similar
```

### 7. Updated MatcherRunner (matcher_runner.py)
Passes `event_id` to agent:

```python
result = await self.agent.find_match(
    attendee_id=current_attendee_id,
    event_id=event_id,  # NEW parameter
    facts=facts,
    opinions=opinions,
    chaos_level=chaos_level,
    exclude_attendee_ids=excluded
)
```

## Data Flow

```
MatcherRunner.match_pairs(event_id=1)
    ↓
MatchingAgent.find_match(attendee_id=5, event_id=1, ...)
    ↓
initial_state = {..., "event_id": 1}
    ↓
_tools_node() auto-injects event_id into tool_args
    ↓
search_similar_attendees(query_text="...", event_id=1, ...)
    ↓
VectorDB.search_similar(event_id=1, ...)
    ↓
SQL: JOIN event_attendee WHERE event_attendee.event_id = 1
    ↓
Results: Only attendees from event 1
```

## Benefits

✅ **Isolation**: Each event's matching is completely isolated  
✅ **Correctness**: No cross-event contamination  
✅ **Database-level filtering**: Efficient SQL-level filtering  
✅ **Backwards compatible**: event_id is optional in VectorDB methods  

## Testing

The existing demo script automatically benefits from this change:

```bash
cd backend
uv run python create_and_run_event.py
```

All matches will now be guaranteed to be within the same event.

## Database Schema

This works with the existing schema where `EventAttendee` has `event_id`:

```python
class EventAttendee(Base):
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("event.id"))
    # ... other fields

class Fact(Base):
    id = Column(Integer, primary_key=True)
    attendee_id = Column(Integer, ForeignKey("event_attendee.id"))
    fact = Column(String)
    embedding = Column(Vector(768))
```

The JOIN connects: `Fact.attendee_id → EventAttendee.id → EventAttendee.event_id`
