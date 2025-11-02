"""Test script for webhook endpoint with sample ElevenLabs payload."""
import asyncio
import json
import os
from dotenv import load_dotenv
from app.gemini_service import GeminiProcessor

# Load environment variables from .env file
load_dotenv()

# Sample ElevenLabs webhook payload structure
SAMPLE_PAYLOAD = {
    "data": {
        "conversation_id": "test-conv-123",
        "transcript": [
            {"role": "agent", "message": "Hi! Welcome to the event. What brings you here today?"},
            {"role": "user", "message": "Hi! I'm excited to meet new people. I work in tech and love hiking on weekends."},
            {"role": "agent", "message": "That's great! Do you prefer morning hikes or evening hikes?"},
            {"role": "user", "message": "Definitely morning hikes. I'm an early bird!"},
            {"role": "agent", "message": "Awesome! What about food preferences? Any favorites?"},
            {"role": "user", "message": "I love Italian food, especially pasta. And I prefer coffee over tea."},
            {"role": "agent", "message": "Notify condition met"},  # Should be filtered out
            {"role": "agent", "message": "Nice! Are you more of an introvert or extrovert?"},
            {"role": "user", "message": "I'd say I'm an ambivert, but I lean more towards extrovert."},
        ],
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "user_id": 1,
                "event_id": 1,
                "user": "Test User",
                "event_name": "DurHack 2025"
            }
        }
    }
}


async def test_gemini_processing():
    """Test Gemini processing with sample transcript."""
    print("=" * 60)
    print("Testing Gemini Conversation Processing")
    print("=" * 60)
    
    processor = GeminiProcessor()
    transcript = SAMPLE_PAYLOAD["data"]["transcript"]
    
    # Test transcript cleaning
    print("\n1. Testing transcript cleaning...")
    cleaned = processor.clean_transcript(transcript)
    print(f"\nCleaned transcript:\n{cleaned}\n")
    
    # Test extraction
    print("2. Testing Gemini extraction...")
    extraction = await processor.process_conversation(transcript)
    
    print(f"\nExtracted {len(extraction.facts)} facts:")
    for i, fact in enumerate(extraction.facts, 1):
        print(f"  {i}. {fact}")
    
    print(f"\nExtracted {len(extraction.opinions)} opinions:")
    for i, opinion in enumerate(extraction.opinions, 1):
        print(f"  {i}. Q: {opinion.question} | A: {opinion.answer}")
    
    print("\n" + "=" * 60)
    print("Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_gemini_processing())
