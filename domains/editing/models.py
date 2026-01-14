from pathlib import Path

from pydantic import BaseModel, Field


class TimelineAsset(BaseModel):
    asset_type: str
    file_path: Path
    start_time: float = 0.0
    duration: float
    layer: int = 0


class ComposedScene(BaseModel):
    scene_id: str
    video_path: Path | None = None
    audio_path: Path | None = None
    text_overlay_path: Path | None = None
    duration: float
    effects: dict = Field(default_factory=dict)


class Timeline(BaseModel):
    project_id: str
    width: int = 720
    height: int = 1280
    fps: float = 30.0
    scenes: list[ComposedScene] = Field(default_factory=list)

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)

    def add_scene(self, scene: ComposedScene) -> None:
        self.scenes.append(scene)
