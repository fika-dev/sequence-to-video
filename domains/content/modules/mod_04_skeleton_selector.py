"""Module 4: Skeleton Selector - Finds most appropriate XML skeleton pattern."""

import json
from typing import List
from ..core.llm_client import LLMClient
from ..domain.schema_output import XmlTaggedTranscript, XmlPattern
from ..prompts.skeleton_selector import get_skeleton_selection_prompt


class SkeletonSelector:
    """Selects the most appropriate XML skeleton pattern from tagged transcripts."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize SkeletonSelector with LLM client.

        Args:
            llm_client: LLMClient instance for pattern selection
        """
        self.llm_client = llm_client
        self.model = "gemini-2.5-pro"  # Use more capable model for pattern analysis
        self.temperature = 0.4

    async def select_skeleton_pattern(
        self,
        tagged_transcripts: List[XmlTaggedTranscript],
        topic: str
    ) -> XmlPattern:
        """
        Select the most appropriate XML skeleton pattern.

        Args:
            tagged_transcripts: List of XML tagged transcripts to analyze
            topic: Original topic for context

        Returns:
            XmlPattern representing the selected skeleton structure

        Raises:
            ValueError: If no tagged transcripts are provided (no base patterns allowed)
        """
        if not tagged_transcripts:
            raise ValueError(
                "Cannot select skeleton pattern: No tagged transcripts available. "
                "Pattern selection requires tagged transcripts to analyze. "
                "Please ensure data fetching and tagging steps completed successfully."
            )

        prompt = get_skeleton_selection_prompt(
            tagged_transcripts=tagged_transcripts,
            topic=topic
        )

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=self.model,
            temperature=self.temperature,
            json_mode=True,
            search=False  # JSON mode doesn't support search tools
        )

        # Parse JSON response
        response_text = response.text if hasattr(response, 'text') else str(response)
        try:
            pattern_data = json.loads(response_text)
            selected = pattern_data.get("selected_pattern", {})

            if not selected:
                raise ValueError("LLM response did not contain a selected_pattern")

            tag_sequence = selected.get("tag_sequence", [])
            if not tag_sequence:
                raise ValueError("Selected pattern has empty tag_sequence")

            # Convert popularity_score to float if needed (Pydantic will handle coercion, but explicit is safer)
            popularity_score = selected.get("popularity_score", 0.8)
            if popularity_score is not None:
                try:
                    popularity_score = float(popularity_score) if not isinstance(popularity_score, (int, float)) else popularity_score
                except (ValueError, TypeError):
                    popularity_score = 0.8

            return XmlPattern(
                pattern_id=selected.get("pattern_id", "pattern_001"),
                tag_sequence=tag_sequence,
                description=selected.get("description"),
                popularity_score=popularity_score
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Try to analyze patterns manually from transcripts
            print(f"⚠️  Warning: Failed to parse LLM response, analyzing transcripts manually: {e}")
            return self._analyze_patterns_manually(tagged_transcripts)

    def _analyze_patterns_manually(
        self,
        tagged_transcripts: List[XmlTaggedTranscript]
    ) -> XmlPattern:
        """
        Fallback method to analyze patterns manually from transcripts.
        No default patterns - must extract from actual transcripts.
        """
        if not tagged_transcripts:
            raise ValueError(
                "Cannot analyze patterns: No tagged transcripts available. "
                "Pattern must be extracted from actual tagged transcripts."
            )

        # Extract tag sequences from all transcripts
        tag_sequences = []
        for transcript in tagged_transcripts:
            if transcript.tags:
                sequence = [tag.tag_type for tag in transcript.tags]
                tag_sequences.append(sequence)

        if not tag_sequences:
            raise ValueError(
                "Cannot extract pattern: Tagged transcripts have no tags. "
                "Transcripts must contain XML tags to determine pattern."
            )

        # Find most common sequence (simplified - could be enhanced)
        # Use first transcript's pattern as the pattern
        most_common = tag_sequences[0]

        return XmlPattern(
            pattern_id="pattern_extracted",
            tag_sequence=most_common,
            description="Pattern extracted from tagged transcripts",
            popularity_score=0.7
        )

