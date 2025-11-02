"""
Matcher Runner for allocating seating pairs for an event.

This module orchestrates the matching process:
1. Fetches all attendees for an event
2. Matches attendees in pairs using the AI agent
3. Allocates seats sequentially (table 0 seat 0, seat 1, table 1 seat 0...)
4. Updates the database with seat assignments
"""
import logging
from typing import List, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Event, EventAttendee, Fact, JoinedOpinion
from app.matching_agent import MatchingAgent

logger = logging.getLogger(__name__)


class MatcherRunner:
    """Orchestrates the seating allocation process for an event."""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the matcher runner.
        
        Args:
            verbose: Enable verbose logging for agent operations
        """
        self.verbose = verbose
        self.agent = MatchingAgent(verbose=verbose)
        logger.info("MatcherRunner initialized")
    
    async def get_event(
        self,
        event_id: int,
        session: AsyncSession
    ) -> Optional[Event]:
        """
        Fetch event by ID.
        
        Args:
            event_id: ID of the event
            session: Database session
            
        Returns:
            Event instance or None if not found
        """
        query = select(Event).where(Event.id == event_id)
        result = await session.execute(query)
        event = result.scalar_one_or_none()
        return event
    
    async def get_attendees(
        self,
        event_id: int,
        session: AsyncSession
    ) -> List[EventAttendee]:
        """
        Fetch all attendees for an event who are going.
        
        Args:
            event_id: ID of the event
            session: Database session
            
        Returns:
            List of EventAttendee instances
        """
        query = (
            select(EventAttendee)
            .where(EventAttendee.event_id == event_id)
            .where(EventAttendee.going == True)  # noqa: E712
        )
        result = await session.execute(query)
        attendees = result.scalars().all()
        return list(attendees)
    
    async def get_attendee_data(
        self,
        attendee_id: int,
        session: AsyncSession
    ) -> Tuple[List[str], List[dict]]:
        """
        Fetch facts and opinions for an attendee.
        
        Args:
            attendee_id: ID of the attendee
            session: Database session
            
        Returns:
            Tuple of (facts_list, opinions_list)
        """
        # Get facts
        facts_query = select(Fact).where(Fact.attendee_id == attendee_id)
        facts_result = await session.execute(facts_query)
        facts = facts_result.scalars().all()
        facts_list = [fact.fact for fact in facts]
        
        # Get opinions
        opinions_query = (
            select(JoinedOpinion)
            .where(JoinedOpinion.attendee_id == attendee_id)
        )
        opinions_result = await session.execute(opinions_query)
        joined_opinions = opinions_result.scalars().all()
        
        # Format opinions with questions
        opinions_list = []
        for joined_opinion in joined_opinions:
            # Fetch the opinion question
            await session.refresh(joined_opinion, ["opinion"])
            opinions_list.append({
                "question": joined_opinion.opinion.opinion,
                "answer": joined_opinion.answer
            })
        
        return facts_list, opinions_list
    
    async def match_pairs(
        self,
        event_id: int,
        chaos_level: float,
        session: AsyncSession
    ) -> List[Tuple[int, int]]:
        """
        Match all attendees into pairs using the AI agent.
        
        Args:
            event_id: ID of the event
            chaos_level: Chaos level for matching (0-10)
            session: Database session
            
        Returns:
            List of (attendee_id_1, attendee_id_2) tuples
        """
        # Get all attendees
        attendees = await self.get_attendees(event_id, session)
        
        if len(attendees) < 2:
            logger.warning(
                f"Event {event_id} has {len(attendees)} attendees. "
                "Need at least 2 for pairing."
            )
            return []
        
        logger.info(f"Starting pairing for {len(attendees)} attendees")
        
        # Create set of all attendee IDs
        all_attendee_ids = {att.id for att in attendees}
        unallocated = all_attendee_ids.copy()
        pairs = []
        
        # Keep matching until we can't find more pairs
        while len(unallocated) >= 2:
            # Get next unallocated attendee
            current_attendee_id = next(iter(unallocated))
            
            # Calculate exclusion list: all attendees except unallocated ones
            excluded = list(all_attendee_ids - unallocated)
            
            logger.info(
                f"\nMatching attendee {current_attendee_id} "
                f"({len(unallocated)} remaining, "
                f"{len(excluded)} excluded)"
            )
            
            # Get attendee data
            facts, opinions = await self.get_attendee_data(
                current_attendee_id,
                session
            )
            
            if not facts and not opinions:
                logger.warning(
                    f"Attendee {current_attendee_id} has no facts "
                    "or opinions. Skipping."
                )
                unallocated.remove(current_attendee_id)
                continue
            
            # Find match using agent
            try:
                result = await self.agent.find_match(
                    attendee_id=current_attendee_id,
                    event_id=event_id,
                    facts=facts,
                    opinions=opinions,
                    chaos_level=chaos_level,
                    exclude_attendee_ids=excluded
                )
                
                matched_id = result.attendee_id
                
                # Validate match
                if matched_id == -1:
                    logger.warning(
                        f"No match found for attendee {current_attendee_id}"
                    )
                    unallocated.remove(current_attendee_id)
                    continue
                
                if matched_id not in unallocated:
                    logger.error(
                        f"Agent returned invalid match: {matched_id} "
                        f"(not in unallocated set)"
                    )
                    unallocated.remove(current_attendee_id)
                    continue
                
                # Valid match found!
                logger.info(
                    f"✓ Matched {current_attendee_id} with {matched_id}"
                )
                logger.info(f"  Reasoning: {result.reasoning}")
                logger.info(f"  Confidence: {result.confidence:.2f}")
                
                # Add pair and remove from unallocated
                pairs.append((current_attendee_id, matched_id))
                unallocated.remove(current_attendee_id)
                unallocated.remove(matched_id)
                
            except Exception as e:
                logger.error(
                    f"Error matching attendee {current_attendee_id}: {e}"
                )
                unallocated.remove(current_attendee_id)
                continue
        
        # Handle odd attendee (if any)
        if unallocated:
            remaining = list(unallocated)
            logger.warning(
                f"Odd number of attendees. {remaining} will be unallocated."
            )
        
        logger.info(f"\nMatching complete: {len(pairs)} pairs created")
        return pairs
    
    async def allocate_seats(
        self,
        pairs: List[Tuple[int, int]],
        event: Event,
        session: AsyncSession
    ) -> None:
        """
        Allocate seats to pairs sequentially.
        
        Seats are allocated starting from table 0 seat 0, then table 0 seat 1,
        then table 1 seat 0, etc.
        
        Args:
            pairs: List of (attendee_id_1, attendee_id_2) tuples
            event: Event instance
            session: Database session
        """
        ppl_per_table = event.ppl_per_table
        total_tables = event.total_tables
        
        logger.info(
            f"Allocating {len(pairs) * 2} attendees to seats "
            f"({total_tables} tables, {ppl_per_table} per table)"
        )
        
        # Flatten pairs into seat assignments
        seat_assignments = []
        for attendee1_id, attendee2_id in pairs:
            seat_assignments.append(attendee1_id)
            seat_assignments.append(attendee2_id)
        
        # Check capacity
        total_capacity = total_tables * ppl_per_table
        if len(seat_assignments) > total_capacity:
            logger.warning(
                f"Not enough capacity! Need {len(seat_assignments)} seats, "
                f"have {total_capacity}"
            )
        
        # Allocate seats sequentially
        seat_index = 0
        for attendee_id in seat_assignments:
            # Calculate table and seat number
            table_no = seat_index // ppl_per_table
            seat_no = seat_index % ppl_per_table
            
            # Check if we've exceeded table capacity
            if table_no >= total_tables:
                logger.error(
                    f"Ran out of tables! Cannot seat attendee {attendee_id}"
                )
                break
            
            # Update attendee in database
            query = select(EventAttendee).where(
                EventAttendee.id == attendee_id
            )
            result = await session.execute(query)
            attendee = result.scalar_one_or_none()
            
            if attendee:
                attendee.table_no = table_no
                attendee.seat_no = seat_no
                logger.info(
                    f"Assigned attendee {attendee_id} ({attendee.name}) "
                    f"to table {table_no}, seat {seat_no}"
                )
            else:
                logger.error(f"Attendee {attendee_id} not found in database")
            
            seat_index += 1
        
        # Commit all changes
        await session.commit()
        logger.info(
            f"✓ Seat allocation complete. "
            f"Assigned {seat_index} attendees to seats."
        )
    
    async def run(self, event_id: int) -> dict:
        """
        Run the complete matching and allocation process for an event.
        
        Args:
            event_id: ID of the event to process
            
        Returns:
            Dict with results summary
        """
        logger.info("="*60)
        logger.info(f"STARTING MATCHER RUNNER FOR EVENT {event_id}")
        logger.info("="*60)
        
        async with async_session() as session:
            # 1. Get event
            event = await self.get_event(event_id, session)
            if not event:
                error_msg = f"Event {event_id} not found"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            logger.info(f"Event: {event.name}")
            logger.info(f"Chaos Level: {event.chaos_temp}/10")
            logger.info(
                f"Capacity: {event.total_tables} tables, "
                f"{event.ppl_per_table} per table "
                f"= {event.total_tables * event.ppl_per_table} total seats"
            )
            
            # 2. Get attendees
            attendees = await self.get_attendees(event_id, session)
            logger.info(f"Attendees going: {len(attendees)}")
            
            if len(attendees) < 2:
                error_msg = "Need at least 2 attendees for pairing"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "attendees_count": len(attendees)
                }
            
            # 3. Match pairs
            pairs = await self.match_pairs(
                event_id,
                event.chaos_temp,
                session
            )
            
            if not pairs:
                error_msg = "No pairs could be created"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg,
                    "attendees_count": len(attendees),
                    "pairs_created": 0
                }
            
            # 4. Allocate seats
            await self.allocate_seats(pairs, event, session)
            
            logger.info("="*60)
            logger.info("MATCHER RUNNER COMPLETE")
            logger.info("="*60)
            
            return {
                "success": True,
                "event_id": event_id,
                "event_name": event.name,
                "attendees_count": len(attendees),
                "pairs_created": len(pairs),
                "attendees_seated": len(pairs) * 2,
                "attendees_unallocated": len(attendees) - (len(pairs) * 2)
            }


async def main():
    """Example usage of MatcherRunner."""
    import asyncio
    
    # Example: Run matcher for event ID 1
    runner = MatcherRunner(verbose=True)
    result = await runner.run(event_id=1)
    
    print("\n" + "="*60)
    print("RESULT SUMMARY")
    print("="*60)
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
