"""Module 7: Direction Injector - Adds directing/visual instructions."""

import json
from typing import List
from ..core.llm_client import LLMClient
from ..domain.schema_output import DirectionInstruction, FinalContentPlan
from ..prompts.director import get_direction_injection_prompt


class DirectionInjector:
    """Injects directing and visual instructions into polished script."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize DirectionInjector with LLM client.

        Args:
            llm_client: LLMClient instance for direction generation
        """
        self.llm_client = llm_client
        self.model = "gemini-2.5-pro"  # Use capable model for creative directions
        self.temperature = 0.7

    async def inject_directions(
        self,
        polished_script: str,
        topic: str,
        plan_id: str = None,
        visual_outlay = None
    ) -> FinalContentPlan:
        """
        Inject directing instructions into polished educational script.

        Args:
            polished_script: Polished script content
            topic: Original topic/concept
            plan_id: Optional plan identifier
            visual_outlay: Optional visual outlay to include in the plan

        Returns:
            FinalContentPlan with script, directions, and visual outlay
        """
        prompt = get_direction_injection_prompt(
            polished_script=polished_script,
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
            directions_data = json.loads(response_text)

            script_with_directions = directions_data.get("script_with_directions", polished_script)
            direction_instructions = directions_data.get("direction_instructions", [])

            # Validate and preserve XML tags in script_with_directions
            try:
                from ..utils.xml_validator import has_xml_tags, preserve_xml_tags
                if not has_xml_tags(script_with_directions):
                    print("⚠️  Warning: Script with directions appears to have lost XML tags. Preserving from polished script...")
                    script_with_directions = preserve_xml_tags(polished_script, script_with_directions)
            except ImportError:
                pass  # Validator not available, skip validation

            # Convert to DirectionInstruction objects with type validation
            directions = []
            for inst in direction_instructions:
                if not isinstance(inst, dict):
                    continue  # Skip non-dict items

                # Ensure all fields are correct types
                instruction_type = inst.get("instruction_type", "general")
                if not isinstance(instruction_type, str):
                    instruction_type = str(instruction_type) if instruction_type else "general"

                instruction = inst.get("instruction", "")
                if not isinstance(instruction, str):
                    instruction = str(instruction) if instruction else ""

                direction = DirectionInstruction(
                    instruction_type=instruction_type,
                    instruction=instruction
                )
                directions.append(direction)
        except (json.JSONDecodeError, KeyError):
            # Fallback: use polished script as-is with empty directions
            script_with_directions = polished_script
            directions = []

        return FinalContentPlan(
            plan_id=plan_id or f"plan_{hash(topic)}",
            topic=topic,
            polished_script=script_with_directions,
            directions=directions,
            visual_outlay=visual_outlay,
            metadata={
                "directions_count": len(directions)
            }
        )

