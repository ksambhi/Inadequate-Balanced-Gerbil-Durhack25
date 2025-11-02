# Event Creation and Matching Demo

## Quick Start

Run the complete demo that creates an event, adds attendees with facts/opinions, runs the AI matcher, and displays the final seating allocation:

```bash
cd backend
uv run python create_and_run_event.py
```

## What It Does

1. **Creates an Event** with configurable chaos level and table settings
2. **Adds Attendees** with facts and opinions (including embeddings)
3. **Runs the AI Matcher** to pair attendees based on similarity/opposition
4. **Allocates Seats** sequentially across tables
5. **Displays Results** in a formatted table view

## Configuration

Edit `create_and_run_event.py` to customize:

### Event Settings

```python
EVENT_CONFIG = {
    "name": "AI Meetup 2025",
    "chaos_temp": 3.0,  # 0=harmony, 10=chaos
    "num_tables": 3,    # Auto-calculated if None
}
```

### Attendees

Add/modify attendees in `ATTENDEES_DATA`:

```python
{
    "name": "Alice",
    "email": "alice@example.com",
    "phone": "+1234567890",
    "facts": [
        "Loves hiking and outdoor adventures",
        "Works as a software engineer",
    ],
    "opinions": {
        "What's your favorite programming language?": "Python",
        "Coffee or tea?": "Coffee",
    }
}
```

## Safety Features

- **Validates minimum table size**: Stops if any table would have < 2 people
- **Auto-calculates tables**: Aims for 4-6 people per table if not specified
- **Handles odd numbers**: Last person marked as unallocated
- **Validates capacity**: Warns if not enough seats

## Example Output

```
============================================================
CREATING EVENT AND ATTENDEES
============================================================
Event: AI Meetup 2025
Chaos Level: 3.0/10
Attendees: 8
Tables: 3
People per table: 3
Minimum at last table: 2

✓ Created event ID: 1

✓ Created attendee: Alice (ID: 1)
  + Fact: Loves hiking and outdoor adventures
  + Fact: Works as a software engineer at a startup
  + Opinion: What's your favorite programming language? → Python

...

============================================================
STARTING MATCHER RUNNER FOR EVENT 1
============================================================
Matching attendee 1 (8 remaining, 0 excluded)
✓ Matched 1 with 2
  Reasoning: Both enjoy hiking and work in tech with Python
  Confidence: 0.89

...

============================================================
FINAL SEATING ALLOCATION
============================================================

Event: AI Meetup 2025
Chaos Level: 3.0/10

Table 0:
  Seat 0: Alice (alice@example.com)
  Seat 1: Bob (bob@example.com)
  Seat 2: Eve (eve@example.com)

Table 1:
  Seat 0: Carol (carol@example.com)
  Seat 1: David (david@example.com)
  Seat 2: Grace (grace@example.com)

Table 2:
  Seat 0: Frank (frank@example.com)
  Seat 1: Henry (henry@example.com)

Statistics:
  Total attendees: 8
  Seated: 8
  Unallocated: 0
  Tables used: 3/3
```

## Customization Tips

### Change Chaos Level
- `0-3`: Harmonious (similar interests)
- `4-6`: Balanced (some diversity)
- `7-10`: Chaotic (opposite views)

### Add More Attendees
Just append to `ATTENDEES_DATA` list. The script will:
- Auto-calculate optimal table count
- Validate minimum table occupancy
- Generate embeddings for all facts

### Custom Opinion Questions
Add any questions you want:
```python
"opinions": {
    "Favorite movie genre?": "Sci-fi",
    "Introvert or extrovert?": "Ambivert",
    "Favorite season?": "Fall"
}
```

## Troubleshooting

### "Would result in table with < 2 people"
**Cause:** Current table configuration leaves last table with 0-1 person

**Solution:** 
- Reduce `num_tables` in `EVENT_CONFIG`
- Or add more attendees
- Script will suggest optimal table count

### Rate Limit Errors
**Cause:** Too many embedding API calls

**Solution:**
- Use paid Gemini API tier
- Reduce number of attendees for testing
- Add delays between operations

### Database Errors
**Cause:** Database not initialized

**Solution:**
```bash
cd backend
uv run alembic upgrade head
```
