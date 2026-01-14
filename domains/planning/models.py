from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class VisualType(str, Enum):
    EXISTING_FOOTAGE = "existing_footage"
    MOTION_GRAPHIC_GEN = "motion_graphic_gen"
    IMAGE_GEN = "image_gen"
    WEB_RENDER = "web_render"


class CameraMovement(str, Enum):
    NONE = "none"
    ZOOM_IN_SLOW = "zoom_in_slow"
    ZOOM_OUT_SLOW = "zoom_out_slow"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    SHAKE = "shake"


class Transition(str, Enum):
    CUT = "cut"
    FADE = "fade"
    WHIP_PAN_LEFT = "whip_pan_left"
    WHIP_PAN_RIGHT = "whip_pan_right"
    DISSOLVE = "dissolve"


class TextAnimation(str, Enum):
    NONE = "none"
    FADE_IN = "fade_in"
    FADE_IN_UP = "fade_in_up"
    SLIDE_IN_LEFT = "slide_in_left"
    SLIDE_IN_RIGHT = "slide_in_right"
    BOUNCE = "bounce"
    TYPEWRITER = "typewriter"


class SyncMode(str, Enum):
    AUDIO = "audio"
    VISUAL = "visual"
    BEAT = "beat"


class VideoType(str, Enum):
    UGC_CENTERED = "ugc_centered"
    AI_GENERATED = "ai_generated"
    MIXED = "mixed"


class AudioScript(BaseModel):
    text: str
    voice_preset_id: str = "chirp_v3_korean_female_confident"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class VisualLayer(BaseModel):
    type: VisualType
    query_tags: list[str] = Field(default_factory=list)
    prompt: str | None = None
    fallback_gen_prompt: str | None = None
    model: str = "google_imagen_3"


class TextOverlay(BaseModel):
    content: str
    style_template: str = "bold_impact_white"
    animation: TextAnimation = TextAnimation.FADE_IN
    position: Literal["top", "center", "bottom"] = "bottom"


class FxBeat(BaseModel):
    camera_movement: CameraMovement = CameraMovement.NONE
    transition_next: Transition = Transition.CUT
    effect: str | None = None
    beat_timing: list[float] = Field(default_factory=list)


class Scene(BaseModel):
    scene_id: str
    sequence_order: int
    audio_script: AudioScript
    visual_layer: VisualLayer
    text_overlay: TextOverlay | None = None
    fx_beat: FxBeat = Field(default_factory=FxBeat)
    duration: float | None = None
    sync_mode: SyncMode = SyncMode.AUDIO
    selected_clip_id: str | None = None


class ScenarioMeta(BaseModel):
    title: str
    tone_voice: str = "energetic_professional_female"
    aspect_ratio: Literal["9:16", "16:9", "1:1"] = "9:16"
    resolution: tuple[int, int] = (720, 1280)
    video_type: VideoType = VideoType.MIXED


class Scenario(BaseModel):
    project_id: str
    scenario_meta: ScenarioMeta
    scenes: list[Scene]
