"""Test webhook endpoint with a curl request to the running server."""
import requests
import json

# Sample ElevenLabs webhook payload
payload = {
    "data": {
        "conversation_id": "test-conv-456",
        "transcript": [
            {"role": "agent", "message": "Hello! Tell me about yourself."},
            {"role": "user", "message": "Hi! I'm a software engineer who loves rock climbing and photography."},
            {"role": "agent", "message": "That's amazing! Do you prefer indoor or outdoor climbing?"},
            {"role": "user", "message": "I prefer outdoor climbing. There's something special about being in nature."},
            {"role": "agent", "message": "What about photography - what's your favorite subject?"},
            {"role": "user", "message": "I love landscape photography, especially mountains and sunsets."},
            {"role": "agent", "message": "Notify condition met"},  # Should be filtered
            {"role": "agent", "message": "Are you a morning person or night owl?"},
            {"role": "user", "message": "Definitely a morning person. I wake up at 5 AM to catch sunrise photos."},
        ],
        "conversation_initiation_client_data": {
            "dynamic_variables": {
                "user_id": 1,  # This attendee should exist in your database
                "event_id": 1,
                "user": "Test User",
                "event_name": "DurHack 2025"
            }
        }
    }
}

# Send POST request to webhook endpoint
url = "http://localhost:8000/webhook/"
print("=" * 60)
print("Sending webhook to:", url)
print("=" * 60)

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print("\n✓ Webhook processed successfully!")
        result = response.json()
        print(f"  - Facts extracted: {result.get('facts_count', 0)}")
        print(f"  - Opinions extracted: {result.get('opinions_count', 0)}")
    else:
        print("\n✗ Webhook processing failed")
        
except requests.exceptions.RequestException as e:
    print(f"\n✗ Error sending request: {e}")
except Exception as e:
    print(f"\n✗ Unexpected error: {e}")

print("=" * 60)
