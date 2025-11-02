from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import os
import httpx
import logging

from app.database import get_db
from app.models import Event, EventAttendee, JoinedOpinion, Opinion, Fact
from app.matching_agent import MatchingAgent, MatchResult
from app.matcher_runner import MatcherRunner
from app.gemini_service import GeminiProcessor
from app.matcher import EmbeddingService

router = APIRouter(prefix="/api/events", tags=["events"])
logger = logging.getLogger(__name__)


class EventCreate(BaseModel):
    """Schema for creating a new event."""
    name: str
    total_tables: int
    ppl_per_table: int
    chaos_temp: float
    opinions: list[str] = []  # List of opinion questions for this event


class EventResponse(BaseModel):
    """Schema for event response."""
    id: int
    name: str
    total_tables: int
    ppl_per_table: int
    chaos_temp: float
    
    class Config:
        from_attributes = True


class AttendeeCreate(BaseModel):
    """Schema for creating an attendee."""
    name: str
    phone: str
    email: str


class OpinionAnswer(BaseModel):
    """Schema for opinion question and answer."""
    question: str
    answer: int


class AttendeeResponse(BaseModel):
    """Schema for attendee response."""
    id: int
    name: str
    phone: str
    email: str
    table_no: int | None
    seat_no: int | None
    event_id: int
    opinions: list[OpinionAnswer]
    rsvp_status: bool | None = None
    
    class Config:
        from_attributes = True


class AttendeeListRequest(BaseModel):
    """Schema for adding multiple attendees to an event."""
    attendees: list[AttendeeCreate]


API_KEY = os.getenv("API_KEY", "your_xi_api_key")
AGENT_ID = os.getenv("AGENT_ID", "your_agent_id")
PHONE_NUM_ID = os.getenv("PHONE_NUM_ID", "your_agent_phone_number_id")


def make_elevenlabs_call(to_number: str, user: str = None, event_name: str = None, event_id: str = None, user_id: str = None):
    url = "https://api.elevenlabs.io/v1/convai/twilio/outbound-call"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    dynamic_variables = {
        "user": user,
        "event_name": event_name,
        "event_id": event_id,
        "user_id": user_id
    }
    
    payload = {
        "agent_id": AGENT_ID,
        "agent_phone_number_id": PHONE_NUM_ID,
        "to_number": to_number,
        "conversation_initiation_client_data": {
            "dynamic_variables": dynamic_variables
        }
    }
    
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@router.get("/")
async def get_events():
    """Get all events."""
    return {"message": "events endpoint"}


