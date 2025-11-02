from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Event, EventAttendee, JoinedOpinion, Opinion

router = APIRouter(prefix="/api/events", tags=["events"])


class EventCreate(BaseModel):
    """Schema for creating a new event."""
    name: str
    total_tables: int
    ppl_per_table: int
    chaos_temp: float


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
    answer: str


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
            seat_no=None
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
