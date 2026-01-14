from pathlib import Path

from pydantic import BaseModel


class AudioAsset(BaseModel):
    file_path: Path
    duration: float
    sample_rate: int = 24000
    text: str = ""


class ImageAsset(BaseModel):
    file_path: Path
    width: int
    height: int
    prompt: str = ""


class VideoAsset(BaseModel):
    file_path: Path
    duration: float
    width: int
    height: int
    fps: float = 30.0
    prompt: str = ""


class GeneratedAsset(BaseModel):
    asset_type: str
    file_path: Path
    metadata: dict = {}
