from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import Event, EventAttendee

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


class AttendeeResponse(BaseModel):
    """Schema for attendee response."""
    id: int
    name: str
    phone: str
    email: str
    table_no: int | None
    seat_no: int | None
    event_id: int
    
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
    
    # Get all attendees for this event
    result = await db.execute(
        select(EventAttendee).where(EventAttendee.event_id == event_id)
    )
    attendees = result.scalars().all()
    
    return attendees


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
    
    # Refresh all attendees to get their IDs
    for attendee in created_attendees:
        await db.refresh(attendee)
    
    return created_attendees