@router.post("/create", response_model=EventResponse)
async def create_event(
    event_data: EventCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new event."""
    event = Event(
        name=event_data.name,
        total_tables=event_data.total_tables,
        ppl_per_table=event_data.ppl_per_table,
        chaos_temp=event_data.chaos_temp
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    
    # Create opinion questions for this event
    for opinion_text in event_data.opinions:
        opinion = Opinion(
            opinion=opinion_text,
            event_id=event.id
        )
        db.add(opinion)
    
    if event_data.opinions:
        await db.commit()
    
    return event


@router.get("/{event_id}/attendees", response_model=list[AttendeeResponse])
async def get_attendees(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all attendees for an event."""
    # Check if event exists
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Get all attendees for this event with their opinions eagerly loaded
    result = await db.execute(
        select(EventAttendee)
        .where(EventAttendee.event_id == event_id)
        .options(selectinload(EventAttendee.opinions))
    )
    attendees = result.scalars().all()
    
    # Transform attendees to include opinion details
    response = []
    for attendee in attendees:
        # Fetch opinion details for each joined opinion
        opinion_answers = []
        for joined_opinion in attendee.opinions:
            opinion_result = await db.execute(
                select(Opinion).where(Opinion.opinion_id == joined_opinion.opinion_id)
            )
            opinion = opinion_result.scalar_one_or_none()
            if opinion:
                opinion_answers.append({
                    "question": opinion.opinion,
                    "answer": joined_opinion.answer
                })
        
        response.append(AttendeeResponse(
            id=attendee.id,
            name=attendee.name,
            phone=attendee.phone,
            email=attendee.email,
            table_no=attendee.table_no,
            seat_no=attendee.seat_no,
            event_id=attendee.event_id,
            opinions=opinion_answers,
            rsvp_status=attendee.rsvp
        ))
    
    return response


@router.put("/{event_id}/attendees", response_model=list[AttendeeResponse])
async def add_attendees(
    event_id: int,
    data: AttendeeListRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add multiple attendees to an event."""
    # Check if event exists
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Create attendees
    created_attendees = []
    for attendee_data in data.attendees:
        attendee = EventAttendee(
            name=attendee_data.name,
            phone=attendee_data.phone,
            email=attendee_data.email,
            event_id=event_id,
            table_no=None,
            seat_no=None,
            rsvp=True,
            going=True,
        )
        db.add(attendee)
        created_attendees.append(attendee)
    
    await db.commit()
    
    # Refresh all attendees to get their IDs and load opinions
    response = []
    for attendee in created_attendees:
        await db.refresh(attendee)
        response.append(AttendeeResponse(
            id=attendee.id,
            name=attendee.name,
            phone=attendee.phone,
            email=attendee.email,
            table_no=attendee.table_no,
            seat_no=attendee.seat_no,
            event_id=attendee.event_id,
            opinions=[]  # New attendees have no opinions yet
        ))
    
    return response


@router.get("/{event_id}/count_rsvp")
async def count_rsvp(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Count attendees with RSVP true for an event."""
    # Check if event exists
    result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Count total attendees
    total_result = await db.execute(
        select(func.count(EventAttendee.id))
        .where(EventAttendee.event_id == event_id)
    )
    total_count = total_result.scalar()
    
    # Count attendees with rsvp = True
    rsvp_result = await db.execute(
        select(func.count(EventAttendee.id))
        .where(EventAttendee.event_id == event_id)
        .where(EventAttendee.rsvp == True)
    )
    rsvp_count = rsvp_result.scalar()
    
    # Calculate pending (not RSVPed)
    pending_count = total_count - rsvp_count
    
    return {
        "event_id": event_id,
        "rsvp_count": rsvp_count,
        "pending_count": pending_count
    }


@router.post("/{event_id}/call_attendees")
async def call_attendees(event_id: int, db: AsyncSession = Depends(get_db)):
    """Trigger outbound calls for all attendees of an event using ElevenLabs API."""
    import random
    
    # Initialize Gemini service for generating facts from opinions
    gemini_service = GeminiProcessor()
    
    # Get all opinions for this event
    opinions_result = await db.execute(
        select(Opinion).where(Opinion.event_id == event_id)
    )
    event_opinions = opinions_result.scalars().all()
    
    result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == event_id)
    )
    attendees = result.scalars().all()
    call_results = []
    for attendee in attendees:
        if not attendee.phone:
            # Skip if no phone number - populate with random opinions
            for opinion in event_opinions:
                # Check if opinion already exists for this attendee
                existing = await db.execute(
                    select(JoinedOpinion).where(
                        JoinedOpinion.attendee_id == attendee.id,
                        JoinedOpinion.opinion_id == opinion.opinion_id
                    )
                )
                if not existing.scalar_one_or_none():
                    # Generate random score
                    score = random.randint(0, 10)
                    
                    # Create joined opinion
                    joined_opinion = JoinedOpinion(
                        attendee_id=attendee.id,
                        opinion_id=opinion.opinion_id,
                        answer=score
                    )
                    db.add(joined_opinion)
                    
                    # Generate fact sentence from opinion using LLM
                    fact_text = gemini_service.generate_fact_from_opinion(
                        opinion_question=opinion.opinion,
                        score=score,
                        attendee_name=attendee.name
                    )
                    
                    # Store the fact
                    fact = Fact(
                        fact=fact_text,
                        attendee_id=attendee.id
                    )
                    db.add(fact)
            
            await db.commit()
            continue
        call_response = make_elevenlabs_call(attendee.phone, user=attendee.name, event_id=event_id, user_id=attendee.id)
        call_results.append({"id": attendee.id, "phone": attendee.phone, "result": call_response})
    return {"calls": call_results}


