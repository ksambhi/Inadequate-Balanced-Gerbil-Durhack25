"""
Matching Agent using LangGraph and Gemini 2.5 Flash.

This agent finds the best seat match for an attendee based on their
facts/opinions and a chaos level (0-10). Low chaos = agreeable matches,
high chaos = arguments.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, MessagesState, START, END
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


class MatchingAgentState(MessagesState):
    """State for the matching agent."""
    # Input fields
    attendee_id: int
    event_id: int  # Filter matches to same event only
    facts: List[str]
    opinions: List[Dict[str, str]]  # List of {"question": str, "answer": str}
    chaos_level: float  # 0-10
    exclude_attendee_ids: List[int]  # List of attendees already paired
    
    # Internal state
    search_count: int
    search_attempts: int  # Number of search attempts made (max 3)
    candidates: List[Dict[str, Any]]  # List of potential matches
    best_match: Optional[MatchResult]


# Global instances
embedding_service = EmbeddingService()
vector_db = VectorDB()


@tool
async def search_similar_attendees(
    query_text: str,
    attendee_id: int,
    event_id: int,
    exclude_attendee_ids: List[int],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for attendees with similar facts/opinions in the vector database.
    
    Args:
        query_text: The text to search for (e.g., a fact or opinion)
        attendee_id: The ID of the attendee to exclude from results
        event_id: The event ID to filter results by
        exclude_attendee_ids: List of attendee IDs already paired to exclude
        limit: Maximum number of results to return
    
    Returns:
        List of matches with attendee_id, fact, and similarity score
    """
    logger.debug(f"Searching similar attendees for query: {query_text}")
    query_embedding = embedding_service.embed_query(query_text)
    results = await vector_db.search_similar(
        query_embedding=query_embedding,
        limit=limit,
        event_id=event_id,
        exclude_attendee_id=attendee_id,
        exclude_attendee_ids=exclude_attendee_ids
    )
    
    # Format results consistently
    matches = [
        {
            "attendee_id": int(row[0]),
            "fact": row[1],
            "similarity": float(row[2])
        }
        for row in results
    ]
    
    logger.debug(f"Found {len(matches)} similar attendees")
    return matches


