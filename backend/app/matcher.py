"""
Improved matcher module with pgvector integration.

Uses SQLAlchemy's pgvector support directly for better performance
and type safety.
"""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import logging

from sqlalchemy import select, func
import google.generativeai as genai
import os

from app.database import async_session
from app.models import Fact as FactModel

logger = logging.getLogger(__name__)


@dataclass
class Fact:
    """Fact dataclass for structured fact data."""
    fact: str


@dataclass
class Opinion:
    """Opinion dataclass with conversion to fact."""
    question: str
    answer: str

    def opinion_to_fact(self) -> Fact:
        """Convert opinion to fact using format: '{question}: {answer}'"""
        fact_text = f"{self.question}: {self.answer}"
        return Fact(fact=fact_text)


class EmbeddingService:
    """Handles Gemini embeddings with caching and error handling."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize embedding service with API key."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")
        
        genai.configure(api_key=self.api_key)  # type: ignore
        self.model = "models/text-embedding-004"
        self.dimensions = 768
        logger.info(f"EmbeddingService initialized with {self.model}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding
            
        Raises:
            ValueError: If embedding generation fails
        """
        try:
            result = genai.embed_content(  # type: ignore
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Failed to embed text: {e}")
            raise ValueError(f"Embedding generation failed: {e}")
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings
        """
        embeddings = []
        for i, text in enumerate(texts):
            try:
                result = genai.embed_content(  # type: ignore
                    model=self.model,
                    content=text,
                    task_type="retrieval_document"
                )
                embeddings.append(result["embedding"])
            except Exception as e:
                logger.warning(f"Failed to embed text {i}: {e}")
                # Continue with other texts
                continue
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a query (optimized for searching).
        
        Args:
            text: Query text to embed
            
        Returns:
            List of floats representing the query embedding
        """
        try:
            result = genai.embed_content(  # type: ignore
                model=self.model,
                content=text,
                task_type="retrieval_query"
            )
            return result["embedding"]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise ValueError(f"Query embedding failed: {e}")


class VectorDB:
    """
    Manages PGVector database operations using SQLAlchemy ORM.
    
    Uses pgvector's native SQLAlchemy integration for type safety
    and better performance.
    """
    
    def __init__(self):
        """Initialize VectorDB."""
        logger.info("VectorDB initialized")
    
    async def insert_fact(
        self,
        attendee_id: int,
        fact_text: str,
        embedding: List[float]
    ) -> FactModel:
        """
        Insert a single fact with embedding.
        
        Args:
            attendee_id: ID of the attendee
            fact_text: The fact text
            embedding: Vector embedding of the fact
            
        Returns:
            Created Fact model instance
        """
        async with async_session() as session:
            fact = FactModel(
                attendee_id=attendee_id,
                fact=fact_text,
                embedding=embedding
            )
            session.add(fact)
            await session.commit()
            await session.refresh(fact)
            logger.debug(f"Inserted fact {fact.id} for attendee {attendee_id}")
            return fact
    
    async def insert_facts_batch(
        self,
        records: List[Tuple[int, str, List[float]]]
    ) -> List[FactModel]:
        """
        Insert multiple facts at once (bulk insert).
        
        Args:
            records: List of (attendee_id, fact_text, embedding) tuples
            
        Returns:
            List of created Fact model instances
        """
        async with async_session() as session:
            facts = [
                FactModel(
                    attendee_id=attendee_id,
                    fact=fact_text,
                    embedding=embedding
                )
                for attendee_id, fact_text, embedding in records
            ]
            session.add_all(facts)
            await session.commit()
            logger.info(f"Bulk inserted {len(facts)} facts")
            return facts
    
    async def search_similar(
        self,
        query_embedding: List[float],
        limit: int = 10,
        event_id: Optional[int] = None,
        exclude_attendee_id: Optional[int] = None,
        exclude_attendee_ids: Optional[List[int]] = None,
        min_similarity: float = 0.0
    ) -> List[Tuple[int, str, float]]:
        """
        Find most similar facts using cosine distance.
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            event_id: Optional event ID to filter results by
            exclude_attendee_id: Optional single attendee ID to exclude
            exclude_attendee_ids: Optional list of attendee IDs to exclude
            min_similarity: Minimum similarity threshold (0-1)
            
        Returns:
            List of (attendee_id, fact_text, similarity_score) tuples
        """
        async with async_session() as session:
            # Build query using SQLAlchemy ORM with pgvector operators
            # Need to join with EventAttendee to filter by event_id
            from app.models import EventAttendee
            
            query = select(
                FactModel.attendee_id,
                FactModel.fact,
                (1 - FactModel.embedding.cosine_distance(query_embedding))
                .label('similarity')
            ).join(
                EventAttendee,
                FactModel.attendee_id == EventAttendee.id
            )
            
            # Filter by event_id if provided
            if event_id is not None:
                query = query.where(EventAttendee.event_id == event_id)
            
            # Build exclusion list
            exclusions = []
            if exclude_attendee_id is not None:
                exclusions.append(exclude_attendee_id)
            if exclude_attendee_ids:
                exclusions.extend(exclude_attendee_ids)
            
            # Add exclusion filter at DB level
            if exclusions:
                query = query.where(
                    FactModel.attendee_id.not_in(exclusions)
                )
            
            # Add similarity threshold
            if min_similarity > 0:
                query = query.where(
                    (1 - FactModel.embedding.cosine_distance(query_embedding))
                    >= min_similarity
                )
            
            # Order by similarity and limit
            query = query.order_by(
                FactModel.embedding.cosine_distance(query_embedding)
            ).limit(limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            logger.debug(
                f"Found {len(rows)} similar facts "
                f"(excluded {len(exclusions)} attendees)"
            )
            return [(row[0], row[1], float(row[2])) for row in rows]
    
    async def search_opposite(
        self,
        query_embedding: List[float],
        limit: int = 10,
        event_id: Optional[int] = None,
        exclude_attendee_id: Optional[int] = None,
        exclude_attendee_ids: Optional[List[int]] = None
    ) -> List[Tuple[int, str, float]]:
        """
        Find LEAST similar facts (opposites).
        
        Uses cosine distance ordered descending to find maximally
        dissimilar vectors.
        
        Args:
            query_embedding: Query vector
            limit: Maximum number of results
            event_id: Optional event ID to filter results by
            exclude_attendee_id: Optional single attendee ID to exclude
            exclude_attendee_ids: Optional list of attendee IDs to exclude
            
        Returns:
            List of (attendee_id, fact_text, dissimilarity_score) tuples
        """
        async with async_session() as session:
            # Use cosine distance for finding opposites
            # Higher distance = more dissimilar (opposite)
            # Need to join with EventAttendee to filter by event_id
            from app.models import EventAttendee
            
            query = select(
                FactModel.attendee_id,
                FactModel.fact,
                FactModel.embedding.cosine_distance(query_embedding)
                .label('dissimilarity')
            ).join(
                EventAttendee,
                FactModel.attendee_id == EventAttendee.id
            )
            
            # Filter by event_id if provided
            if event_id is not None:
                query = query.where(EventAttendee.event_id == event_id)
            
            # Build exclusion list
            exclusions = []
            if exclude_attendee_id is not None:
                exclusions.append(exclude_attendee_id)
            if exclude_attendee_ids:
                exclusions.extend(exclude_attendee_ids)
            
            # Add exclusion filter at DB level
            if exclusions:
                query = query.where(
                    FactModel.attendee_id.not_in(exclusions)
                )
            
            # Order by cosine distance descending (most opposite first)
            query = query.order_by(
                FactModel.embedding.cosine_distance(query_embedding).desc()
            ).limit(limit)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            logger.debug(
                f"Found {len(rows)} opposite facts "
                f"(excluded {len(exclusions)} attendees)"
            )
            return [(row[0], row[1], float(row[2])) for row in rows]
    
    async def get_attendee_facts(
        self,
        attendee_id: int
    ) -> List[FactModel]:
        """
        Get all facts for a specific attendee.
        
        Args:
            attendee_id: ID of the attendee
            
        Returns:
            List of Fact model instances
        """
        async with async_session() as session:
            query = select(FactModel).where(
                FactModel.attendee_id == attendee_id
            )
            result = await session.execute(query)
            facts = result.scalars().all()
            return list(facts)
    
    async def count_facts(self) -> int:
        """Get total number of facts in database."""
        async with async_session() as session:
            query = select(func.count(FactModel.id))
            result = await session.execute(query)
            count = result.scalar() or 0
            return count
    
    async def delete_attendee_facts(self, attendee_id: int) -> int:
        """
        Delete all facts for an attendee.
        
        Args:
            attendee_id: ID of the attendee
            
        Returns:
            Number of facts deleted
        """
        async with async_session() as session:
            query = select(FactModel).where(
                FactModel.attendee_id == attendee_id
            )
            result = await session.execute(query)
            facts = result.scalars().all()
            
            for fact in facts:
                await session.delete(fact)
            
            await session.commit()
            logger.info(
                f"Deleted {len(facts)} facts for attendee {attendee_id}"
            )
            return len(facts)
