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


class TextStyle(str, Enum):
    BOLD_IMPACT_WHITE = "bold_impact_white"
    BOLD_IMPACT_RED = "bold_impact_red"
    SUBTITLE_CLEAN = "subtitle_clean"


class SyncMode(str, Enum):
    AUDIO = "audio"
    VISUAL = "visual"
    BEAT = "beat"


class VideoFitMode(str, Enum):
    LOOP = "loop"
    FREEZE = "freeze"
    SPEED = "speed"


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
    clip_offset: float | None = None
    gen_duration: int | None = Field(
        default=None, description="Video generation duration (4, 6, or 8 seconds)"
    )


class TextOverlay(BaseModel):
    content: str
    style: TextStyle = TextStyle.BOLD_IMPACT_WHITE
    animation: TextAnimation = TextAnimation.FADE_IN
    position: Literal["top", "center", "bottom"] = "bottom"
    font_color: str | None = None
    background_color: str | None = None


class LottieOverlay(BaseModel):
    lottie_name: str
    start_time: float = 0.0
    position: Literal[
        "top", "center", "bottom", "top-left", "top-right", "bottom-left", "bottom-right"
    ] = "center"
    scale: float = Field(default=0.5, ge=0.1, le=1.0)


class SoundEffect(BaseModel):
    preset_name: str
    volume: float = Field(default=0.5, ge=0.0, le=1.0)
    start_time: float = Field(default=0.0, ge=0.0)
    fade_in: float = Field(default=0.0, ge=0.0)
    fade_out: float = Field(default=0.0, ge=0.0)


class PreparedAssets(BaseModel):
    """Stores paths to already-generated assets for a scene.

    When present, the composer will reuse these assets instead of regenerating.
    Set individual fields to None to force regeneration of that specific asset.
    """

    audio_path: str | None = None
    audio_duration: float | None = None
    visual_path: str | None = None
    visual_clip_start: float | None = None
    visual_clip_end: float | None = None
    text_overlay_path: str | None = None


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
    lottie_overlays: list[LottieOverlay] = Field(default_factory=list)
    sound_effects: list[SoundEffect] = Field(default_factory=list)
    fx_beat: FxBeat = Field(default_factory=FxBeat)
    duration: float | None = None
    sync_mode: SyncMode = SyncMode.AUDIO
    video_fit_mode: VideoFitMode = VideoFitMode.FREEZE
    selected_clip_id: str | None = None
    prepared: PreparedAssets | None = None


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
