"""Module 1: Query Generation Engine."""

import json
from typing import List
from ..core.llm_client import LLMClient
from ..domain.schema_input import UserRequest
from ..domain.schema_data import SearchQueries
from ..prompts.query_generation import get_search_query_prompt


class QueryEngine:
    """Generates comprehensive search queries from user topic."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize QueryEngine with LLM client.

        Args:
            llm_client: LLMClient instance for generating queries
        """
        self.llm_client = llm_client
        self.model = "gemini-2.0-flash"  # Fast model for query generation
        self.temperature = 0.7

    async def generate_queries(self, user_request: UserRequest) -> SearchQueries:
        """
        Generate search queries based on user topic.

        Args:
            user_request: User request containing topic and persona

        Returns:
            SearchQueries object with queries organized by tracks
        """
        prompt = get_search_query_prompt(
            topic=user_request.topic,
            persona=user_request.persona,
            additional_text=user_request.additional_text
        )

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=self.model,
            temperature=self.temperature,
            json_mode=True,  # Auto-disables search in LLMClient
            search=False  # Explicitly disable search for query generation
        )

        # Parse JSON response
        response_text = response.text if hasattr(response, 'text') else str(response)

        # Try multiple parsing strategies
        queries_data = None

        # Strategy 1: Direct JSON parse
        try:
            queries_data = json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Strategy 2: Use LLMClient's parse helper (handles markdown code blocks)
        if not queries_data:
            try:
                parsed = self.llm_client.parse_and_get_result(response, key=None)
                if isinstance(parsed, dict):
                    queries_data = parsed
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse query response with helper: {e}")

        # Strategy 3: Try to extract JSON from markdown code blocks manually
        if not queries_data:
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    queries_data = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass

        # Strategy 4: Fallback
        if not queries_data:
            print(f"⚠️  Warning: Could not parse query response. Raw response preview: {response_text[:200]}...")
            queries_data = self._parse_queries_fallback(response_text)

        # Validate that we got meaningful data
        track1 = queries_data.get("track1", [])
        track2 = queries_data.get("track2", [])
        track3 = queries_data.get("track3", [])

        if not (track1 or track2 or track3):
            print(f"⚠️  Warning: No queries generated. Response data: {queries_data}")
            print(f"⚠️  Full response text: {response_text[:500]}...")

        return SearchQueries(
            track1=track1,
            track2=track2,
            track3=track3
        )

    def _parse_queries_fallback(self, text: str) -> dict:
        """Fallback parser if JSON parsing fails."""
        # Simple fallback - can be enhanced
        return {
            "track1": [],
            "track2": [],
            "track3": []
        }

