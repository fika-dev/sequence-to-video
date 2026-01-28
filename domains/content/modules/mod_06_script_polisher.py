"""Module 6: Script Polisher - Post-processes script for human-like tone."""

from ..core.llm_client import LLMClient
from ..domain.schema_output import DraftScript
from ..prompts.polisher import get_script_polish_prompt


class ScriptPolisher:
    """Polishes draft script to sound more human-like and natural."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize ScriptPolisher with LLM client.

        Args:
            llm_client: LLMClient instance for script polishing
        """
        self.llm_client = llm_client
        self.model = "gemini-2.5-pro"  # Use capable model for nuanced polishing
        self.temperature = 0.6  # Balanced for natural language

    async def polish_script(
        self,
        draft_script: DraftScript,
        topic: str
    ) -> str:
        """
        Polish the draft script to sound more human-like.

        Args:
            draft_script: Draft script to polish
            topic: Original topic for context

        Returns:
            Polished script content as string
        """
        prompt = get_script_polish_prompt(
            draft_script=draft_script.content,
            topic=topic
        )

        response = await self.llm_client.generate_gemini(
            content=prompt,
            model=self.model,
            temperature=self.temperature,
            json_mode=False
        )

        polished_content = response.text if hasattr(response, 'text') else str(response)

        # Clean up any markdown formatting
        polished_content = polished_content.strip()

        # Validate and preserve XML tags
        try:
            from ..utils.xml_validator import has_xml_tags, preserve_xml_tags
            if not has_xml_tags(polished_content):
                print("⚠️  Warning: Polished script appears to have lost XML tags. Attempting to preserve from draft...")
                polished_content = preserve_xml_tags(draft_script.content, polished_content)
        except ImportError:
            pass  # Validator not available, skip validation

        return polished_content

