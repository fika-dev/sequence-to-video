"""Adapter to convert FinalContentPlan to sequence JSON format."""

from typing import Any
from domains.content.domain.schema_output import FinalContentPlan, VisualScene, DirectionInstruction


class ContentPlanAdapter:
    """Converts FinalContentPlan to sequence JSON structure."""
    
    @staticmethod
    def to_sequence_input(content_plan: FinalContentPlan) -> dict:
        """Convert FinalContentPlan to dict for sequence generator."""
        return {
            "polished_script": content_plan.polished_script,
            "directions": [
                {
                    "instruction_type": d.instruction_type,
                    "instruction": d.instruction
                }
                for d in content_plan.directions
            ],
            "visual_outlay": {
                "total_scenes": content_plan.visual_outlay.total_scenes if content_plan.visual_outlay else 0,
                "scenes": [
                    {
                        "scene_number": scene.scene_number,
                        "scene_description": scene.scene_description,
                        "subtitles": scene.subtitles,
                        "visual_type": scene.visual_type,
                        "visual_generation_prompt": scene.visual_generation_prompt
                    }
                    for scene in (content_plan.visual_outlay.scenes if content_plan.visual_outlay else [])
                ]
            } if content_plan.visual_outlay else None,
            "topic": content_plan.topic,
            "metadata": content_plan.metadata
        }
