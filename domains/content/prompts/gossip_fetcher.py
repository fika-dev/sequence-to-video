"""Prompt templates for fetching and organizing gossip content."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.schema_data import GossipItem, FactItem


def get_gossip_fetching_prompt(
    search_results: List[dict] = None,
    topic: str = "",
    content_type: str = "gossip"
) -> str:
    """Generate prompt for extracting and organizing gossip or fact-based content using Gemini's Google Search."""
    # Build query that will be searched by Gemini's Google Search grounding
    if content_type == "gossip":
        search_query = f"{topic} gossip discussion community forum viral trending"
    else:  # fact
        search_query = f"{topic} research study news facts verified authoritative"

    # Include raw search results if provided (for backwards compatibility)
    results_text = ""
    if search_results:
        results_text = "\n".join([
            f"- Title: {r.get('title', 'N/A')}\n  URL: {r.get('url', 'N/A')}\n  Snippet: {r.get('snippet', 'N/A')}"
            for r in search_results[:20]  # Limit to top 20 results
        ])
        results_text = f"\nSearch Results:\n{results_text}\n"

    if content_type == "gossip":
        extraction_instructions = """
Instructions:
1. Extract community gossip, rumors, discussions, and social media trends related to the topic
2. Focus on what people are talking about, controversies, and viral discussions
3. Rate relevance to the topic (0.0 to 1.0)
4. Prioritize recent and trending content
"""
        output_format = """
{{
   "gossip_items": [
       {{
           "title": "Gossip item title",
           "source": "source URL or site name",
           "summary": "Brief summary of the gossip",
           "relevance_score": 0.9
       }}
   ]
}}
"""
    else:  # fact-based
        extraction_instructions = """
Instructions:
1. Extract fact-based news, research findings, and credible information related to the topic
2. Focus on verified information, studies, expert opinions, and reputable sources
3. Rate credibility (0.0 to 1.0) based on source reputation
4. Prioritize recent and authoritative content
"""
        output_format = """
{{
   "fact_items": [
       {{
           "title": "Fact item title",
           "source": "source URL or site name",
           "summary": "Brief summary of the fact/research",
           "credibility_score": 0.95
       }}
   ]
}}
"""

    return f"""
You are a content researcher specializing in extracting and organizing {content_type} information for video script creation.

Task: Search for and extract relevant {content_type} content about the topic, then organize it for video script creation.

Topic: {topic}
Search Query: {search_query}

{results_text}

{extraction_instructions}

Output format (JSON):
{output_format}

Search the web for current information about the topic and extract the most relevant and engaging {content_type} items that would be valuable for creating a viral short-form video script. Include source URLs or site names when available.
"""

