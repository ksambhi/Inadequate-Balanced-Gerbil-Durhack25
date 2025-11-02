"""Check if test data exists in database."""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.database import async_session
from app.models import EventAttendee, Event
from sqlalchemy import select

async def check_data():
    async with async_session() as session:
        # Check for attendee
        result = await session.execute(select(EventAttendee).where(EventAttendee.id == 1))
        attendee = result.scalar_one_or_none()
        
        # Check for event
        result2 = await session.execute(select(Event).where(Event.id == 1))
        event = result2.scalar_one_or_none()
        
        print("=" * 60)
        if attendee:
            print(f"✓ Attendee found: {attendee}")
        else:
            print("✗ No attendee with id=1 found")
            
        if event:
            print(f"✓ Event found: {event}")
        else:
            print("✗ No event with id=1 found")
        print("=" * 60)
        
        return attendee, event

if __name__ == "__main__":
    asyncio.run(check_data())
