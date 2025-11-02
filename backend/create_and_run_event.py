"""
Create a complete event with attendees, facts, and opinions,
then run the matching algorithm and display the final allocation.

Usage: uv run python create_and_run_event.py
"""
import asyncio
import logging
from typing import List, Dict
from sqlalchemy import select

from app.database import async_session
from app.models import Event, EventAttendee, Fact, Opinion, JoinedOpinion
from app.matcher import EmbeddingService
from app.matcher_runner import MatcherRunner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

EVENT_CONFIG = {
    "name": "AI Meetup 2025",
    "chaos_temp": 5,  # 0-10 (0=harmony, 10=chaos)
    "num_tables": 3,    # Will be calculated from attendees if None
}

ATTENDEES_DATA = [
    {
        "name": "Alice",
        "email": "alice@example.com",
        "phone": "+1234567890",
        "facts": [
            "Loves hiking and outdoor adventures",
            "Works as a software engineer at a startup",
            "Enjoys cooking Italian food"
        ],
        "opinions": {
            "What's your favorite programming language?": 9,
            "Coffee or tea?": 10,
            "Morning person or night owl?": 9
        }
    },
    {
        "name": "Bob",
        "email": "bob@example.com",
        "phone": "+1234567891",
        "facts": [
            "Passionate about rock climbing",
            "Backend developer specializing in Python",
            "Loves pizza and craft beer"
        ],
        "opinions": {
            "What's your favorite programming language?": 9,
            "Coffee or tea?": 10,
            "Morning person or night owl?": 10
        }
    },
    {
        "name": "Carol",
        "email": "carol@example.com",
        "phone": "+1234567892",
        "facts": [
            "Enjoys reading sci-fi novels",
            "Works in AI research and machine learning",
            "Vegetarian and loves Thai food"
        ],
        "opinions": {
            "What's your favorite programming language?": 8,
            "Coffee or tea?": 2,
            "Morning person or night owl?": 2
        }
    },
    {
        "name": "David",
        "email": "david@example.com",
        "phone": "+1234567893",
        "facts": [
            "Amateur photographer specializing in nature",
            "Frontend developer who loves React",
            "Enjoys hiking and wildlife observation"
        ],
        "opinions": {
            "What's your favorite programming language?": 8,
            "Coffee or tea?": 3,
            "Morning person or night owl?": 1
        }
    },
    {
        "name": "Eve",
        "email": "eve@example.com",
        "phone": "+1234567894",
        "facts": [
            "Loves board games and strategy games",
            "Data scientist working with neural networks",
            "Enjoys Mexican and Indian cuisine"
        ],
        "opinions": {
            "What's your favorite programming language?": 9,
            "Coffee or tea?": 7,
            "Morning person or night owl?": 5
        }
    },
    {
        "name": "Frank",
        "email": "frank@example.com",
        "phone": "+1234567895",
        "facts": [
            "Marathon runner and fitness enthusiast",
            "DevOps engineer working with Kubernetes",
            "Loves sushi and Japanese food"
        ],
        "opinions": {
            "What's your favorite programming language?": 8,
            "Coffee or tea?": 0,
            "Morning person or night owl?": 10
        }
    },
    {
        "name": "Grace",
        "email": "grace@example.com",
        "phone": "+1234567896",
        "facts": [
            "Plays guitar and writes songs",
            "Full-stack developer with 10 years experience",
            "Loves Mediterranean food"
        ],
        "opinions": {
            "What's your favorite programming language?": 9,
            "Coffee or tea?": 4,
            "Morning person or night owl?": 1
        }
    },
    {
        "name": "Henry",
        "email": "henry@example.com",
        "phone": "+1234567897",
        "facts": [
            "Rock climbing instructor on weekends",
            "Mobile app developer for iOS",
            "Enjoys BBQ and grilling"
        ],
        "opinions": {
            "What's your favorite programming language?": 7,
            "Coffee or tea?": 9,
            "Morning person or night owl?": 10
        }
    },
]


