"""Watch database changes in real-time for webhook testing."""
import asyncio
import sys
from typing import Any, Dict, Optional
from dotenv import load_dotenv
load_dotenv()

from app.database import async_session
from app.models import Fact, Opinion, JoinedOpinion, EventAttendee
from sqlalchemy import select, func

async def get_stats(attendee_id: Optional[int] = None) -> Dict[str, Any]:
    """Get current database stats."""
    async with async_session() as session:
        # Count total facts
        result = await session.execute(select(func.count(Fact.id)))
        total_facts = result.scalar()
        
        # Count total opinions
        result = await session.execute(select(func.count(Opinion.opinion_id)))
        total_opinions = result.scalar()
        
        # Count total joined opinions
        result = await session.execute(select(func.count(JoinedOpinion.id)))
        total_joined = result.scalar()
        
        stats: Dict[str, Any] = {
            'total_facts': total_facts,
            'total_opinions': total_opinions,
            'total_joined_opinions': total_joined
        }
        
        # If attendee_id specified, get attendee-specific stats
        if attendee_id:
            result = await session.execute(
                select(func.count(Fact.id)).where(Fact.attendee_id == attendee_id)
            )
            stats['attendee_facts'] = result.scalar()
            
            result = await session.execute(
                select(func.count(JoinedOpinion.id)).where(JoinedOpinion.attendee_id == attendee_id)
            )
            stats['attendee_opinions'] = result.scalar()
            
            # Get actual facts
            result = await session.execute(
                select(Fact).where(Fact.attendee_id == attendee_id)
            )
            stats['facts_list'] = list(result.scalars().all())
            
            # Get actual opinions
            result = await session.execute(
                select(JoinedOpinion, Opinion)
                .join(Opinion)
                .where(JoinedOpinion.attendee_id == attendee_id)
            )
            stats['opinions_list'] = list(result.all())
        
        return stats

def print_stats(title: str, stats: Dict[str, Any], attendee_id: Optional[int] = None) -> None:
    """Pretty print stats."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(f"Total Facts in DB: {stats['total_facts']}")
    print(f"Total Opinions in DB: {stats['total_opinions']}")
    print(f"Total Joined Opinions: {stats['total_joined_opinions']}")
    
    if attendee_id:
        print(f"\nAttendee #{attendee_id} Data:")
        print(f"  - Facts: {stats['attendee_facts']}")
        print(f"  - Opinions: {stats['attendee_opinions']}")
        
        if stats['facts_list']:
            print(f"\n  Facts:")
            for i, fact in enumerate(stats['facts_list'], 1):
                has_emb = "✓" if fact.embedding else "✗"
                print(f"    {i}. [{has_emb}] {fact.fact}")
        
        if stats['opinions_list']:
            print(f"\n  Opinions:")
            for i, (joined, opinion) in enumerate(stats['opinions_list'], 1):
                print(f"    {i}. Q: {opinion.opinion}")
                print(f"       A: {joined.answer}")
    
    print("=" * 60)

async def watch_mode(attendee_id: int) -> None:
    """Watch mode - show before, wait for user, show after."""
    # Show BEFORE
    before_stats = await get_stats(attendee_id)
    print_stats("BEFORE - Database State", before_stats, attendee_id)
    
    print("\n📞 Ready for ElevenLabs call!")
    print(f"   Make your call now with user_id={attendee_id}")
    print(f"   Press ENTER after the call completes to see changes...\n")
    
    # Wait for user
    input()
    
    # Show AFTER
    after_stats = await get_stats(attendee_id)
    print_stats("AFTER - Database State", after_stats, attendee_id)
    
    # Show DIFF
    print("\n" + "=" * 60)
    print("📊 CHANGES DETECTED")
    print("=" * 60)
    
    facts_added = after_stats.get('attendee_facts', 0) - before_stats.get('attendee_facts', 0)
    opinions_added = after_stats.get('attendee_opinions', 0) - before_stats.get('attendee_opinions', 0)
    
    print(f"✓ Facts added: {facts_added}")
    print(f"✓ Opinions added: {opinions_added}")
    
    if facts_added > 0:
        print(f"\nNew Facts:")
        facts_list = after_stats.get('facts_list', [])
        before_count = before_stats.get('attendee_facts', 0)
        new_facts = facts_list[before_count:]
        for i, fact in enumerate(new_facts, 1):
            has_emb = "✓" if fact.embedding else "✗"
            print(f"  {i}. [{has_emb}] {fact.fact}")
    
    if opinions_added > 0:
        print(f"\nNew Opinions:")
        opinions_list = after_stats.get('opinions_list', [])
        before_count = before_stats.get('attendee_opinions', 0)
        new_opinions = opinions_list[before_count:]
        for i, (joined, opinion) in enumerate(new_opinions, 1):
            print(f"  {i}. Q: {opinion.opinion}")
            print(f"     A: {joined.answer}")
    
    print("=" * 60)

async def list_attendees() -> Optional[list[Any]]:
    """List all attendees."""
    async with async_session() as session:
        result = await session.execute(select(EventAttendee))
        attendees = list(result.scalars().all())
        
        if not attendees:
            print("No attendees found in database.")
            print("Run: .venv/bin/python create_test_data.py")
            return None
        
        print("\n" + "=" * 60)
        print("Available Attendees:")
        print("=" * 60)
        for att in attendees:
            result = await session.execute(
                select(func.count(Fact.id)).where(Fact.attendee_id == att.id)
            )
            fact_count = result.scalar()
            print(f"ID {att.id}: {att.name} ({att.email}) - {fact_count} facts")
        print("=" * 60 + "\n")
        
        return attendees

async def main() -> None:
    """Main entry point."""
    attendees = await list_attendees()
    
    if not attendees:
        return
    
    # Get attendee ID from user
    if len(sys.argv) > 1:
        attendee_id = int(sys.argv[1])
    else:
        attendee_id_input = input(f"Enter attendee ID to watch (default: 1): ").strip()
        attendee_id = int(attendee_id_input) if attendee_id_input else 1
    
    # Verify attendee exists
    async with async_session() as session:
        result = await session.execute(
            select(EventAttendee).where(EventAttendee.id == attendee_id)
        )
        attendee = result.scalar_one_or_none()
        
        if not attendee:
            print(f"❌ Attendee with ID {attendee_id} not found!")
            return
        
        print(f"👤 Watching attendee: {attendee.name} (ID: {attendee_id})")
    
    await watch_mode(attendee_id)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
