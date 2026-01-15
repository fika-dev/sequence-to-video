import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class PathConfig(BaseModel):
    raw_footage: Path = Path("assets/raw_footage")
    library_index: Path = Path("assets/library_index")
    generated: Path = Path("assets/generated")
    review_output: Path = Path("assets/review_output")
    templates: Path = Path("templates")


class ApiConfig(BaseModel):
    google_api_key: str | None = None
    google_project_id: str | None = None
    google_location: str = "us-central1"
    gcs_bucket: str | None = None


class VideoConfig(BaseModel):
    width: int = 720
    height: int = 1280
    fps: float = 30.0
    aspect_ratio: str = "9:16"


class TTSConfig(BaseModel):
    max_speed: float = 1.25
    min_speed: float = 1.25


class TextOverlayConfig(BaseModel):
    max_font_size: int = 90


class FFmpegConfig(BaseModel):
    video_codec: str = "libx264"
    video_preset: str = "fast"
    video_crf: int = 23
    audio_codec: str = "aac"
    audio_bitrate: str = "128k"
    prores_profile: str = "4444"
    prores_pix_fmt: str = "yuva444p10le"
    zoom_scale_factor: int = 2
    chromakey_color: str = "0x00FF00"
    chromakey_similarity: float = 0.1
    chromakey_blend: float = 0.2


class GenerationConfig(BaseModel):
    locale: str = "ko-KR"
    context: str = ""
    tts: TTSConfig = Field(default_factory=TTSConfig)
    text_overlay: TextOverlayConfig = Field(default_factory=TextOverlayConfig)


class Config(BaseModel):
    paths: PathConfig = Field(default_factory=PathConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    ffmpeg: FFmpegConfig = Field(default_factory=FFmpegConfig)

    def ensure_directories(self) -> None:
        self.paths.raw_footage.mkdir(parents=True, exist_ok=True)
        self.paths.library_index.mkdir(parents=True, exist_ok=True)
        self.paths.generated.mkdir(parents=True, exist_ok=True)
        self.paths.review_output.mkdir(parents=True, exist_ok=True)
        self.paths.templates.mkdir(parents=True, exist_ok=True)

        (self.paths.generated / "audio").mkdir(parents=True, exist_ok=True)
        (self.paths.generated / "images").mkdir(parents=True, exist_ok=True)
        (self.paths.generated / "videos").mkdir(parents=True, exist_ok=True)
        (self.paths.generated / "text_overlays").mkdir(parents=True, exist_ok=True)


def load_config(env_file: str | None = None) -> Config:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    api_config = ApiConfig(
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_project_id=os.getenv("GOOGLE_PROJECT_ID"),
        gcs_bucket=os.getenv("GCS_BUCKET"),
    )

    generation_config = GenerationConfig(
        locale=os.getenv("GENERATION_LOCALE", "ko-KR"),
        context=os.getenv("GENERATION_CONTEXT", ""),
    )

    return Config(api=api_config, generation=generation_config)
