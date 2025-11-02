"""
Test script for the MatcherRunner.

Run with: uv run python test_matcher_runner.py
"""
import asyncio
import logging
from app.matcher_runner import MatcherRunner

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


async def main():
    """Test the matcher runner with an event."""
    print("\n" + "="*60)
    print("MATCHER RUNNER TEST")
    print("="*60)
    
    # Get event ID from user
    try:
        event_id = int(input("\nEnter event ID to process: "))
    except (ValueError, KeyboardInterrupt):
        print("\nUsing default event ID: 1")
        event_id = 1
    
    # Ask for verbose mode
    verbose_input = input("Enable verbose mode? (y/n) [default: y]: ").strip()
    verbose = verbose_input.lower() != 'n'
    
    print(f"\nRunning matcher for event {event_id}...")
    print(f"Verbose mode: {'ON' if verbose else 'OFF'}")
    print()
    
    # Run the matcher
    runner = MatcherRunner(verbose=verbose)
    result = await runner.run(event_id=event_id)
    
    # Print results
    print("\n" + "="*60)
    print("RESULT SUMMARY")
    print("="*60)
    
    if result.get("success"):
        print("✓ SUCCESS!")
        print(f"  Event: {result.get('event_name')}")
        print(f"  Total attendees: {result.get('attendees_count')}")
        print(f"  Pairs created: {result.get('pairs_created')}")
        print(f"  Attendees seated: {result.get('attendees_seated')}")
        print(f"  Unallocated: {result.get('attendees_unallocated')}")
    else:
        print("✗ FAILED")
        print(f"  Error: {result.get('error')}")
        if 'attendees_count' in result:
            print(f"  Attendees found: {result.get('attendees_count')}")
        if 'pairs_created' in result:
            print(f"  Pairs created: {result.get('pairs_created')}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
