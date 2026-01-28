"""Prompt templates for query generation."""

from typing import List


def get_search_query_prompt(topic: str, persona: str, additional_text: str = None) -> str:
    """Generate prompt for creating comprehensive search queries."""
    additional_context = ""
    if additional_text:
        additional_context = f"\nAdditional Context/Instructions: {additional_text}"

    return f"""
You are a research expert specializing in educational content research and information gathering for educational videos.

Task: Generate comprehensive search queries to find relevant educational information, explanations, and visual aids related to the topic/concept.

User Topic/Concept: {topic}
Target Audience: {persona}{additional_context}

Generate 3 tracks of search queries focused on educational content. Each track should have multiple queries that approach the topic from different educational angles:
- Track 1: Educational explanations and tutorials (how-to, explanations, definitions, concept breakdowns)
- Track 2: Academic sources and detailed concept breakdowns (in-depth explanations, research, expert insights)
- Track 3: Real-world examples, practical applications, and analogies (real-life examples, case studies, practical demonstrations, relatable analogies, step-by-step applications)

Output format (JSON):
{{
   "track1": ["query1", "query2", "query3"],
   "track2": ["query1", "query2", "query3"],
   "track3": ["query1", "query2", "query3"]
}}

Make queries specific, clear, and focused on finding educational content that can help explain the concept clearly. Each track should have at least 3-5 queries.
"""

