"""Gemini AI service for processing conversation transcripts."""
import random
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import google.generativeai as genai
import os
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Opinion, EventAttendee, JoinedOpinion


class ExtractedFact(BaseModel):
    """Single fact extracted from conversation."""
    fact: str = Field(..., description="A factual statement about the user")


class ExtractedOpinion(BaseModel):
    """Single opinion extracted from conversation."""
    question: str = Field(..., description="The question or topic")
    answer: str = Field(..., description="The user's answer or preference")


class ConversationExtraction(BaseModel):
    """Structured data extracted from a conversation."""
    facts: List[str] = Field(default_factory=list, description="List of facts about the user")
    opinions: List[ExtractedOpinion] = Field(default_factory=list, description="List of opinions/preferences")


class GeminiProcessor:
    """Handles conversation processing using Gemini AI."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Gemini AI client."""
        genai.configure(api_key=api_key or os.getenv("GOOGLE_API_KEY"))  # type: ignore
        self.model = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore
    
    def clean_transcript(self, transcript: List[Dict[str, str]]) -> str:
        """
        Clean transcript by removing workflow messages and formatting for analysis.
        
        Args:
            transcript: List of message dicts with 'role' and 'message' keys
            
        Returns:
            Cleaned transcript as formatted string
        """
        # Filter out workflow/system messages
        workflow_keywords = [
            "notify condition met",
            "tool call",
            "function call",
            "system:",
            "[workflow]",
            "[system]"
        ]
        
        cleaned_messages = []
        for msg in transcript:
            role = msg.get("role", "")
            message = msg.get("message", "")
            
            # Skip empty messages
            if not message or not message.strip():
                continue
            
            # Skip workflow messages
            message_lower = message.lower()
            if any(keyword in message_lower for keyword in workflow_keywords):
                continue
            
            # Format: "Agent: ..." or "User: ..."
            speaker = "Agent" if role == "agent" else "User"
            cleaned_messages.append(f"{speaker}: {message}")
        
        return "\n".join(cleaned_messages)
    
    def extract_structured_data(self, transcript_text: str) -> ConversationExtraction:
        """
        Extract structured facts and opinions from transcript using Gemini.
        
        Args:
            transcript_text: Cleaned transcript text
            
        Returns:
            ConversationExtraction with facts and opinions
        """
        prompt = f"""You are analyzing a conversation between an AI agent and a user at an event.
Extract all relevant facts and opinions about the USER (not the agent).

Facts should be:
- Concise statements about the user (hobbies, preferences, background, interests)
- Action-oriented or descriptive (e.g., "Enjoys hiking", "Works in tech", "Prefers tea over coffee")
- Not redundant

Opinions should be:
- Clear question-answer pairs about preferences or views
- The question should be a general topic (e.g., "Chocolate preference", "Morning or night person")
- The answer should be the user's specific response

Return your response as valid JSON with this exact structure:
{{
  "facts": ["fact1", "fact2", ...],
  "opinions": [
    {{"question": "topic", "answer": "user's answer"}},
    ...
  ]
}}

Conversation transcript:
{transcript_text}

Extract the facts and opinions as JSON:"""

        response_text = ""
        try:
            response = self.model.generate_content(prompt)  # type: ignore
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON response
            data = json.loads(response_text)
            
            # Validate and return using Pydantic
            return ConversationExtraction(**data)
            
        except json.JSONDecodeError as e:
            print(f"Failed to parse Gemini response as JSON: {e}")
            print(f"Raw response: {response_text}")
            return ConversationExtraction(facts=[], opinions=[])
        except Exception as e:
            print(f"Error extracting structured data: {e}")
            return ConversationExtraction(facts=[], opinions=[])
    
    async def process_conversation(
        self,
        transcript: List[Dict[str, str]]
    ) -> ConversationExtraction:
        """
        Process a conversation transcript end-to-end.
        
        Args:
            transcript: Raw transcript from ElevenLabs
            
        Returns:
            Extracted facts and opinions
        """
        # Clean the transcript
        cleaned_text = self.clean_transcript(transcript)
        
        if not cleaned_text:
            print("No valid conversation content found in transcript")
            return ConversationExtraction(facts=[], opinions=[])
        
        # Extract structured data
        extraction = self.extract_structured_data(cleaned_text)
        
        return extraction
    
    async def get_opinions(
        self,
        event_id: int,
        attendee_id: int,
        transcript: List[Dict[str, str]],
        db: AsyncSession
    ) -> List[JoinedOpinion]:
        """
        Get opinions for an event and extract user's answers from transcript.
        
        This method:
        1. Fetches all opinion questions associated with the event
        2. For each opinion, asks the AI to extract the user's answer
        3. Stores answers in the JoinedOpinion table
        
        Args:
            event_id: ID of the event
            attendee_id: ID of the attendee
            transcript: Conversation transcript
            db: Database session
            
        Returns:
            List of created JoinedOpinion records
        """
        # Get all opinions for this event
        query = select(Opinion).where(Opinion.event_id == event_id)
        result = await db.execute(query)
        opinions = result.scalars().all()
        
        if not opinions:
            print(f"No opinions found for event {event_id}")
            return []
        
        # Clean the transcript
        cleaned_text = self.clean_transcript(transcript)
        
        if not cleaned_text:
            print("No valid conversation content found in transcript")
            return []
        
        # Process each opinion question
        joined_opinions = []
        for opinion in opinions:
            prompt = f"""You are analyzing a conversation transcript.
Extract the user's answer to the following question.
Return ONLY a non-negative integer (0 to 10) representing their answer.
If the user did not answer this question or the topic wasn't discussed, pick a random number.

Question: {opinion.opinion}

Conversation transcript:
{cleaned_text}

User's answer (integer only):"""

            try:
                response = self.model.generate_content(prompt)
                answer_text = response.text.strip()
                
                # Parse integer from response
                try:
                    answer = int(answer_text)
                    # Ensure non-negative
                    if answer < 0:
                        answer = 0
                except ValueError:
                    print(f"Could not parse integer from '{answer_text}', using a random number")
                    answer = random.randint(0, 10)
                
                # Create JoinedOpinion record
                joined_opinion = JoinedOpinion(
                    attendee_id=attendee_id,
                    opinion_id=opinion.opinion_id,
                    answer=answer
                )
                db.add(joined_opinion)
                joined_opinions.append(joined_opinion)
                
            except Exception as e:
                print(f"Error extracting opinion for '{opinion.opinion}': {e}")
                continue
        
        # Commit all joined opinions
        if joined_opinions:
            await db.commit()
            for jo in joined_opinions:
                await db.refresh(jo)
        
        return joined_opinions
