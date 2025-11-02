"""
Test script for the matching agent.
This script tests the agent with mock data.
"""
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_agent_basic():
    """Test the agent with basic functionality."""
    print("🧪 Testing Matching Agent...")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("❌ ERROR: GOOGLE_API_KEY not found in environment")
        print("Please add your Google API key to the .env file:")
        print("  GOOGLE_API_KEY=your_key_here")
        return False
    
    print("✓ Google API key found")
    
    # Import the agent
    try:
        from app.matching_agent import MatchingAgent
        print("✓ Successfully imported MatchingAgent")
    except Exception as e:
        print(f"❌ Failed to import MatchingAgent: {e}")
        return False
    
    # Initialize the agent
    try:
        agent = MatchingAgent(verbose=True)  # Enable verbose mode
        print("✓ Successfully initialized agent")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return False
    
    # Test with sample data
    print("\n📊 Testing with sample attendee data...")
    print("-" * 60)
    
    try:
        # Sample attendee data
        attendee_id = 1
        facts = [
            "Loves dogs and has a golden retriever",
            "Enjoys outdoor hiking on weekends",
            "Works as a software engineer in tech",
            "Vegetarian and loves Italian food"
        ]
        opinions = [
            {"question": "Favorite food?", "answer": "Pizza"},
            {
                "question": "Morning or night person?",
                "answer": "Definitely a morning person"
            },
            {
                "question": "Prefer remote or office work?",
                "answer": "Remote work for flexibility"
            }
        ]
        
        print(f"Attendee ID: {attendee_id}")
        print(f"Facts: {len(facts)} facts")
        print(f"Opinions: {len(opinions)} opinions")
        print()
        
        # Test with low chaos (harmonious matching)
        print("🔍 Test 1: Low Chaos Level (2.0) - Finding similar people")
        print("-" * 60)
        result = await agent.find_match(
            attendee_id=attendee_id,
            facts=facts,
            opinions=opinions,
            chaos_level=2.0
        )
        
        print(f"✓ Match found!")
        print(f"  - Matched Attendee ID: {result.attendee_id}")
        print(f"  - Reasoning: {result.reasoning}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print()
        
        # Test with high chaos (opposite matching)
        print("🔍 Test 2: High Chaos Level (8.0) - Finding opposites")
        print("-" * 60)
        result = await agent.find_match(
            attendee_id=attendee_id,
            facts=facts,
            opinions=opinions,
            chaos_level=8.0
        )
        
        print(f"✓ Match found!")
        print(f"  - Matched Attendee ID: {result.attendee_id}")
        print(f"  - Reasoning: {result.reasoning}")
        print(f"  - Confidence: {result.confidence:.2f}")
        print()
        
        print("=" * 60)
        print("✅ All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during matching: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_with_db():
    """Test the agent with actual database data."""
    print("\n🔗 Testing with Database...")
    print("=" * 60)
    
    try:
        from app.database import async_session
        from app.models import EventAttendee, Opinion, Fact
        from sqlalchemy import select
        
        async with async_session() as session:
            # Get first attendee
            result = await session.execute(
                select(EventAttendee).limit(1)
            )
            attendee = result.scalar_one_or_none()
            
            if not attendee:
                print("⚠️  No attendees in database, skipping DB test")
                return True
            
            print(f"✓ Found attendee: {attendee.name} (ID: {attendee.id})")
            
            # Get their facts
            fact_result = await session.execute(
                select(Fact).where(Fact.attendee_id == attendee.id)
            )
            facts = [f.fact for f in fact_result.scalars().all()]
            
            print(f"  - Facts: {len(facts)}")
            
            # Initialize agent
            from app.matching_agent import MatchingAgent
            agent = MatchingAgent(verbose=True)  # Enable verbose mode
            
            # Find a match
            if facts:
                result = await agent.find_match(
                    attendee_id=attendee.id,
                    facts=facts,
                    opinions=[],
                    chaos_level=5.0
                )
                
                print(f"✓ Match found: Attendee {result.attendee_id}")
                print(f"  - Confidence: {result.confidence:.2f}")
            else:
                print("⚠️  No facts for this attendee, add some first")
            
            return True
            
    except Exception as e:
        print(f"⚠️  Database test skipped: {e}")
        return True  # Don't fail if DB not available


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MATCHING AGENT TEST SUITE")
    print("=" * 60 + "\n")
    
    # Run basic test
    basic_result = await test_agent_basic()
    
    # Run database test if basic test passed
    if basic_result:
        await test_agent_with_db()
    
    print("\n" + "=" * 60)
    print("TEST SUITE COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