@router.post("/{event_id}/find_match/{attendee_id}", response_model=dict)
async def find_seat_match(
    event_id: int,
    attendee_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Use AI agent to find the best seat match for an attendee.
    Uses the event's chaos_temp as the chaos level.
    """
    # Check if event exists
    event_result = await db.execute(
        select(Event).where(Event.id == event_id)
    )
    event = event_result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Check if attendee exists and belongs to this event
    attendee_result = await db.execute(
        select(EventAttendee)
        .where(EventAttendee.id == attendee_id)
        .where(EventAttendee.event_id == event_id)
        .options(selectinload(EventAttendee.facts))
        .options(selectinload(EventAttendee.opinions))
    )
    attendee = attendee_result.scalar_one_or_none()
    
    if not attendee:
        raise HTTPException(
            status_code=404,
            detail="Attendee not found or doesn't belong to this event"
        )
    
    # Gather facts
    facts = [fact.fact for fact in attendee.facts]
    
    # Gather opinions with questions
    opinions = []
    for joined_opinion in attendee.opinions:
        opinion_result = await db.execute(
            select(Opinion).where(
                Opinion.opinion_id == joined_opinion.opinion_id
            )
        )
        opinion = opinion_result.scalar_one_or_none()
        if opinion:
            opinions.append({
                "question": opinion.opinion,
                "answer": joined_opinion.answer
            })
    
    # Initialize the matching agent
    agent = MatchingAgent()
    
    # Find the best match using the event's chaos_temp
    match_result = await agent.find_match(
        attendee_id=attendee_id,
        facts=facts,
        opinions=opinions,
        chaos_level=event.chaos_temp
    )
    
    # Return the result
    return {
        "attendee_id": attendee_id,
        "matched_with": match_result.attendee_id,
        "reasoning": match_result.reasoning,
        "confidence": match_result.confidence,
        "chaos_level": event.chaos_temp
    }


@router.post("/{event_id}/allocate_seats", response_model=dict)
async def allocate_seats(
    event_id: int,
    verbose: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Run the matcher runner to allocate seats for all attendees.
    
    This endpoint:
    1. Fetches all attendees for the event
    2. Matches them into pairs using the AI agent
    3. Allocates seats sequentially (table 0 seat 0, 0 seat 1, etc.)
    4. Updates the database with seat assignments
    
    Args:
        event_id: ID of the event
        verbose: Enable verbose logging (default: False)
        db: Database session
        
    Returns:
        Dict with allocation results
    """
    runner = MatcherRunner(verbose=verbose)
    result = await runner.run(event_id=event_id)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Unknown error occurred")
        )
    
    return result


async def run_matcher_background(event_id: int):
    """
    Background task to run the matcher for an event.
    
    This function runs the complete matching process:
    1. Fetches all attendees for the event
    2. Matches them into pairs using the AI agent
    3. Allocates seats sequentially
    4. Updates the database with seat assignments
    
    Logs progress similar to the create_and_run_event.py script.
    
    Args:
        event_id: ID of the event to process
    """
    logger.info("="*60)
    logger.info(f"STARTING BACKGROUND MATCHER FOR EVENT {event_id}")
    logger.info("="*60)
    
    try:
        # Run matcher with verbose logging
        runner = MatcherRunner(verbose=True)
        result = await runner.run(event_id=event_id)
        
        if result.get("success"):
            logger.info("\n" + "="*60)
            logger.info("MATCHING COMPLETE")
            logger.info("="*60)
            logger.info(f"Event: {result['event_name']} (ID: {event_id})")
            logger.info(f"Attendees: {result['attendees_count']}")
            logger.info(f"Pairs created: {result['pairs_created']}")
            logger.info(f"People seated: {result['attendees_seated']}")
            if result['attendees_unallocated'] > 0:
                logger.info(
                    f"Unallocated: {result['attendees_unallocated']}"
                )
            logger.info("="*60)
        else:
            logger.error("\n" + "="*60)
            logger.error("MATCHING FAILED")
            logger.error("="*60)
            logger.error(f"Event ID: {event_id}")
            logger.error(f"Error: {result.get('error')}")
            logger.error("="*60)
            
    except Exception as e:
        logger.error("\n" + "="*60)
        logger.error("MATCHING ERROR")
        logger.error("="*60)
        logger.error(f"Event ID: {event_id}")
        logger.error(f"Exception: {e}", exc_info=True)
        logger.error("="*60)


@router.post(
    "/{event_id}/start_matching",
    status_code=202,
    response_model=dict
)
async def start_matching_background(
    event_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Start the matcher runner in the background for an event.
    
    Returns immediately with 202 Accepted while the matching process
    runs in the background. Check logs for progress and results.
    
    This endpoint:
    1. Validates the event exists
    2. Starts the matching process in the background
    3. Returns 202 Accepted immediately
    
    The background process will:
    - Fetch all attendees for the event
    - Match them into pairs using the AI agent
    - Allocate seats sequentially
    - Update the database with seat assignments
    - Log progress and results
    
    Args:
        event_id: ID of the event
        background_tasks: FastAPI background tasks handler
        db: Database session
        
    Returns:
        Dict with status and message
        
    Raises:
        HTTPException: 404 if event not found
    """
    # Validate event exists
    query = select(Event).where(Event.id == event_id)
    result = await db.execute(query)
    event = result.scalar_one_or_none()
    
    if not event:
        raise HTTPException(
            status_code=404,
            detail=f"Event with id {event_id} not found"
        )
    
    # Start background task
    background_tasks.add_task(run_matcher_background, event_id)
    
    logger.info(
        f"Started background matching for event {event_id} ({event.name})"
    )
    
    return {
        "status": "accepted",
        "message": (
            f"Matching process started for event {event_id}. "
            "Check logs for progress."
        ),
        "event_id": event_id,
        "event_name": event.name
    }
