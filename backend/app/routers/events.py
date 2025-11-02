from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event

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
