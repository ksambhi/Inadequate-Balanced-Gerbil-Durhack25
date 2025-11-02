from fastapi import APIRouter, Request, HTTPException
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session
from app.gemini_service import GeminiProcessor
from app.matcher import EmbeddingService, VectorDB
from app.models import Opinion, JoinedOpinion, EventAttendee

router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/")
async def elevenlabs_webhook(request: Request) -> Dict[str, Any]:
    """Handle ElevenLabs post-call webhook.
    
    Receives call data from ElevenLabs after a call is completed.
    Processes the conversation transcript using Gemini AI and stores
    extracted facts and opinions in the database.
    """
    try:
        data: Dict[str, Any] = await request.json()
        print("Received webhook data")
        
        # Extract relevant data from webhook payload
        conversation_data = data.get("data", {})
        transcript = conversation_data.get("transcript", [])
        
        # Extract dynamic variables (user_id, event_id, etc.)
        client_data = conversation_data.get("conversation_initiation_client_data", {})
        dynamic_vars = client_data.get("dynamic_variables", {})
        
        attendee_id = dynamic_vars.get("user_id")
        event_id = dynamic_vars.get("event_id")
        
        # Validate required fields
        if not attendee_id:
            print("Warning: No attendee_id (user_id) found in webhook data")
            return {"status": "ok", "warning": "No attendee_id found"}
        
        if not transcript:
            print("Warning: No transcript found in webhook data")
            return {"status": "ok", "warning": "No transcript found"}
        
        print(f"Processing conversation for attendee_id={attendee_id}, event_id={event_id}")
        
        # Verify attendee exists in database
        async with async_session() as session:
            result = await session.execute(
                select(EventAttendee).where(EventAttendee.id == attendee_id)
            )
            attendee = result.scalar_one_or_none()
            
            if not attendee:
                print(f"Warning: Attendee with id={attendee_id} not found in database")
                return {"status": "ok", "warning": "Attendee not found"}
        
        # Process conversation with Gemini
        gemini_processor = GeminiProcessor()
        extraction = await gemini_processor.process_conversation(transcript)
        
        print(f"Extracted {len(extraction.facts)} facts and {len(extraction.opinions)} opinions")
        
        # Initialize services
        embedding_service = EmbeddingService()
        vector_db = VectorDB()
        
        # Store facts with embeddings
        if extraction.facts:
            # Generate embeddings for all facts
            embeddings = embedding_service.embed_batch(extraction.facts)
            
            # Prepare records for batch insert
            fact_records = [
                (attendee_id, fact_text, embedding)
                for fact_text, embedding in zip(extraction.facts, embeddings)
            ]
            
            # Insert facts into database
            await vector_db.insert_facts_batch(fact_records)
            print(f"Stored {len(fact_records)} facts for attendee {attendee_id}")
        
        # Store opinions
        if extraction.opinions:
            await store_opinions(attendee_id, extraction.opinions)
            print(f"Stored {len(extraction.opinions)} opinions for attendee {attendee_id}")
        
        return {
            "status": "ok",
            "facts_count": len(extraction.facts),
            "opinions_count": len(extraction.opinions)
        }
        
    except Exception as e:
        # Log error but return 200 OK to ElevenLabs (don't retry on our errors)
        print(f"Error processing webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": str(e)}


async def store_opinions(attendee_id: int, opinions: List[Any]) -> None:
    """
    Store opinions in Opinion and JoinedOpinion tables.
    
    Args:
        attendee_id: ID of the attendee
        opinions: List of ExtractedOpinion objects
    """
    async with async_session() as session:
        for opinion_data in opinions:
            question = opinion_data.question
            answer = opinion_data.answer
            
            # Check if opinion question already exists
            result = await session.execute(
                select(Opinion).where(Opinion.opinion == question)
            )
            opinion = result.scalar_one_or_none()
            
            # Create opinion if it doesn't exist
            if not opinion:
                opinion = Opinion(opinion=question)
                session.add(opinion)
                await session.flush()  # Flush to get the opinion_id
            
            # Check if this attendee already answered this opinion
            result = await session.execute(
                select(JoinedOpinion).where(
                    JoinedOpinion.attendee_id == attendee_id,
                    JoinedOpinion.opinion_id == opinion.opinion_id
                )
            )
            existing_joined = result.scalar_one_or_none()
            
            if existing_joined:
                # Update existing answer
                existing_joined.answer = answer
            else:
                # Create new joined opinion
                joined_opinion = JoinedOpinion(
                    attendee_id=attendee_id,
                    opinion_id=opinion.opinion_id,
                    answer=answer
                )
                session.add(joined_opinion)
        
        await session.commit()
