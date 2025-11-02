from dataclasses import dataclass
from typing import List, Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
import google.generativeai as genai
import os
from app.database import async_session
from app.models import Fact as FactModel

@dataclass
class Fact:
    fact: str

@dataclass
class Opinion:
    question: str
    answer: str

    def opinion_to_fact(self) -> Fact:
        """Convert opinion to fact using format: '{question}: {answer}'"""
        fact_text = f"{self.question}: {self.answer}"
        return Fact(fact=fact_text)


class EmbeddingService:
    """Handles Gemini embeddings"""
    
    def __init__(self, api_key: Optional[str] = None):
        genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))  # type: ignore
        # Gemini's embedding model
        self.model = "models/text-embedding-004"
        # Gemini embeddings are 768 dimensions
        self.dimensions = 768
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        result = genai.embed_content(  # type: ignore
            model=self.model,
            content=text,
            task_type="retrieval_document"  # For storing in database
        )
        return result["embedding"]
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            result = genai.embed_content(  # type: ignore
                model=self.model,
                content=text,
                task_type="retrieval_document"
            )
            embeddings.append(result["embedding"])
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a query (used when searching)"""
        result = genai.embed_content(  # type: ignore
            model=self.model,
            content=text,
            task_type="retrieval_query"  # For querying database
        )
        return result["embedding"]


class VectorDB:
    """Manages PGVector database operations using async SQLAlchemy"""
    
    def __init__(self):
        """Initialize VectorDB - uses the async_session from database.py"""
        pass
    
    async def insert_fact(self, attendee_id: int, fact_text: str, embedding: List[float]):
        """Insert a single fact with embedding"""
        async with async_session() as session:
            fact = FactModel(
                attendee_id=attendee_id,
                fact=fact_text,
                embedding=embedding
            )
            session.add(fact)
            await session.commit()
            await session.refresh(fact)
            return fact
    
    async def insert_facts_batch(self, records: List[tuple]):
        """
        Insert multiple facts at once
        records: List of (attendee_id, fact_text, embedding) tuples
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
            return facts
    
    async def search_similar(
        self, 
        query_embedding: List[float], 
        limit: int = 10, 
        exclude_attendee_id: Optional[int] = None
    ):
        """
        Find most similar facts using cosine similarity
        Returns list of tuples: (attendee_id, fact_text, similarity)
        """
        async with async_session() as session:
            # Build the query based on whether we're excluding an attendee
            if exclude_attendee_id:
                query = text("""
                    SELECT attendee_id, fact, 1 - (embedding <=> :embedding::vector) as similarity
                    FROM fact
                    WHERE attendee_id != :exclude_id
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                """)
                result = await session.execute(
                    query,
                    {
                        "embedding": str(query_embedding),
                        "exclude_id": exclude_attendee_id,
                        "limit": limit
                    }
                )
            else:
                query = text("""
                    SELECT attendee_id, fact, 1 - (embedding <=> :embedding::vector) as similarity
                    FROM fact
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                """)
                result = await session.execute(
                    query,
                    {
                        "embedding": str(query_embedding),
                        "limit": limit
                    }
                )
            
            return result.fetchall()
    
    async def search_opposite(
        self, 
        query_embedding: List[float], 
        limit: int = 10, 
        exclude_attendee_id: Optional[int] = None
    ):
        """
        Find LEAST similar facts (opposites) using negative similarity
        Returns list of tuples: (attendee_id, fact_text, dissimilarity)
        """
        # Negate the embedding to find opposites
        negated_embedding = [-x for x in query_embedding]
        
        async with async_session() as session:
            if exclude_attendee_id:
                query = text("""
                    SELECT attendee_id, fact, 1 - (embedding <=> :embedding::vector) as dissimilarity
                    FROM fact
                    WHERE attendee_id != :exclude_id
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                """)
                result = await session.execute(
                    query,
                    {
                        "embedding": str(negated_embedding),
                        "exclude_id": exclude_attendee_id,
                        "limit": limit
                    }
                )
            else:
                query = text("""
                    SELECT attendee_id, fact, 1 - (embedding <=> :embedding::vector) as dissimilarity
                    FROM fact
                    ORDER BY embedding <=> :embedding::vector
                    LIMIT :limit
                """)
                result = await session.execute(
                    query,
                    {
                        "embedding": str(negated_embedding),
                        "limit": limit
                    }
                )
            
            return result.fetchall()
