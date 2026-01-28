"""Input schemas for user requests."""

from pydantic import BaseModel, Field
from typing import Optional


class UserRequest(BaseModel):
    """User request schema for content generation."""

    topic: str = Field(..., description="The main topic for the video script (e.g., 'Diet Herbal Medicine')")
    persona: str = Field(
        default="general",
        description="Target audience persona or style preference"
    )
    additional_text: Optional[str] = Field(
        default=None,
        description="Additional text input providing extra context, instructions, or requirements"
    )
    target_duration_seconds: Optional[int] = Field(
        default=None,
        description="Target video duration in seconds (e.g., 30, 60, 90). Script will be adjusted to fit this duration when read by TTS."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "topic": "Diet Herbal Medicine",
                "persona": "health-conscious millennials",
                "additional_text": "Focus on recent research findings and avoid medical claims",
                "target_duration_seconds": 60
            }
        }


class ShortsStrategy(BaseModel):
    """Strategy schema for short-form video content structure."""

    title: str = Field(..., description="Title of the strategy (e.g., 'Giving a shocking prediction')")
    instructions: str = Field(..., description="Detailed instructions for the strategy")
    example: str = Field(..., description="Example tagged script demonstrating the strategy in XML format")

    def to_strategy_string(self) -> str:
        """Convert strategy to formatted string for prompts."""
        return f"## {self.title}\n{self.instructions}\n- An example of tagged script is provided below.\n{self.example}"

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Giving a shocking prediction",
                "instructions": "Start with a shocking prediction that can grab the viewer's attention.\n- Give a unique insight relevant to the prediction.\n- Conclude the prediction with a logical conclusion.",
                "example": "<shocking_prediction>중국이 지금 60조 달러예요.</shocking_prediction><unique_insight>그런데 gdp는 미국이 25조고 중국은 한 19조 정도밖에 안 돼요.</unique_insight><conclusion>중국의 부동산 가격이 가격이 아니라는 거죠.</conclusion>"
            }
        }
