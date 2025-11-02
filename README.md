# [Sit Happens](https://devpost.com/software/sit-happens-r8nfuh)

Have you ever wondered how to seat guests as messily as possible?

Wanted to put two people on the same table, just to see how much they'd fight?

## Inspiration

We’ve all been to *that* wedding. Hours of forced small talk with a random uncle or your grandma’s bridge partner. So we thought: what if seating plans didn’t have to be polite? What if we added a bit of **chaos**?

Introducing **Sit Happens**: a conversational voice agent and seat-matching algorithm that ensures every event, whether dream or disaster, is never boring again.

---

## What It Does

Our **voice agent** calls event attendees and playfully analyses their personality through adaptive icebreaker questions.  
The system extracts unstructured conversational data, classifies it into _Facts_ and _Opinions_, and uses this to predict who each guest would mesh or clash with.

Finally, users get an **interactive web app** that visualises the optimal (or most chaotic) seating plan in real time.

---

## How We Built It

1. **Frontend:** A React app where organisers create events, add attendees, and input phone numbers for the calls.  
2. **Voice Agent:** Built on the **ElevenLabs Agents Platform**, leveraging the new *Agents Workflow* feature to dynamically adapt to user responses.  
3. **Data Pipeline:** Using an **ngrok** webhook, we pull transcriptions from ElevenLabs into a **Postgres** database. A **Gemini** model then structures this text into clear Facts and Opinions.  
4. **Vectorisation:** Gemini also generates embeddings for each Fact, capturing personality traits numerically. With **pgvector**, we store these embeddings directly in Postgres for similarity search.  
5. **Matching Algorithm:** Given an `event_id`, `attendee_id`, `chaos_score`, and Fact, we greedily query for embeddings that maximise or minimise similarity, depending on how chaotic you want the vibe.  
6. **Visualisation:** The resulting matches generate a dynamic seating chart displayed through our web interface.

---

## Challenges We Ran Into

- **Regulatory hurdles:** Using a Twilio virtual number with ElevenLabs required identity verification, which is a process that takes hours to approve in the UK.  
- **Vector database setup:** `pgvector` on Windows required a full Visual Studio build environment (20–50 GB!). Docker saved the day.  
- **Integrating multiple moving parts:** Getting ElevenLabs, Gemini, Postgres, and the frontend all to talk seamlessly took serious debugging finesse.

---

## Accomplishments We’re Proud Of

- Rapidly mastering the **ElevenLabs Agents** platform and advanced features like real-time *Workflows* and post-call webhooks.  
- Successfully implementing a **vector-based matching system**, from embedding generation to efficient querying inside Postgres.  
- Expanding our **frontend** skillset: React, async functions, SASS, and real-time API integration all within a single hackathon sprint.  
- Delivering a fully working end-to-end pipeline: voice → structured data → embeddings → matchmaking → visual UI.

---

## What We Learned

**Planning pays off.**  
We spent the first few hours brainstorming and designing the system architecture before touching code, and it made all the difference. Once we started building, everything clicked into place. The result: a project we’re genuinely proud of and one that actually works.

---

## What’s Next for Sit Happens

- Add **multi-language support** for international events. This can be easily supported within ElevenLabs's framework, specifically.  
- Introduce **personality visualisation**, showing clusters of guests and predicted compatibility scores.  
- Integrate **real-time seat-swap simulation** — so organisers can preview the chaos before committing.  
- Package our matching API as a **plug-and-play SDK** for other event platforms.

---
