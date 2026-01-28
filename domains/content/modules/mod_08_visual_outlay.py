"""Module 8: Visual Outlay Generator - Creates visual outlay mapping script to visual scenes."""

import json
from typing import List
from ..core.llm_client import LLMClient
from ..domain.schema_output import VisualOutlay, VisualScene
from ..prompts.visual_outlay import get_visual_outlay_prompt


class VisualOutlayGenerator:
    """Generates visual outlay mapping script to AI-generated visual assets."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize VisualOutlayGenerator with LLM client.

        Args:
            llm_client: LLMClient instance for visual outlay generation
        """
        self.llm_client = llm_client
        self.model = "gemini-2.5-pro"  # Use capable model for visual planning
        self.temperature = 0.7

    async def generate_visual_outlay(
        self,
        polished_script: str,
        topic: str
    ) -> VisualOutlay:
        """
        Generate visual outlay that maps script sections to visual scenes.

        Args:
            polished_script: Polished script content
            topic: Original topic/concept

        Returns:
            VisualOutlay with scenes, descriptions, and generation prompts
        """
        prompt = get_visual_outlay_prompt(
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
            outlay_data = json.loads(response_text)

            scenes_data = outlay_data.get("scenes", [])
            visual_prompts = outlay_data.get("visual_generation_prompts", {})

            # Convert to VisualScene objects
            scenes = []
            for scene_data in scenes_data:
                if not isinstance(scene_data, dict):
                    continue

                # Get enhanced visual generation prompt if available
                scene_num = scene_data.get("scene_number")
                enhanced_prompt = visual_prompts.get(f"scene_{scene_num}", scene_data.get("visual_generation_prompt", ""))

                scene = VisualScene(
                    scene_number=scene_data.get("scene_number", 0),
                    scene_description=scene_data.get("scene_description", ""),
                    subtitles=scene_data.get("subtitles", scene_data.get("script_alignment", "")),  # Support both old and new field names
                    visual_generation_prompt=enhanced_prompt or scene_data.get("visual_generation_prompt", ""),
                    visual_type=scene_data.get("visual_type", "image")
                )
                scenes.append(scene)

            # Sort scenes by scene number
            scenes.sort(key=lambda x: x.scene_number)

            return VisualOutlay(
                scenes=scenes,
                total_scenes=len(scenes),
                metadata={
                    "topic": topic,
                    "script_length": len(polished_script)
                }
            )

        except (json.JSONDecodeError, KeyError) as e:
            # Fallback: create empty visual outlay
            return VisualOutlay(
                scenes=[],
                total_scenes=0,
                metadata={
                    "error": f"Failed to parse visual outlay: {str(e)}",
                    "topic": topic
                }
            )

