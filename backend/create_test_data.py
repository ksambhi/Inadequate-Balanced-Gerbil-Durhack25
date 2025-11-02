"""Create test data for webhook testing."""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.database import async_session
from app.models import Event, EventAttendee

async def create_test_data():
    async with async_session() as session:
        # Create test event
        event = Event(
            name="DurHack 2025",
            total_tables=10,
            ppl_per_table=8,
            chaos_temp=0.5
        )
        session.add(event)
        await session.flush()
        
        # Create test attendee
        attendee = EventAttendee(
            name="Test User",
            phone="+1234567890",
            email="test@example.com",
            event_id=event.id,
            rsvp=True,
            going=True
        )
        session.add(attendee)
        await session.commit()
        
        print("=" * 60)
        print(f"✓ Created test event: {event}")
        print(f"✓ Created test attendee: {attendee}")
        print(f"  - Attendee ID: {attendee.id}")
        print(f"  - Event ID: {event.id}")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(create_test_data())
