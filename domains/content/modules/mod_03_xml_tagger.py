"""Module 3: XML Tagger - Tags transcript sentences with XML tags."""

import json
from typing import List, Optional
from ..core.llm_client import LLMClient
from ..domain.schema_data import Transcript
from ..domain.schema_input import ShortsStrategy
from ..domain.schema_output import XmlTaggedTranscript, XmlTag
from ..prompts.tag_strategy import get_tag_strategy_prompt, get_tag_strategy_prompt_content
from ..prompts.strategy_instructions import get_strategy_instruction_prompt


class XmlTagger:
    """Tags transcript sentences with appropriate XML tags."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize XmlTagger with LLM client.

        Args:
            llm_client: LLMClient instance for tagging
        """
        self.llm_client = llm_client
        self.model = "gemini-2.0-flash"
        self.temperature = 0.3  # Lower temperature for more consistent tagging

    async def tag_transcript(
        self,
        transcript: Transcript,
        category: str = "real estate",
        title: Optional[str] = None
    ) -> XmlTaggedTranscript:
        """
        Tag a transcript by identifying its strategy and extracting tagged content.

        Args:
            transcript: Transcript object to tag
            category: Category/domain of the content (e.g., "real estate", "economics")
            title: Video title (uses video metadata title if not provided)

        Returns:
            XmlTaggedTranscript with tagged sentences
        """
        # Combine sentences if available, otherwise use full text
        transcript_text = ". ".join(transcript.sentences) if transcript.sentences else transcript.text

        # Use provided title or fall back to video metadata title
        video_title = title or transcript.video_metadata.title or "Untitled Video"

        # Get prompt dict with role, system, and content
        prompt_dict = get_tag_strategy_prompt(
            short_transcript=transcript_text,
            category=category,
            title=video_title
        )

        # Extract content (system context is already included in the content string)
        prompt_content = prompt_dict["content"]

        response = await self.llm_client.generate_gemini(
            content=prompt_content,
            model=self.model,
            temperature=self.temperature,
            json_mode=True,
            search=False  # JSON mode doesn't support search tools
        )

        # Parse JSON response
        response_text = response.text if hasattr(response, 'text') else str(response)
        try:
            result_data = json.loads(response_text)
            result = result_data.get("result", {})
        except json.JSONDecodeError:
            # Fallback parsing
            result = self.llm_client.parse_and_get_result(response, key="result")

        # Extract tagged script and parse XML tags
        tagged_script = result.get("tagged_script", "")
        tags = self._parse_tagged_script(tagged_script)

        # If no tags parsed, fall back to simple tagging
        if not tags:
            tags = self._create_fallback_tags_from_transcript(transcript)

        return XmlTaggedTranscript(
            transcript_id=f"transcript_{transcript.video_metadata.video_id}",
            video_id=transcript.video_metadata.video_id,
            tags=tags
        )

    def _parse_tagged_script(self, tagged_script: str) -> List[XmlTag]:
        """
        Parse XML tagged script string into XmlTag objects.

        Args:
            tagged_script: String with XML tags like "<tag>content</tag>"

        Returns:
            List of XmlTag objects
        """
        import re
        tags = []

        # Pattern to match XML tags: <tag_name>content</tag_name>
        pattern = r'<([^>]+)>([^<]*)</\1>'
        matches = re.finditer(pattern, tagged_script)

        for order, match in enumerate(matches):
            tag_type = match.group(1)
            content = match.group(2).strip()

            if content:  # Only add non-empty tags
                tag = XmlTag(
                    tag_type=tag_type,
                    sentence=content,
                    order=order
                )
                tags.append(tag)

        return tags

    def _create_fallback_tags_from_transcript(self, transcript: Transcript) -> List[XmlTag]:
        """Create simple fallback tags if strategy parsing fails."""
        sentences = transcript.sentences if transcript.sentences else [transcript.text]
        tags = []

        for i, sentence in enumerate(sentences):
            # Simple heuristic tagging
            tag_type = "story"
            if i == 0:
                tag_type = "hook"
            elif i < 3:
                tag_type = "intro"
            elif i == len(sentences) - 1:
                tag_type = "call_to_action"

            tag = XmlTag(
                tag_type=tag_type,
                sentence=sentence,
                order=i
            )
            tags.append(tag)

        return tags

    async def tag_multiple_transcripts(
        self,
        transcripts: List[Transcript],
        category: str = "real estate",
        title: Optional[str] = None
    ) -> List[XmlTaggedTranscript]:
        """
        Tag multiple transcripts.

        Args:
            transcripts: List of transcripts to tag
            category: Category/domain of the content
            title: Optional title (uses video metadata if not provided)

        Returns:
            List of XmlTaggedTranscript objects
        """
        tagged_transcripts = []
        for transcript in transcripts:
            # Use transcript-specific title if available
            transcript_title = title or transcript.video_metadata.title
            tagged = await self.tag_transcript(
                transcript=transcript,
                category=category,
                title=transcript_title
            )
            tagged_transcripts.append(tagged)

        return tagged_transcripts


    async def create_tag_instructions(
        self,
        strategy: ShortsStrategy,
        model: str = "gemini-2.0-flash"
    ) -> List[str]:
        """
        Create step-by-step instructions for extracting tagged script based on a strategy.

        This generates instructions that can be used to tag transcripts according to a specific
        strategy pattern (e.g., "shocking prediction", "problem-solution", etc.).

        Args:
            strategy: ShortsStrategy object containing title, instructions, and example
            model: Model to use for generation (default: gemini-2.0-flash)

        Returns:
            List of instruction strings for extracting tagged script
        """
        strategy_string = strategy.to_strategy_string()
        prompt = get_strategy_instruction_prompt(
            strategy=strategy_string,
            system_context="You are an economist who is analyzing the current real estate market, and also Youtube creator."
        )

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=model,
            temperature=self.temperature,
            json_mode=True,
            search=False  # JSON mode doesn't support search tools
        )

        # Parse response using the helper method
        result = self.llm_client.parse_and_get_result(response, key="result")

        # Extract instructions list
        # result might be the instructions list directly, or a dict containing instructions
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            instructions = result.get("instructions", [])
            return instructions if isinstance(instructions, list) else []
        else:
            return []

    async def tag_transcript_with_strategy(
        self,
        transcript: Transcript,
        strategy: ShortsStrategy,
        tag_instructions: Optional[List[str]] = None,
        model: str = "gemini-2.0-flash"
    ) -> XmlTaggedTranscript:
        """
        Tag a transcript using a specific strategy pattern.

        Args:
            transcript: Transcript object to tag
            strategy: ShortsStrategy defining the tagging pattern
            tag_instructions: Optional pre-generated instructions (if None, will generate them)
            model: Model to use for generation

        Returns:
            XmlTaggedTranscript with strategy-based tags
        """
        # Generate instructions if not provided
        if tag_instructions is None:
            tag_instructions = await self.create_tag_instructions(strategy, model)

        # Create prompt for tagging with strategy
        transcript_text = ". ".join(transcript.sentences) if transcript.sentences else transcript.text

        instructions_text = "\n".join([f"{i+1}. {inst}" for i, inst in enumerate(tag_instructions)])

        prompt = f"""
You are an expert in analyzing short-form video scripts and extracting content according to specific strategies.

Task: Extract and tag sections from the transcript according to the strategy instructions.

Strategy: {strategy.title}
Strategy Instructions: {strategy.instructions}

Step-by-step Instructions:
{instructions_text}

Transcript:
{transcript_text}

Output format (JSON):
{{
   "tagged_sections": [
       {{
           "tag_type": "tag_name",
           "content": "extracted content from transcript",
           "order": 0
       }}
   ]
}}

Important: Extract content directly from the transcript without modifying it. Match the tag types from the strategy example.
"""

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=model,
            temperature=self.temperature,
            json_mode=True,
            search=False  # JSON mode doesn't support search tools
        )

        # Parse response
        response_text = response.text if hasattr(response, 'text') else str(response)
        try:
            tagging_data = json.loads(response_text)
        except json.JSONDecodeError:
            tagging_data = self.llm_client.parse_and_get_result(response)

        # Convert to XmlTag objects
        tags = []
        tagged_sections = tagging_data.get("tagged_sections", [])

        for item in tagged_sections:
            tag = XmlTag(
                tag_type=item.get("tag_type", "story"),
                sentence=item.get("content", ""),
                order=item.get("order", len(tags))
            )
            tags.append(tag)

        return XmlTaggedTranscript(
            transcript_id=f"transcript_{transcript.video_metadata.video_id}",
            video_id=transcript.video_metadata.video_id,
            tags=tags
        )

