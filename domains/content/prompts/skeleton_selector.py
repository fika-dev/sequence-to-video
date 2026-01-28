"""Prompt templates for selecting appropriate XML skeleton pattern."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.schema_output import XmlTaggedTranscript


def get_skeleton_selection_prompt(
    tagged_transcripts: List["XmlTaggedTranscript"],
    topic: str
) -> str:
    """Generate prompt for finding the most appropriate XML skeleton pattern."""
    # Format tagged transcripts for prompt
    transcripts_summary = ""
    for i, transcript in enumerate(tagged_transcripts):
        tag_sequence = [tag.tag_type for tag in transcript.tags]
        transcripts_summary += f"\nTranscript {i+1} (Video ID: {transcript.video_id}):\n"
        transcripts_summary += f"Tag Sequence: {' -> '.join(tag_sequence)}\n"

    return f"""
You are an expert in educational content pattern analysis for short-form educational videos.

Task: Analyze multiple tagged transcripts and identify the most effective XML tag pattern (skeleton) that should be used as the structure for generating an educational explanatory script.

Topic/Concept: {topic}

Tagged Transcripts Analysis:
{transcripts_summary}

Instructions:
1. Identify common XML tag patterns across the transcripts
2. Evaluate which pattern best supports educational explanation and learning
3. Consider the topic context when selecting the pattern - prioritize patterns that support concept explanation
4. The pattern should be a sequence of XML tag types that represents the optimal structure for educational content
5. Consider educational flow over viral hooks - focus on what helps learners understand

Output format (JSON):
{{
   "selected_pattern": {{
       "pattern_id": "pattern_001",
       "tag_sequence": ["intro", "explanation", "example", "summary"],
       "description": "Description of why this pattern is optimal for educational content",
       "popularity_score": 0.95
   }},
   "alternative_patterns": [
       {{
           "pattern_id": "pattern_002",
           "tag_sequence": ["tag1", "tag2", "tag3"],
           "description": "Alternative educational option",
           "popularity_score": 0.85
       }}
   ]
}}

Select the pattern that best balances educational effectiveness, concept explanation support, topic relevance, and engagement. Focus on identifying the core structural flow that makes educational content effective for learning.
"""

