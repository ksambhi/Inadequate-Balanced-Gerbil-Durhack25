# Background Matching API Endpoint

## Overview

Added a new API endpoint that starts the matcher in the background and returns `202 Accepted` immediately. This allows the matching process to run asynchronously without blocking the client.

## Endpoint

```
POST /api/events/{event_id}/start_matching
```

### Parameters
- `event_id` (path): ID of the event to match

### Response
- **Status Code**: `202 Accepted` - Request accepted and processing in background
- **Body**:
  ```json
  {
    "status": "accepted",
    "message": "Matching process started for event 1. Check logs for progress.",
    "event_id": 1,
    "event_name": "AI Meetup 2025"
  }
  ```

### Error Responses
- **404 Not Found**: Event with given ID doesn't exist
  ```json
  {
    "detail": "Event with id 999 not found"
  }
  ```

## How It Works

1. **Validates** the event exists in the database
2. **Starts background task** using FastAPI's `BackgroundTasks`
3. **Returns immediately** with 202 status
4. **Background process** runs the complete matching workflow:
   - Fetches all attendees for the event
   - Matches them into pairs using the AI agent (with retry logic)
   - Allocates seats sequentially
   - Updates database with assignments
   - Logs all progress (similar to `create_and_run_event.py`)

## Usage Examples

### Using curl

```bash
# Start matching for event ID 1
curl -X POST "http://localhost:8000/api/events/1/start_matching"

# Response (immediate):
# {
#   "status": "accepted",
#   "message": "Matching process started for event 1. Check logs for progress.",
#   "event_id": 1,
#   "event_name": "AI Meetup 2025"
# }
```

### Using Python requests

```python
import requests

response = requests.post("http://localhost:8000/api/events/1/start_matching")

print(f"Status: {response.status_code}")  # 202
print(f"Response: {response.json()}")

# Continue with other work while matching runs in background
```

### Using the existing test script

First create an event with attendees:

```bash
cd backend
uv run python create_and_run_event.py
```

Then you can trigger matching again via the API:

```bash
curl -X POST "http://localhost:8000/api/events/1/start_matching"
```

## Logging

The background task logs output similar to `create_and_run_event.py`:

```
============================================================
STARTING BACKGROUND MATCHER FOR EVENT 1
============================================================
Event: AI Meetup 2025
Chaos Level: 5.0/10
Capacity: 3 tables, 3 per table = 9 total seats
Attendees going: 8

Matching attendee 1 (8 remaining, 0 excluded)
🚀 ==========================================================
STARTING MATCHING AGENT
============================================================
Attendee ID: 1
Event ID: 1
Facts: 3
Opinions: 3
Chaos Level: 5.0/10
Excluded: 0 attendees
============================================================

[... matching process ...]

✓ Matched 1 with 2
  Reasoning: Both enjoy hiking and work in tech
  Confidence: 0.85

[... continues for all pairs ...]

============================================================
MATCHING COMPLETE
============================================================
Event: AI Meetup 2025 (ID: 1)
Attendees: 8
Pairs created: 4
People seated: 8
============================================================
```

## Comparison with Existing Endpoint

| Feature | `/allocate_seats` | `/start_matching` (NEW) |
|---------|-------------------|-------------------------|
| **Execution** | Synchronous | Asynchronous (background) |
| **Response Time** | Waits for completion | Immediate (202) |
| **Status Code** | 200 (success) or 400 (error) | 202 (accepted) |
| **Use Case** | Small events, testing | Production, large events |
| **Timeout Risk** | Yes (long-running) | No (runs in background) |
| **Progress Tracking** | Return value only | Check logs |
| **Verbose Option** | Yes (query param) | Always verbose |

## Benefits

✅ **Non-blocking**: Client doesn't have to wait for matching to complete  
✅ **No timeouts**: Long-running matches won't timeout HTTP requests  
✅ **Better UX**: Can show "processing" state in UI  
✅ **Detailed logs**: Full verbose logging like the test script  
✅ **Production-ready**: Suitable for real-world deployments  
✅ **Event isolation**: Uses event_id filtering (only matches within same event)  

## Monitoring Progress

Since the process runs in the background, monitor progress through:

1. **Server logs** - Full verbose output with reasoning and confidence scores
2. **Database queries** - Check `EventAttendee.table_no` and `seat_no` fields
3. **Additional endpoint** - Could add `/events/{id}/matching_status` endpoint (future enhancement)

## Example Workflow

```python
# 1. Create event and attendees (via your UI/API)
event_id = create_event_with_attendees()

# 2. Start matching in background
response = requests.post(f"http://localhost:8000/api/events/{event_id}/start_matching")
assert response.status_code == 202

# 3. Show "Processing..." in UI
print("Matching in progress...")

# 4. Poll or wait for completion (check database)
import time
time.sleep(10)  # Or poll database for seat assignments

# 5. Fetch final allocation
allocation = requests.get(f"http://localhost:8000/api/events/{event_id}/attendees")
print(f"Seating complete: {allocation.json()}")
```

## Testing

```bash
# Terminal 1: Start FastAPI server
cd backend
uv run uvicorn app.main:app --reload

# Terminal 2: Create test event
cd backend
uv run python create_and_run_event.py

# Terminal 3: Trigger background matching via API
curl -X POST "http://localhost:8000/api/events/1/start_matching"

# Watch Terminal 1 for detailed matching logs
```
