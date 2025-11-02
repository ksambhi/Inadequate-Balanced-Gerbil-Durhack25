"""
Matching Service using cosine similarity on fact embeddings.

This service finds the best seat match for an attendee based on their
facts and a chaos level (0-10). Low chaos = similar matches (high similarity),
high chaos = opposite matches (low similarity).
"""
import os
import logging
import random
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.matcher import EmbeddingService, VectorDB

# Load environment variables
load_dotenv()

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
    """Service that finds the best seat match for an attendee using cosine similarity."""
    
    def __init__(self, verbose: bool = False):
        """Initialize the matching service."""
        self.verbose = verbose
        self.embedding_service = EmbeddingService()
        self.vector_db = VectorDB()
        
        if self.verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            logger.info("✓ Matching service initialized")
    
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
        Find the best seat match for an attendee using cosine similarity.
        
        Args:
            attendee_id: ID of the attendee to find a match for
            event_id: ID of the event (only match within same event)
            facts: List of facts about the attendee
            opinions: List of opinion dicts with "question" and "answer"
            chaos_level: Chaos level from 0 (harmony/similar) to 10 (chaos/opposite)
            exclude_attendee_ids: Optional list of attendee IDs already
                                  paired to exclude from matching
        
        Returns:
            MatchResult with the best matched attendee ID
        """
        # Validate chaos level
        chaos_level = max(0, min(10, chaos_level))
        
        # Default to empty list if not provided
        if exclude_attendee_ids is None:
            exclude_attendee_ids = []
        
        if self.verbose:
            logger.info("\n" + "🚀 " + "="*58)
            logger.info("STARTING MATCHING SERVICE")
            logger.info("="*60)
            logger.info(f"Attendee ID: {attendee_id}")
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Facts: {len(facts)}")
            logger.info(f"Opinions: {len(opinions)}")
            logger.info(f"Chaos Level: {chaos_level}/10")
            logger.info(f"Excluded: {len(exclude_attendee_ids)} attendees")
            logger.info("="*60)
        
        # Check if we have any facts
        if not facts:
            if self.verbose:
                logger.warning("⚠️  No facts available for matching")
            return MatchResult(
                attendee_id=-1,
                reasoning="No facts available to match on",
                confidence=0.0
            )
        
        # Pick a random fact to search with
        random_fact = random.choice(facts)
        
        if self.verbose:
            logger.info(f"Selected random fact: '{random_fact}'")
        
        # Embed the query fact
        query_embedding = self.embedding_service.embed_query(random_fact)
        
        # Determine search strategy based on chaos level
        # Low chaos (0-3): Find SIMILAR (high cosine similarity)
        # Medium chaos (4-6): Random mix
        # High chaos (7-10): Find OPPOSITE (low cosine similarity)
        
        if chaos_level <= 3:
            # Low chaos: search for similar
            if self.verbose:
                logger.info("Strategy: Finding SIMILAR attendees (high similarity)")
            
            results = await self.vector_db.search_similar(
                query_embedding=query_embedding,
                limit=50,  # Get more candidates
                event_id=event_id,
                exclude_attendee_id=attendee_id,
                exclude_attendee_ids=exclude_attendee_ids
            )
            
            # Higher similarity is better for low chaos
            sort_ascending = False
            
        elif chaos_level <= 6:
            # Medium chaos: get both similar and opposite, pick randomly
            if self.verbose:
                logger.info("Strategy: Finding MIXED attendees (medium chaos)")
            
            results = await self.vector_db.search_similar(
                query_embedding=query_embedding,
                limit=50,
                event_id=event_id,
                exclude_attendee_id=attendee_id,
                exclude_attendee_ids=exclude_attendee_ids
            )
            
            # Random selection from middle range
            sort_ascending = None
            
        else:
            # High chaos: search for opposite
            if self.verbose:
                logger.info("Strategy: Finding OPPOSITE attendees (low similarity)")
            
            results = await self.vector_db.search_opposite(
                query_embedding=query_embedding,
                limit=50,
                event_id=event_id,
                exclude_attendee_id=attendee_id,
                exclude_attendee_ids=exclude_attendee_ids
            )
            
            # Lower similarity (higher dissimilarity) is better for high chaos
            sort_ascending = True
        
        if not results:
            if self.verbose:
                logger.warning("⚠️  No candidates found")
            return MatchResult(
                attendee_id=-1,
                reasoning="No suitable candidates found in the database",
                confidence=0.0
            )
        
        if self.verbose:
            logger.info(f"Found {len(results)} candidates")
        
        # Group results by attendee_id and calculate average similarity
        attendee_scores = {}
        attendee_facts = {}
        
        for row in results:
            att_id = int(row[0])
            fact = row[1]
            similarity = float(row[2])
            
            if att_id not in attendee_scores:
                attendee_scores[att_id] = []
                attendee_facts[att_id] = []
            
            attendee_scores[att_id].append(similarity)
            attendee_facts[att_id].append(fact)
        
        # Calculate average similarity for each attendee
        attendee_avg = {
            att_id: sum(scores) / len(scores)
            for att_id, scores in attendee_scores.items()
        }
        
        if self.verbose:
            logger.info(f"Unique attendees found: {len(attendee_avg)}")
        
        # Select best match based on chaos level
        if sort_ascending is None:
            # Medium chaos: pick randomly
            matched_id = random.choice(list(attendee_avg.keys()))
            avg_similarity = attendee_avg[matched_id]
            strategy_desc = "random selection"
        else:
            # Sort by average similarity
            sorted_attendees = sorted(
                attendee_avg.items(),
                key=lambda x: x[1],
                reverse=not sort_ascending
            )
            
            matched_id = sorted_attendees[0][0]
            avg_similarity = sorted_attendees[0][1]
            
            if sort_ascending:
                strategy_desc = "lowest similarity (most opposite)"
            else:
                strategy_desc = "highest similarity (most similar)"
        
        # Build reasoning
        matched_fact = attendee_facts[matched_id][0]
        
        if chaos_level <= 3:
            reasoning = (
                f"Harmonious match with {strategy_desc}. "
                f"Similar fact: '{matched_fact}' "
                f"(similarity: {avg_similarity:.2f})"
            )
        elif chaos_level <= 6:
            reasoning = (
                f"Balanced match with {strategy_desc}. "
                f"Related fact: '{matched_fact}' "
                f"(similarity: {avg_similarity:.2f})"
            )
        else:
            reasoning = (
                f"Chaotic match with {strategy_desc}. "
                f"Opposite fact: '{matched_fact}' "
                f"(dissimilarity: {1 - avg_similarity:.2f})"
            )
        
        # Confidence is based on how many candidates we had
        confidence = min(1.0, len(attendee_avg) / 10.0)
        
        if self.verbose:
            logger.info(f"✓ Match found: Attendee {matched_id}")
            logger.info(f"  Reasoning: {reasoning}")
            logger.info(f"  Confidence: {confidence:.2f}")
            logger.info(f"  Avg Similarity: {avg_similarity:.2f}")
            logger.info("="*60 + "\n")
        
        return MatchResult(
            attendee_id=matched_id,
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