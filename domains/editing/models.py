from pathlib import Path

from pydantic import BaseModel, Field


class TimelineAsset(BaseModel):
    asset_type: str
    file_path: Path
    start_time: float = 0.0
    duration: float
    layer: int = 0


class LottieOverlayAsset(BaseModel):
    file_path: Path
    start_time: float = 0.0
    position: str = "center"
    scale: float = 0.5


class SFXAsset(BaseModel):
    file_path: Path
    volume: float = 0.5
    start_time: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0


class ComposedScene(BaseModel):
    scene_id: str
    video_path: Path | None = None
    audio_path: Path | None = None
    text_overlay_path: Path | None = None
    lottie_overlays: list[LottieOverlayAsset] = Field(default_factory=list)
    sfx_assets: list[SFXAsset] = Field(default_factory=list)
    duration: float
    effects: dict = Field(default_factory=dict)
    clip_start_time: float | None = None
    clip_end_time: float | None = None


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
