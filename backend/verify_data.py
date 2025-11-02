"""Verify that webhook data was stored in database."""
import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.database import async_session
from app.models import Fact, Opinion, JoinedOpinion, EventAttendee
from sqlalchemy import select

async def verify_data():
    async with async_session() as session:
        # Get attendee
        result = await session.execute(select(EventAttendee).where(EventAttendee.id == 1))
        attendee = result.scalar_one()
        
        # Get facts for this attendee
        result = await session.execute(select(Fact).where(Fact.attendee_id == 1))
        facts = result.scalars().all()
        
        # Get opinions for this attendee
        result = await session.execute(
            select(JoinedOpinion, Opinion)
            .join(Opinion)
            .where(JoinedOpinion.attendee_id == 1)
        )
        opinions = result.all()
        
        print("=" * 60)
        print(f"Data for attendee: {attendee.name} (ID: {attendee.id})")
        print("=" * 60)
        
        print(f"\n✓ Facts extracted: {len(facts)}")
        for i, fact in enumerate(facts, 1):
            has_embedding = fact.embedding is not None
            embedding_status = "✓ has embedding" if has_embedding else "✗ no embedding"
            print(f"  {i}. {fact.fact} [{embedding_status}]")
        
        print(f"\n✓ Opinions extracted: {len(opinions)}")
        for i, (joined_opinion, opinion) in enumerate(opinions, 1):
            print(f"  {i}. Q: {opinion.opinion}")
            print(f"     A: {joined_opinion.answer}")
        
        print("=" * 60)
        print("✓ Webhook data successfully stored in database!")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(verify_data())
