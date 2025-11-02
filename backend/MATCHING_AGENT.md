# Matching Agent

This is an AI-powered seating arrangement agent built with LangGraph and Google's Gemini 2.0 Flash model.

## Overview

The matching agent finds the best seat match for event attendees based on their facts, opinions, and a configurable "chaos level."

### How It Works

1. **Input**: Takes an attendee's facts and opinions, plus a chaos level (0-10)
2. **Search Strategy**: 
   - **Low Chaos (0-3)**: Finds similar people for harmonious seating
   - **Medium Chaos (4-6)**: Finds moderately different people for diversity
   - **High Chaos (7-10)**: Finds opposite people to maximize disagreement
3. **Single Search**: Makes one strategic search to find the best match
4. **Structured Output**: Returns the best matched attendee ID with reasoning and confidence score

## Setup

### 1. Install Dependencies

```bash
cd backend
uv pip install -r pyproject.toml
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory:

```bash
cp .env.example .env
```

Edit `.env` and add your Google API key:

```
GOOGLE_API_KEY=your_actual_google_api_key_here
DATABASE_URL=postgresql+asyncpg://user:password@localhost/dbname
```

### 3. Get a Google API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy it to your `.env` file

## Usage

### Via API Endpoint

The agent is integrated into the FastAPI backend. Use the endpoint:

```bash
POST /api/events/{event_id}/find_match/{attendee_id}
```

**Example:**

```bash
curl -X POST "http://localhost:8000/api/events/1/find_match/5"
```

**Response:**

```json
{
  "attendee_id": 5,
  "matched_with": 12,
  "reasoning": "Both attendees share interests in hiking and technology, making them compatible seat partners",
  "confidence": 0.85,
  "chaos_level": 2.0
}
```

### Programmatically

```python
from app.matching_agent import MatchingAgent

# Initialize the agent
agent = MatchingAgent()

# Find a match
result = await agent.find_match(
    attendee_id=1,
    facts=["Loves dogs", "Enjoys hiking", "Works in tech"],
    opinions=[
        {"question": "Favorite food?", "answer": "Pizza"},
        {"question": "Morning person?", "answer": "Yes"}
    ],
    chaos_level=2.0  # Low chaos - harmonious seating
)

print(f"Best match: Attendee {result.attendee_id}")
print(f"Reasoning: {result.reasoning}")
print(f"Confidence: {result.confidence}")
```

## Architecture

### Components

1. **MatchingAgent**: Main agent class that orchestrates the matching process
2. **Vector Database Tools**: 
   - `search_similar_attendees`: Finds similar people (low chaos)
   - `search_opposite_attendees`: Finds opposite people (high chaos)
3. **LangGraph Workflow**: State machine that manages the search process
4. **Structured Output**: Uses Pydantic models for type-safe results

### Agent Flow

```
START → Agent Reasoning → Tool Execution → Finalize → END
```

### Vector Database

The agent uses PostgreSQL with pgvector extension for semantic search:
- Embeddings are generated using Gemini's `text-embedding-004` model (768 dimensions)
- Cosine similarity is used for matching
- Negative embeddings are used for finding opposites (high chaos)

## Chaos Level Guide

| Level | Strategy | Use Case |
|-------|----------|----------|
| 0-3 | Similar interests, harmonious | Corporate events, networking |
| 4-6 | Moderate diversity | Social mixers, team building |
| 7-10 | Maximum disagreement | Debate events, intentional chaos |

## Customization

### Adjusting Search Parameters

Edit `matching_agent.py`:

```python
# Change maximum search iterations (default: 1)
if state["search_count"] >= 1:  # Change this value
```

### Using Different Models

```python
# Change the Gemini model
self.llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-exp",  # Try gemini-pro, etc.
    temperature=0.7  # Adjust creativity
)
```

## Testing

Run the example script:

```bash
cd backend
python -m app.matching_agent
```

## Troubleshooting

### "GOOGLE_API_KEY not found"
- Ensure `.env` file exists in `backend/` directory
- Check that `python-dotenv` is installed
- Verify the key is valid at [Google AI Studio](https://makersuite.google.com/)

### "No suitable match found"
- Ensure the vector database has embeddings for other attendees
- Check that facts/opinions have been added to attendees
- Verify pgvector extension is enabled in PostgreSQL

### Low confidence scores
- Add more facts and opinions to attendees
- Ensure embeddings are generated for all facts
- Try adjusting the chaos level

## Performance

- **Search time**: ~2-5 seconds per match (depends on iterations)
- **Token usage**: ~1000-3000 tokens per match
- **Cost**: ~$0.001-0.003 per match (Gemini 2.0 Flash pricing)

## Next Steps

- [ ] Add caching for repeated searches
- [ ] Implement batch matching for entire events
- [ ] Add custom weighting for facts vs opinions
- [ ] Support multi-table optimization
- [ ] Add explanation visualizations
