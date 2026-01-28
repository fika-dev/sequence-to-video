"""Module 5: Script Assembler - Creates draft script from skeleton and content."""

import json
import re
from ..core.llm_client import LLMClient
from ..domain.schema_output import XmlPattern, DraftScript
from ..domain.schema_data import ContentMaterial
from ..prompts.script_creator import get_script_creation_prompt


class ScriptAssembler:
    """Assembles draft script from XML skeleton and content material."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize ScriptAssembler with LLM client.

        Args:
            llm_client: LLMClient instance for script generation
        """
        self.llm_client = llm_client
        self.model = "gemini-2.5-pro"  # Use capable model for script creation
        self.temperature = 0.7  # Creative temperature for engaging scripts

    async def assemble_script(
        self,
        skeleton_pattern: XmlPattern,
        content_material: ContentMaterial,
        topic: str,
        persona: str = "general",
        additional_text: str = None,
        target_duration_seconds: int = None
    ) -> DraftScript:
        """
        Assemble educational draft script from skeleton pattern and content material.

        Args:
            skeleton_pattern: XML pattern to use as skeleton
            content_material: Content material to fill the skeleton
            topic: Original topic/concept
            persona: Target audience persona
            additional_text: Additional context or instructions
            target_duration_seconds: Target video duration in seconds (for TTS)

        Returns:
            DraftScript with assembled content
        """
        prompt = get_script_creation_prompt(
            skeleton_pattern=skeleton_pattern,
            content_material=content_material,
            topic=topic,
            persona=persona,
            additional_text=additional_text,
            target_duration_seconds=target_duration_seconds
        )

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=self.model,
            temperature=self.temperature,
            json_mode=False  # Script is text, not JSON
        )

        # Extract script content
        script_content = response.text if hasattr(response, 'text') else str(response)

        # Clean up script content (remove markdown formatting if present)
        script_content = self._clean_script_content(script_content)

        # Validate that XML tags are present
        try:
            from ..utils.xml_validator import validate_xml_structure
            is_valid, error_msg = validate_xml_structure(script_content, skeleton_pattern.tag_sequence)
            if not is_valid:
                print(f"⚠️  Warning: {error_msg}")
                print("   The script may not have proper XML tags. Continuing anyway...")
        except ImportError:
            pass  # Validator not available, skip validation

        return DraftScript(
            script_id=f"draft_{hash(topic)}",
            skeleton_pattern=skeleton_pattern,
            content=script_content,
            metadata={
                "topic": topic,
                "pattern_id": skeleton_pattern.pattern_id,
                "material_sources": len(content_material.transcripts)
            }
        )

    def _clean_script_content(self, content: str) -> str:
        """Clean script content by removing unwanted formatting."""
        # Remove markdown code blocks if present
        content = re.sub(r'```xml\n?', '', content)
        content = re.sub(r'```\n?', '', content)

        # Remove leading/trailing whitespace
        content = content.strip()

        return content

