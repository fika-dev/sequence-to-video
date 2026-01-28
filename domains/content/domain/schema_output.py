"""Output schemas for final content plan."""

from pydantic import BaseModel, Field
from typing import List, Optional


class XmlTag(BaseModel):
    """XML tag for a sentence in transcript."""

    tag_type: str = Field(..., description="Type of XML tag (e.g., 'hook', 'story', 'transition')")
    sentence: str = Field(..., description="The tagged sentence")
    order: int = Field(..., description="Order position in transcript")

    class Config:
        json_schema_extra = {
            "example": {
                "tag_type": "hook",
                "sentence": "This herbal medicine will change your life!",
                "order": 0
            }
        }


class XmlTaggedTranscript(BaseModel):
    """Transcript with XML tags applied."""

    transcript_id: str = Field(..., description="Identifier for the transcript")
    video_id: str = Field(..., description="Source video ID")
    tags: List[XmlTag] = Field(default_factory=list, description="List of XML tagged sentences")


class XmlPattern(BaseModel):
    """XML pattern/skeleton extracted from tagged transcripts."""

    pattern_id: str = Field(..., description="Unique identifier for the pattern")
    tag_sequence: List[str] = Field(..., description="Sequence of XML tag types (e.g., ['hook', 'intro', 'story', 'transition'])")
    description: Optional[str] = Field(None, description="Description of the pattern")
    popularity_score: Optional[float] = Field(None, description="Score based on how common this pattern is")

    class Config:
        json_schema_extra = {
            "example": {
                "pattern_id": "pattern_001",
                "tag_sequence": ["hook", "intro", "story", "transition", "call_to_action"],
                "description": "High-performing viral pattern",
                "popularity_score": 0.95
            }
        }


class DraftScript(BaseModel):
    """Draft script generated from skeleton and content material."""

    script_id: str = Field(..., description="Unique identifier for the script")
    skeleton_pattern: XmlPattern = Field(..., description="XML pattern used as skeleton")
    content: str = Field(..., description="Generated script content with XML tags")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "script_id": "script_001",
                "skeleton_pattern": {},
                "content": "<hook>...</hook><intro>...</intro>",
                "metadata": {}
            }
        }


class DirectionInstruction(BaseModel):
    """Visual/directing instruction for video editing and production."""

    instruction_type: str = Field(..., description="Type of instruction (e.g., 'visual_asset', 'transition', 'effect', 'text_overlay', 'animation')")
    instruction: str = Field(..., description="Detailed instruction")

    class Config:
        json_schema_extra = {
            "example": {
                "instruction_type": "visual_asset",
                "instruction": "개념을 설명하는 다이어그램 이미지 생성"
            }
        }


class VisualScene(BaseModel):
    """A single visual scene in the educational video."""

    scene_number: int = Field(..., description="Sequential scene number")
    scene_description: str = Field(..., description="What the scene portrays visually")
    subtitles: str = Field(..., description="The subtitle text that will be displayed with this scene")
    visual_generation_prompt: str = Field(..., description="Detailed, prompt-engineered prompt for generating the visual asset (image/video)")
    visual_type: str = Field(default="image", description="Type: 'image' or 'video'")

    class Config:
        json_schema_extra = {
            "example": {
                "scene_number": 1,
                "scene_description": "Diagram showing the concept structure",
                "subtitles": "Photosynthesis is how plants make food using sunlight.",
                "visual_generation_prompt": "Create an educational diagram showing...",
                "visual_type": "image"
            }
        }


class VisualOutlay(BaseModel):
    """Complete visual outlay mapping script to visual scenes for AI-generated assets."""

    scenes: List[VisualScene] = Field(..., description="List of all visual scenes")
    total_scenes: int = Field(..., description="Total number of scenes")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "scenes": [],
                "total_scenes": 5,
                "metadata": {}
            }
        }


class FinalContentPlan(BaseModel):
    """Final content plan with polished script, directions, and visual outlay."""

    plan_id: str = Field(..., description="Unique identifier for the content plan")
    topic: str = Field(..., description="Original topic")
    polished_script: str = Field(..., description="Final polished script content")
    directions: List[DirectionInstruction] = Field(default_factory=list, description="Directing/visual instructions")
    visual_outlay: Optional[VisualOutlay] = Field(None, description="Visual outlay mapping script to scenes")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "plan_id": "plan_001",
                "topic": "Diet Herbal Medicine",
                "polished_script": "Final script content...",
                "directions": [],
                "visual_outlay": None,
                "metadata": {}
            }
        }
