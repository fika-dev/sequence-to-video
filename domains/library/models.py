from pathlib import Path

from pydantic import BaseModel, Field


class VideoClip(BaseModel):
    clip_id: str
    source_file: Path
    start_time: float
    end_time: float
    description: str
    tags: list[str] = Field(default_factory=list)
    camera_angle: str | None = None
    camera_movement: str | None = None
    embedding: list[float] | None = Field(default=None, exclude=True)
    embedding_path: str | None = None

    content_type: str | None = None
    appeal_point: str | None = None
    product_focus: str | None = None
    usage_context: str | None = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class VideoIndex(BaseModel):
    source_file: Path
    total_duration: float
    analyzed_at: str
    clips: list[VideoClip] = Field(default_factory=list)
    raw_response: str | None = None
    footage_type: str = "generic"
    product_context: str | None = None

    def find_by_tags(self, tags: list[str], min_duration: float = 0.0) -> list[VideoClip]:
        matching = []
        for clip in self.clips:
            if clip.duration < min_duration:
                continue
            tag_match = any(t.lower() in [c.lower() for c in clip.tags] for t in tags)
            desc_match = any(t.lower() in clip.description.lower() for t in tags)
            if tag_match or desc_match:
                matching.append(clip)
        return matching


class MediaFile(BaseModel):
    file_path: Path
    file_type: str
    duration: float | None = None
    width: int | None = None
    height: int | None = None