async def create_or_get_opinions(
    session,
    opinion_questions: List[str],
    event_id
) -> Dict[str, int]:
    """
    Create or retrieve opinion questions from the database.
    
    Returns:
        Dict mapping question text to opinion_id
    """
    opinion_map = {}
    
    for question in opinion_questions:
        # Check if opinion already exists
        query = select(Opinion).where(Opinion.opinion == question, Opinion.event_id == event_id)
        result = await session.execute(query)
        opinion = result.scalar_one_or_none()
        
        if not opinion:
            # Create new opinion
            opinion = Opinion(opinion=question, event_id=event_id)
            session.add(opinion)
            await session.flush()
            logger.info(f"Created opinion: {question}")
        
        opinion_map[question] = opinion.opinion_id
    
    return opinion_map


async def create_event_and_attendees() -> int:
    """
    Create an event with all attendees, facts, and opinions.
    
    Returns:
        Event ID
    """
    logger.info("="*60)
    logger.info("CREATING EVENT AND ATTENDEES")
    logger.info("="*60)
    
    # Calculate table settings
    num_attendees = len(ATTENDEES_DATA)
    
    if num_attendees < 2:
        raise ValueError("Need at least 2 attendees")
    
    # Calculate optimal table configuration
    if EVENT_CONFIG.get("num_tables"):
        num_tables = EVENT_CONFIG["num_tables"]
    else:
        # Auto-calculate: aim for 4-6 people per table
        num_tables = max(1, (num_attendees + 4) // 5)
    
    ppl_per_table = (num_attendees + num_tables - 1) // num_tables
    
    # Check if tables would be too empty
    min_ppl_at_last_table = num_attendees - (num_tables - 1) * ppl_per_table
    if min_ppl_at_last_table < 2:
        logger.error(
            f"ERROR: Last table would have {min_ppl_at_last_table} people. "
            "Need at least 2 per table."
        )
        logger.info(f"Consider reducing num_tables to {num_tables - 1}")
        raise ValueError("Would result in table with < 2 people")
    
    logger.info(f"Event: {EVENT_CONFIG['name']}")
    logger.info(f"Chaos Level: {EVENT_CONFIG['chaos_temp']}/10")
    logger.info(f"Attendees: {num_attendees}")
    logger.info(f"Tables: {num_tables}")
    logger.info(f"People per table: {ppl_per_table}")
    logger.info(
        f"Minimum at last table: {min_ppl_at_last_table}"
    )
    
    async with async_session() as session:
        # Create event
        event = Event(
            name=EVENT_CONFIG["name"],
            total_tables=num_tables,
            ppl_per_table=ppl_per_table,
            chaos_temp=EVENT_CONFIG["chaos_temp"]
        )
        session.add(event)
        await session.flush()
        
        logger.info(f"\n✓ Created event ID: {event.id}")
        
        # Collect all unique opinion questions
        all_questions = set()
        for attendee_data in ATTENDEES_DATA:
            all_questions.update(attendee_data["opinions"].keys())
        
        # Create or get opinions
        opinion_map = await create_or_get_opinions(
            session,
            list(all_questions),
            event_id=event.id
        )

        print(f"{event.id} has opinions map: {opinion_map}")

        
        # Initialize embedding service
        embedding_service = EmbeddingService()
        
        # Create attendees with facts and opinions
        for attendee_data in ATTENDEES_DATA:
            # Create attendee
            attendee = EventAttendee(
                name=attendee_data["name"],
                email=attendee_data["email"],
                phone=attendee_data["phone"],
                event_id=event.id,
                rsvp=True,
                going=True  # Mark as going so matcher will include them
            )
            session.add(attendee)
            await session.flush()
            
            logger.info(
                f"\n✓ Created attendee: {attendee.name} (ID: {attendee.id})"
            )
            
            # Create facts with embeddings
            for fact_text in attendee_data["facts"]:
                # Generate embedding
                embedding = embedding_service.embed_text(fact_text)
                
                fact = Fact(
                    fact=fact_text,
                    attendee_id=attendee.id,
                    embedding=embedding
                )
                session.add(fact)
                logger.info(f"  + Fact: {fact_text}")
            
            await session.flush()
            
            # Create opinions
            for question, answer in attendee_data["opinions"].items():
                opinion_id = opinion_map[question]
                
                joined_opinion = JoinedOpinion(
                    attendee_id=attendee.id,
                    opinion_id=opinion_id,
                    answer=answer
                )
                session.add(joined_opinion)
                logger.info(f"  + Opinion: {question} → {answer}")
        
        # Commit all changes
        await session.commit()
        
        logger.info("\n" + "="*60)
        logger.info("✓ DATABASE SETUP COMPLETE")
        logger.info("="*60)
        
        return event.id


async def print_allocation(event_id: int):
    """
    Print the final seating allocation in a nice format.
    """
    logger.info("\n" + "="*60)
    logger.info("FINAL SEATING ALLOCATION")
    logger.info("="*60)
    
    async with async_session() as session:
        # Get event
        event_query = select(Event).where(Event.id == event_id)
        event_result = await session.execute(event_query)
        event = event_result.scalar_one()
        
        logger.info(f"\nEvent: {event.name}")
        logger.info(f"Chaos Level: {event.chaos_temp}/10")
        logger.info("")
        
        # Get all attendees with seat assignments
        attendees_query = (
            select(EventAttendee)
            .where(EventAttendee.event_id == event_id)
            .where(EventAttendee.going == True)  # noqa: E712
            .order_by(EventAttendee.table_no, EventAttendee.seat_no)
        )
        result = await session.execute(attendees_query)
        attendees = result.scalars().all()
        
        # Group by table
        tables = {}
        unallocated = []
        
        for attendee in attendees:
            if attendee.table_no is not None:
                if attendee.table_no not in tables:
                    tables[attendee.table_no] = []
                tables[attendee.table_no].append(attendee)
            else:
                unallocated.append(attendee)
        
        # Print tables
        for table_no in sorted(tables.keys()):
            logger.info(f"Table {table_no}:")
            for attendee in tables[table_no]:
                logger.info(
                    f"  Seat {attendee.seat_no}: {attendee.name} "
                    f"({attendee.email})"
                )
            logger.info("")
        
        # Print unallocated
        if unallocated:
            logger.info("Unallocated:")
            for attendee in unallocated:
                logger.info(f"  - {attendee.name} ({attendee.email})")
            logger.info("")
        
        # Print statistics
        total_attendees = len(attendees)
        seated = sum(len(seats) for seats in tables.values())
        logger.info("Statistics:")
        logger.info(f"  Total attendees: {total_attendees}")
        logger.info(f"  Seated: {seated}")
        logger.info(f"  Unallocated: {len(unallocated)}")
        logger.info(f"  Tables used: {len(tables)}/{event.total_tables}")
        
        logger.info("\n" + "="*60)


async def main():
    """
    Main function: Create event, run matcher, display results.
    """
    print("\n" + "="*70)
    print("EVENT CREATION AND MATCHING SYSTEM")
    print("="*70)
    
    try:
        # Step 1: Create event and attendees
        event_id = await create_event_and_attendees()
        
        # Step 2: Run matcher
        logger.info("\n")
        runner = MatcherRunner(verbose=True)
        result = await runner.run(event_id=event_id)
        
        # Step 3: Check results
        if not result.get("success"):
            logger.error(f"\n✗ Matching failed: {result.get('error')}")
            return
        
        # Step 4: Print allocation
        await print_allocation(event_id)
        
        # Step 5: Print summary
        print("\n" + "="*70)
        print("FINAL SUMMARY")
        print("="*70)
        print(f"✓ Event created: {result['event_name']} (ID: {event_id})")
        print(f"✓ Attendees: {result['attendees_count']}")
        print(f"✓ Pairs created: {result['pairs_created']}")
        print(f"✓ People seated: {result['attendees_seated']}")
        if result['attendees_unallocated'] > 0:
            print(f"⚠ Unallocated: {result['attendees_unallocated']}")
        print("="*70 + "\n")
        
    except Exception as e:
        logger.error(f"\n✗ Error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