@tool
async def search_opposite_attendees(
    query_text: str,
    attendee_id: int,
    event_id: int,
    exclude_attendee_ids: List[int],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search for attendees with OPPOSITE facts/opinions in the vector database.
    Use this for high chaos levels to find people who will disagree.
    
    Args:
        query_text: The text to search for opposites of
        attendee_id: The ID of the attendee to exclude from results
        event_id: The event ID to filter results by
        exclude_attendee_ids: List of attendee IDs already paired to exclude
        limit: Maximum number of results to return
    
    Returns:
        List of matches with attendee_id, fact, and dissimilarity score
    """
    logger.debug(f"Searching opposite attendees for query: {query_text}")
    query_embedding = embedding_service.embed_query(query_text)
    
    # Search for opposites
    results = await vector_db.search_opposite(
        query_embedding=query_embedding,
        limit=limit,
        event_id=event_id,
        exclude_attendee_id=attendee_id,
        exclude_attendee_ids=exclude_attendee_ids
    )
    
    # Format results
    matches = [
        {
            "attendee_id": int(row[0]),
            "fact": row[1],
            "dissimilarity": float(row[2])
        }
        for row in results
    ]
    
    logger.debug(f"Found {len(matches)} opposite attendees")
    return matches


rate_limiter = InMemoryRateLimiter(
    requests_per_second=(1/6),  # 10 requests per minute
    check_every_n_seconds=0.1,  # Wake up every 100 ms to check whether allowed to make a request,
    max_bucket_size=10,  # Controls the maximum burst size.
)

class MatchingAgent:
    """Agent that finds the best seat match for an attendee."""
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False):
        """Initialize the matching agent."""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GOOGLE_API_KEY not found in environment variables"
            )
        
        self.verbose = verbose
        if self.verbose:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Initialize the LLM with Gemini 2.5 Flash
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=self.api_key,
            temperature=0.7,
            rate_limiter=rate_limiter,
        )
        
        # Bind tools to LLM
        self.tools = [search_similar_attendees, search_opposite_attendees]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
        
        if self.verbose:
            logger.info("✓ Matching agent initialized")
            logger.info("  Model: gemini-2.5-flash")
            logger.info(f"  Tools: {len(self.tools)} available")
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        # Create graph
        workflow = StateGraph(MatchingAgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)
        workflow.add_node("finalize", self._finalize_node)
        
        # Add edges
        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "finalize": "finalize",
                "end": END
            }
        )
        workflow.add_edge("tools", "agent")
        workflow.add_edge("finalize", END)
        
        return workflow.compile()
    
    async def _agent_node(self, state: MatchingAgentState) -> Dict[str, Any]:
        """Agent reasoning node."""
        if self.verbose:
            logger.info("\n" + "="*60)
            logger.info("🤖 AGENT REASONING")
            logger.info(f"Attendee ID: {state['attendee_id']}")
            logger.info(f"Chaos Level: {state['chaos_level']}/10")
            logger.info(f"Search Count: {state['search_count']}/1")
            logger.info("="*60)
        
        # Build the system prompt based on chaos level
        if state["chaos_level"] <= 3:
            strategy = (
                "Find people with SIMILAR interests, opinions, and facts. "
                "Look for harmony and agreement."
            )
        elif state["chaos_level"] <= 6:
            strategy = (
                "Find people with MODERATELY different views. "
                "Some agreement, some diversity."
            )
        else:
            strategy = (
                "Find people with OPPOSITE views and interests. "
                "Maximize disagreement and chaos!"
            )

        if self.verbose:
            logger.info(f"Strategy: {strategy}")
            logger.info(f"Facts: {state['facts']}")
            logger.info(f"Opinions: {state['opinions']}")

        system_prompt = f"""You are a creative seating arrangement assistant.
Your job is to find the best person for attendee {state["attendee_id"]} \
to sit next to.

CHAOS LEVEL: {state["chaos_level"]}/10
STRATEGY: {strategy}

Attendee's Facts: {state["facts"]}
Attendee's Opinions: {state["opinions"]}

You have access to tools to search the vector database:
- search_similar_attendees: Find people with similar views \
(use for LOW chaos)
- search_opposite_attendees: Find people with opposite views \
(use for HIGH chaos)

IMPORTANT: You can make a MAXIMUM of 3 searches total.
SEARCH ATTEMPT: {state["search_attempts"] + 1}/3

Make ONE search with a relevant query combining the attendee's \
facts and opinions. Be creative and strategic with your search term.

If this is attempt 2 or 3, try a DIFFERENT query strategy than before:
- Attempt 1: Use the most prominent fact/opinion
- Attempt 2: Try a different fact or opinion
- Attempt 3: Use a broader or more general query

After your search returns results, DO NOT call tools again. \
Let the system finalize the match.
"""

        messages = [SystemMessage(content=system_prompt)] + state["messages"]

        if self.verbose:
            logger.info("Calling LLM with tools...")
        
        # Call LLM with tools
        response = await self.llm_with_tools.ainvoke(messages)
        
        if self.verbose:
            if hasattr(response, "tool_calls") and response.tool_calls:
                num_tools = len(response.tool_calls)
                logger.info(f"✓ LLM decided to call {num_tools} tool(s)")
                for tc in response.tool_calls:
                    logger.info(f"  Tool: {tc['name']}")
                    logger.info(f"  Args: {tc['args']}")
            else:
                logger.info("✓ LLM response received (no tools called)")

        return {
            "messages": [response]
        }
    
    async def _tools_node(self, state: MatchingAgentState) -> Dict[str, Any]:
        """Execute tools and update state."""
        last_message = state["messages"][-1]
        
        if (not hasattr(last_message, "tool_calls") or
                not last_message.tool_calls):
            return {}
        
        if self.verbose:
            num_tools = len(last_message.tool_calls)
            logger.info(f"\n🔧 Executing {num_tools} tool(s)...")
        
        # Execute each tool call
        tool_messages = []
        all_candidates = list(state.get("candidates", []))
        
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"].copy()
            
            # Inject event_id and exclude_attendee_ids into tool arguments
            tool_args["event_id"] = state.get("event_id")
            tool_args["exclude_attendee_ids"] = state.get(
                "exclude_attendee_ids", []
            )
            
            if self.verbose:
                logger.info(f"  Tool: {tool_name}")
                logger.info(f"  Query: {tool_args.get('query_text', 'N/A')}")
                logger.info(f"  Event ID: {tool_args['event_id']}")
                num_excluded = len(tool_args["exclude_attendee_ids"])
                logger.info(f"  Excluding: {num_excluded} attendees")
            
            # Find and execute the tool
            tool_func = None
            for available_tool in self.tools:
                if available_tool.name == tool_name:
                    tool_func = available_tool
                    break
            
            if tool_func:
                try:
                    result = await tool_func.ainvoke(tool_args)
                    
                    # Add results to candidates
                    if isinstance(result, list):
                        all_candidates.extend(result)
                    
                    if self.verbose:
                        result_count = (
                            len(result) if isinstance(result, list) else 0
                        )
                        logger.info(f"  ✓ Found {result_count} results")
                    
                    # Create tool message
                    tool_messages.append(
                        ToolMessage(
                            content=str(result),
                            tool_call_id=tool_call["id"]
                        )
                    )
                except Exception as e:
                    logger.error(f"Tool execution failed: {e}")
                    tool_messages.append(
                        ToolMessage(
                            content=f"Error: {str(e)}",
                            tool_call_id=tool_call["id"]
                        )
                    )
        
        # Increment search count and attempts
        new_search_count = state["search_count"] + 1
        new_search_attempts = state["search_attempts"] + 1
        
        if self.verbose:
            old_count = state['search_count']
            logger.info(
                f"Search count updated: {old_count} → {new_search_count}"
            )
            logger.info(
                f"Search attempts: {new_search_attempts}/3, "
                f"Total candidates: {len(all_candidates)}"
            )
        
        return {
            "messages": tool_messages,
            "search_count": new_search_count,
            "search_attempts": new_search_attempts,
            "candidates": all_candidates
        }
    
    def _should_continue(self, state: MatchingAgentState) -> str:
        """Decide whether to continue searching or finalize."""
        last_message = state["messages"][-1]
        search_attempts = state.get("search_attempts", 0)
        has_candidates = len(state.get("candidates", [])) > 0

        # HARD LIMIT: If we've already made 3 searches, finalize
        if search_attempts >= 3:
            if self.verbose:
                if has_candidates:
                    logger.info(
                        f"✓ Hit 3 search limit with "
                        f"{len(state['candidates'])} candidates, finalizing..."
                    )
                else:
                    logger.info(
                        "✗ Hit 3 search limit with no candidates, "
                        "finalizing..."
                    )
            return "finalize"

        # If the LLM called tools and we haven't hit limit, continue
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            if self.verbose:
                logger.info(
                    f"→ Executing tools (attempt {search_attempts + 1}/3)..."
                )
            return "continue"

        # If we have candidates, finalize early (don't waste searches)
        if has_candidates:
            if self.verbose:
                logger.info(
                    f"✓ Found {len(state['candidates'])} candidates, "
                    "finalizing..."
                )
            return "finalize"
        
        # If no candidates and haven't tried 3 times yet, continue
        if search_attempts < 3:
            if self.verbose:
                logger.info(
                    f"No candidates found. Retrying "
                    f"({search_attempts}/3 attempts)"
                )
            return "continue"

        # Otherwise check if LLM wants to finalize
        content_lower = str(last_message.content).lower()
        if "final" in content_lower or "best match" in content_lower:
            if self.verbose:
                logger.info("→ LLM signaled to finalize")
            return "finalize"

        return "finalize"

    async def _finalize_node(
        self, state: MatchingAgentState
    ) -> Dict[str, Any]:
        """Finalize and output the best match using structured output."""
        if self.verbose:
            logger.info("\n" + "="*60)
            logger.info("🎯 FINALIZING MATCH")
            logger.info("="*60)
        
        # Check if we have any candidates
        candidates = state.get("candidates", [])
        attendee_id = state["attendee_id"]
        
        if not candidates:
            # No matches found after all attempts
            if self.verbose:
                logger.warning(
                    f"No candidates found after "
                    f"{state['search_attempts']} attempts"
                )
            
            # Return a no-match result
            result = MatchResult(
                attendee_id=-1,
                reasoning=(
                    f"No suitable matches found after "
                    f"{state['search_attempts']} search attempts"
                ),
                confidence=0.0
            )
            
            return {"best_match": result}
        
        # Create a summarization prompt
        summary_prompt = f"""Based on all the searches performed, \
select the BEST match for attendee {attendee_id}.

Chaos Level: {state["chaos_level"]}/10
Search Results: {candidates}
Number of candidates: {len(candidates)}

Select the attendee ID that best fits the strategy and provide your \
reasoning.
"""

        # Use structured output
        llm_with_structure = self.llm.with_structured_output(MatchResult)

        messages = [
            SystemMessage(content=summary_prompt),
            *state["messages"]
        ]

        if self.verbose:
            logger.info("Generating structured output...")
        
        result = await llm_with_structure.ainvoke(messages)
        
        if self.verbose:
            logger.info(f"✓ Match found: Attendee {result.attendee_id}")
            logger.info(f"  Reasoning: {result.reasoning}")
            logger.info(f"  Confidence: {result.confidence:.2f}")
            logger.info("="*60 + "\n")

        return {
            "best_match": result
        }
    
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
        Find the best seat match for an attendee.
        
        Args:
            attendee_id: ID of the attendee to find a match for
            event_id: ID of the event (only match within same event)
            facts: List of facts about the attendee
            opinions: List of opinion dicts with "question" and "answer"
            chaos_level: Chaos level from 0 (harmony) to 10 (max chaos)
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
            logger.info("STARTING MATCHING AGENT")
            logger.info("="*60)
            logger.info(f"Attendee ID: {attendee_id}")
            logger.info(f"Event ID: {event_id}")
            logger.info(f"Facts: {len(facts)}")
            logger.info(f"Opinions: {len(opinions)}")
            logger.info(f"Chaos Level: {chaos_level}/10")
            logger.info(f"Excluded: {len(exclude_attendee_ids)} attendees")
            logger.info("="*60)
        
        # Initialize state
        initial_state = {
            "messages": [
                HumanMessage(
                    content=(
                        f"Find the best seat match for attendee "
                        f"{attendee_id}. Chaos level: {chaos_level}/10"
                    )
                )
            ],
            "attendee_id": attendee_id,
            "event_id": event_id,
            "facts": facts,
            "opinions": opinions,
            "chaos_level": chaos_level,
            "exclude_attendee_ids": exclude_attendee_ids,
            "search_count": 0,
            "search_attempts": 0,
            "candidates": [],
            "best_match": None
        }
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        # Return the best match
        if final_state.get("best_match"):
            return final_state["best_match"]
        else:
            # Fallback if no match found
            if self.verbose:
                logger.warning("⚠️  No match found, returning fallback")
            return MatchResult(
                attendee_id=-1,
                reasoning="No suitable match found in the database",
                confidence=0.0
            )


# Example usage
async def main():
    """Example usage of the matching agent."""
    agent = MatchingAgent()
    
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
