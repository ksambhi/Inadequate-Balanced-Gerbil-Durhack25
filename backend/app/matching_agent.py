"""
Matching Service using opinion vector dot products.

This service finds the best seat match for an attendee based on their
opinion vectors. Higher dot product = more different opinions = better match.
Each attendee's opinions form a vector, and we maximize the dot product
between pairs to create the most interesting conversations.
"""
import logging
import numpy as np
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import Opinion, EventAttendee, JoinedOpinion

# Setup logging
logger = logging.getLogger(__name__)


class MatchResult(BaseModel):
    """Structured output for the best match."""
    attendee_id: int = Field(
        description="The ID of the best matched attendee to sit next to"
    )
    reasoning: str = Field(
        description="Brief explanation of why this is the best match"
    )
    confidence: float = Field(
        description="Confidence score between 0 and 1",
        ge=0,
        le=1
    )


class MatchingAgent:
    """Service that finds the best seat match using opinion vector dot products."""
    
    def __init__(self, verbose: bool = False):
        """Initialize the matching service."""
        self.verbose = verbose
        
        if self.verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logger.info("✓ Matching service initialized (opinion-based)")
    
    async def _get_opinion_vectors(
        self,
        event_id: int,
        attendee_ids: List[int],
        session: AsyncSession
    ) -> Dict[int, np.ndarray]:
        """
        Get opinion vectors for all attendees.
        
        Args:
            event_id: ID of the event
            attendee_ids: List of attendee IDs to get vectors for
            session: Database session
            
        Returns:
            Dict mapping attendee_id to their opinion vector (numpy array)
        """
        # Get all opinions for this event (ordered consistently)
        opinions_query = (
            select(Opinion)
            .where(Opinion.event_id == event_id)
            .order_by(Opinion.opinion_id)
        )
        opinions_result = await session.execute(opinions_query)
        event_opinions = opinions_result.scalars().all()
        
        if not event_opinions:
            if self.verbose:
                logger.warning(f"No opinions found for event {event_id}")
            return {}
        
        opinion_ids = [op.opinion_id for op in event_opinions]
        
        if self.verbose:
            logger.info(f"Event has {len(opinion_ids)} opinion questions")
        
        # Get all joined opinions for these attendees
        vectors = {}
        
        for attendee_id in attendee_ids:
            # Get this attendee's opinions
            joined_query = (
                select(JoinedOpinion)
                .where(JoinedOpinion.attendee_id == attendee_id)
                .where(JoinedOpinion.opinion_id.in_(opinion_ids))
            )
            joined_result = await session.execute(joined_query)
            joined_opinions = joined_result.scalars().all()
            
            # Build vector (default to 5 if missing)
            opinion_dict = {
                jo.opinion_id: jo.answer
                for jo in joined_opinions
            }
            
            vector = np.array([
                opinion_dict.get(op_id, 5)
                for op_id in opinion_ids
            ], dtype=float)
            
            vectors[attendee_id] = vector
        
        return vectors
    
    async def find_match(
        self,
        attendee_id: int,
        event_id: int,
        facts: List[str],
        opinions: List[Dict[str, str]],
        chaos_level: float,
        exclude_attendee_ids: Optional[List[int]] = None
    ) -> MatchResult:
        """
        Find the best seat match using opinion vector dot products.
        
        Args:
            attendee_id: ID of the attendee to find a match for
            event_id: ID of the event (only match within same event)
            facts: List of facts (not used in this matcher)
            opinions: List of opinion dicts (not used directly)
            chaos_level: Chaos level (not used in this matcher)
            exclude_attendee_ids: List of attendee IDs already paired
        
        Returns:
            MatchResult with the best matched attendee ID
        """
        # Default to empty list if not provided
        if exclude_attendee_ids is None:
            exclude_attendee_ids = []
        
        if self.verbose:
            logger.info("\n" + "🚀 " + "="*58)
            logger.info("STARTING MATCHING SERVICE (Opinion Vectors)")
            logger.info("="*60)
            logger.info(f"Attendee ID: {attendee_id}")
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Excluded: {len(exclude_attendee_ids)} attendees")
            logger.info("="*60)
        
        # Get all attendees for this event (going=True)
        async with async_session() as session:
            attendees_query = (
                select(EventAttendee)
                .where(EventAttendee.event_id == event_id)
                .where(EventAttendee.going == True)  # noqa: E712
            )
            attendees_result = await session.execute(attendees_query)
            all_attendees = attendees_result.scalars().all()
            
            # Get candidate IDs (exclude self and already paired)
            candidate_ids = [
                att.id for att in all_attendees
                if att.id != attendee_id and att.id not in exclude_attendee_ids
            ]
            
            if not candidate_ids:
                if self.verbose:
                    logger.warning("⚠️  No candidates available")
                return MatchResult(
                    attendee_id=-1,
                    reasoning="No available candidates to match with",
                    confidence=0.0
                )
            
            # Get opinion vectors for current attendee and all candidates
            all_ids = [attendee_id] + candidate_ids
            vectors = await self._get_opinion_vectors(
                event_id,
                all_ids,
                session
            )
            
            if attendee_id not in vectors:
                if self.verbose:
                    logger.warning(f"No opinion vector for attendee {attendee_id}")
                return MatchResult(
                    attendee_id=-1,
                    reasoning="No opinions available for this attendee",
                    confidence=0.0
                )
            
            current_vector = vectors[attendee_id]
            
            # Calculate dot products with all candidates
            dot_products = {}
            for candidate_id in candidate_ids:
                if candidate_id in vectors:
                    candidate_vector = vectors[candidate_id]
                    # Dot product: higher = more different
                    dot_prod = np.dot(current_vector, candidate_vector)
                    dot_products[candidate_id] = dot_prod
            
            if not dot_products:
                if self.verbose:
                    logger.warning("No candidates with opinion vectors")
                return MatchResult(
                    attendee_id=-1,
                    reasoning="No candidates with opinions available",
                    confidence=0.0
                )
            
            # Find the candidate with HIGHEST dot product (most different)
            best_match_id = max(dot_products.items(), key=lambda x: x[1])[0]
            best_dot_product = dot_products[best_match_id]
            
            # Get attendee name for reasoning
            attendee_query = select(EventAttendee).where(
                EventAttendee.id == best_match_id
            )
            attendee_result = await session.execute(attendee_query)
            matched_attendee = attendee_result.scalar_one_or_none()
            
            matched_name = (
                matched_attendee.name if matched_attendee else f"ID {best_match_id}"
            )
            
            # Build reasoning
            reasoning = (
                f"Best match with {matched_name} "
                f"(dot product: {best_dot_product:.2f}). "
                f"Maximizes opinion diversity for interesting conversations."
            )
            
            # Confidence based on number of candidates
            confidence = min(1.0, len(dot_products) / 5.0)
            
            if self.verbose:
                logger.info(f"✓ Match found: Attendee {best_match_id}")
                logger.info(f"  Dot Product: {best_dot_product:.2f}")
                logger.info(f"  Reasoning: {reasoning}")
                logger.info(f"  Confidence: {confidence:.2f}")
                logger.info(f"  Evaluated {len(dot_products)} candidates")
                logger.info("="*60 + "\n")
            
            return MatchResult(
                attendee_id=best_match_id,
                reasoning=reasoning,
                confidence=confidence
            )


# Example usage
async def main():
    """Example usage of the matching service."""
    agent = MatchingAgent(verbose=True)
    
    # Example attendee data
    result = await agent.find_match(
        attendee_id=1,
        event_id=1,
        facts=["Loves dogs", "Enjoys hiking", "Works in tech"],
        opinions=[
            {"question": "Favorite food?", "answer": 8},
            {"question": "Morning person?", "answer": 9}
        ],
        chaos_level=5.0
    )
    
    print(f"Best match: Attendee {result.attendee_id}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Confidence: {result.confidence}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


# Example usage
async def main():
    """Example usage of the matching service."""
    agent = MatchingAgent(verbose=True)
    
    # Example attendee data
    result = await agent.find_match(
        attendee_id=1,
        event_id=1,
        facts=["Loves dogs", "Enjoys hiking", "Works in tech"],
        opinions=[
            {"question": "Favorite food?", "answer": "Pizza"},
            {
                "question": "Morning person?",
                "answer": "Yes, love early mornings"
            }
        ],
        chaos_level=2.0  # Low chaos = harmonious seating
    )
    
    print(f"Best match: Attendee {result.attendee_id}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Confidence: {result.confidence}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())