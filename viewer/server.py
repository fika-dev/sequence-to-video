import json
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from domains.planning.models import (
    CameraMovement,
    PreparedAssets,
    Scenario,
    SyncMode,
    TextAnimation,
    TextStyle,
    Transition,
    VideoFitMode,
    VisualType,
)
from domains.planning.parser import ScenarioParser
from infrastructure.config import Config, load_config

app = FastAPI(title="Sequence Viewer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_state: dict = {
    "sequence_path": None,
    "scenario": None,
    "config": None,
    "tasks": {},
    "dirty": False,
}


class RegenerateRequest(BaseModel):
    scene_id: str
    asset_type: Literal["audio", "visual", "text_overlay", "scene"]


class LottieOverlayRequest(BaseModel):
    lottie_name: str
    start_time: float = 0.0
    position: Literal[
        "top", "center", "bottom", "top-left", "top-right", "bottom-left", "bottom-right"
    ] = "center"
    scale: float = 0.5


class SoundEffectRequest(BaseModel):
    preset_name: str
    volume: float = 0.5
    start_time: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0


class SceneUpdateRequest(BaseModel):
    audio_script_text: str | None = None
    audio_script_speed: float | None = None
    visual_type: str | None = None
    visual_prompt: str | None = None
    visual_fallback_prompt: str | None = None
    visual_gen_duration: int | None = None
    # Text overlay fields - use "REMOVE" sentinel to delete overlay
    text_overlay_enabled: bool | None = None
    text_overlay_content: str | None = None
    text_overlay_style: str | None = None
    text_overlay_animation: str | None = None
    text_overlay_position: Literal["top", "center", "bottom"] | None = None
    text_overlay_font_color: str | None = None
    text_overlay_background_color: str | None = None
    # Lottie and SFX - replace entire arrays when provided
    lottie_overlays: list[LottieOverlayRequest] | None = None
    sound_effects: list[SoundEffectRequest] | None = None
    duration: float | None = None
    sync_mode: str | None = None
    video_fit_mode: str | None = None
    camera_movement: str | None = None
    transition_next: str | None = None


class LottieOverlayInfo(BaseModel):
    lottie_name: str
    start_time: float
    position: str
    scale: float


class SoundEffectInfo(BaseModel):
    preset_name: str
    volume: float
    start_time: float
    fade_in: float
    fade_out: float


class SceneAssetInfo(BaseModel):
    scene_id: str
    sequence_order: int
    audio_script_text: str
    audio_script_speed: float
    voice_preset_id: str
    visual_type: str
    visual_prompt: str | None
    visual_fallback_prompt: str | None
    visual_query_tags: list[str]
    visual_gen_duration: int | None
    text_overlay_content: str | None
    text_overlay_style: str | None
    text_overlay_animation: str | None
    text_overlay_position: str | None
    text_overlay_font_color: str | None
    text_overlay_background_color: str | None
    lottie_overlays: list[LottieOverlayInfo]
    sound_effects: list[SoundEffectInfo]
    duration: float | None
    sync_mode: str
    video_fit_mode: str
    camera_movement: str
    transition_next: str
    prepared: PreparedAssets | None
    rendered_scene_path: str | None


def get_scenario() -> Scenario:
    if _state["scenario"] is None:
        raise HTTPException(status_code=400, detail="No sequence loaded")
    return _state["scenario"]


def get_config() -> Config:
    if _state["config"] is None:
        _state["config"] = load_config()
    return _state["config"]


def get_rendered_scene_path(project_id: str, scene_id: str) -> Path | None:
    config = get_config()
    scene_path = config.paths.review_output / project_id / "scenes" / f"{scene_id}.mp4"
    return scene_path if scene_path.exists() else None


def _snap_to_veo_duration(duration: float) -> int:
    valid_durations = [4, 6, 8]
    return min(valid_durations, key=lambda x: abs(x - duration))


@app.get("/", response_class=HTMLResponse)
async def index():
    return get_viewer_html()


@app.post("/api/load")
async def load_sequence(sequence_path: str):
    path = Path(sequence_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {sequence_path}")

    parser = ScenarioParser()
    scenario = parser.parse_file(path)

    _state["sequence_path"] = path
    _state["scenario"] = scenario
    _state["dirty"] = False

    return {"project_id": scenario.project_id, "scene_count": len(scenario.scenes), "dirty": False}


@app.get("/api/scenario")
async def get_scenario_info():
    scenario = get_scenario()
    return {
        "project_id": scenario.project_id,
        "title": scenario.scenario_meta.title,
        "aspect_ratio": scenario.scenario_meta.aspect_ratio,
        "resolution": scenario.scenario_meta.resolution,
        "video_type": scenario.scenario_meta.video_type.value,
        "scene_count": len(scenario.scenes),
        "dirty": _state["dirty"],
    }


@app.post("/api/save")
async def save_to_file():
    if _state["scenario"] is None:
        raise HTTPException(status_code=400, detail="No sequence loaded")
    _save_to_file()
    return {"status": "saved", "path": str(_state["sequence_path"]), "dirty": False}


@app.get("/api/enums")
async def get_enum_options():
    from domains.studio.lottie_renderer import LottieRenderer
    from domains.studio.sfx_provider import SFXProvider

    return {
        "visual_types": [e.value for e in VisualType],
        "camera_movements": [e.value for e in CameraMovement],
        "transitions": [e.value for e in Transition],
        "sync_modes": [e.value for e in SyncMode],
        "video_fit_modes": [e.value for e in VideoFitMode],
        "text_animations": [e.value for e in TextAnimation],
        "text_styles": [e.value for e in TextStyle],
        "text_positions": ["top", "center", "bottom"],
        "lottie_presets": LottieRenderer.list_presets(),
        "lottie_positions": [
            "top",
            "center",
            "bottom",
            "top-left",
            "top-right",
            "bottom-left",
            "bottom-right",
        ],
        "sfx_presets": SFXProvider.list_presets(),
    }


@app.get("/api/lottie/{preset_name}")
async def get_lottie_asset(preset_name: str):
    from domains.studio.lottie_renderer import LottieRenderer

    renderer = LottieRenderer()
    try:
        path = renderer.get_overlay_path(preset_name)
        return {"preset_name": preset_name, "path": str(path)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Lottie preset not found: {preset_name}")


@app.get("/api/sfx/{preset_name}")
async def get_sfx_asset(preset_name: str):
    from domains.studio.sfx_provider import SFXProvider

    provider = SFXProvider()
    try:
        path = provider.get_sfx_path(preset_name)
        return {"preset_name": preset_name, "path": str(path)}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"SFX preset not found: {preset_name}")


def _build_scene_info(scene, rendered_path: Path | None) -> SceneAssetInfo:
    return SceneAssetInfo(
        scene_id=scene.scene_id,
        sequence_order=scene.sequence_order,
        audio_script_text=scene.audio_script.text,
        audio_script_speed=scene.audio_script.speed,
        voice_preset_id=scene.audio_script.voice_preset_id,
        visual_type=scene.visual_layer.type.value,
        visual_prompt=scene.visual_layer.prompt,
        visual_fallback_prompt=scene.visual_layer.fallback_gen_prompt,
        visual_query_tags=scene.visual_layer.query_tags,
        visual_gen_duration=scene.visual_layer.gen_duration,
        text_overlay_content=scene.text_overlay.content if scene.text_overlay else None,
        text_overlay_style=scene.text_overlay.style.value if scene.text_overlay else None,
        text_overlay_animation=scene.text_overlay.animation.value if scene.text_overlay else None,
        text_overlay_position=scene.text_overlay.position if scene.text_overlay else None,
        text_overlay_font_color=scene.text_overlay.font_color if scene.text_overlay else None,
        text_overlay_background_color=scene.text_overlay.background_color
        if scene.text_overlay
        else None,
        lottie_overlays=[
            LottieOverlayInfo(
                lottie_name=lo.lottie_name,
                start_time=lo.start_time,
                position=lo.position,
                scale=lo.scale,
            )
            for lo in scene.lottie_overlays
        ],
        sound_effects=[
            SoundEffectInfo(
                preset_name=sfx.preset_name,
                volume=sfx.volume,
                start_time=sfx.start_time,
                fade_in=sfx.fade_in,
                fade_out=sfx.fade_out,
            )
            for sfx in scene.sound_effects
        ],
        duration=scene.duration,
        sync_mode=scene.sync_mode.value,
        video_fit_mode=scene.video_fit_mode.value,
        camera_movement=scene.fx_beat.camera_movement.value,
        transition_next=scene.fx_beat.transition_next.value,
        prepared=scene.prepared,
        rendered_scene_path=str(rendered_path) if rendered_path else None,
    )


@app.get("/api/scenes")
async def list_scenes() -> list[SceneAssetInfo]:
    scenario = get_scenario()
    result = []
    for scene in scenario.scenes:
        rendered_path = get_rendered_scene_path(scenario.project_id, scene.scene_id)
        result.append(_build_scene_info(scene, rendered_path))
    return result


@app.get("/api/scenes/{scene_id}")
async def get_scene(scene_id: str) -> SceneAssetInfo:
    scenario = get_scenario()
    scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    rendered_path = get_rendered_scene_path(scenario.project_id, scene.scene_id)
    return _build_scene_info(scene, rendered_path)


@app.patch("/api/scenes/{scene_id}")
async def update_scene(scene_id: str, request: SceneUpdateRequest):
    from domains.planning.models import LottieOverlay, SoundEffect, TextOverlay

    scenario = get_scenario()
    scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene not found: {scene_id}")

    if request.audio_script_text is not None:
        scene.audio_script.text = request.audio_script_text
    if request.audio_script_speed is not None:
        scene.audio_script.speed = request.audio_script_speed
    if request.visual_type is not None:
        scene.visual_layer.type = VisualType(request.visual_type)
    if request.visual_prompt is not None:
        scene.visual_layer.prompt = request.visual_prompt
    if request.visual_fallback_prompt is not None:
        scene.visual_layer.fallback_gen_prompt = request.visual_fallback_prompt
    if request.visual_gen_duration is not None:
        scene.visual_layer.gen_duration = request.visual_gen_duration

    if request.text_overlay_enabled is not None:
        if request.text_overlay_enabled and scene.text_overlay is None:
            scene.text_overlay = TextOverlay(content="")
        elif not request.text_overlay_enabled:
            scene.text_overlay = None

    if scene.text_overlay:
        if request.text_overlay_content is not None:
            scene.text_overlay.content = request.text_overlay_content
        if request.text_overlay_style is not None:
            scene.text_overlay.style = TextStyle(request.text_overlay_style)
        if request.text_overlay_animation is not None:
            scene.text_overlay.animation = TextAnimation(request.text_overlay_animation)
        if request.text_overlay_position is not None:
            scene.text_overlay.position = request.text_overlay_position
        if request.text_overlay_font_color is not None:
            scene.text_overlay.font_color = (
                request.text_overlay_font_color if request.text_overlay_font_color else None
            )
        if request.text_overlay_background_color is not None:
            scene.text_overlay.background_color = (
                request.text_overlay_background_color
                if request.text_overlay_background_color
                else None
            )

    if request.lottie_overlays is not None:
        scene.lottie_overlays = [
            LottieOverlay(
                lottie_name=lo.lottie_name,
                start_time=lo.start_time,
                position=lo.position,
                scale=lo.scale,
            )
            for lo in request.lottie_overlays
        ]

    if request.sound_effects is not None:
        scene.sound_effects = [
            SoundEffect(
                preset_name=sfx.preset_name,
                volume=sfx.volume,
                start_time=sfx.start_time,
                fade_in=sfx.fade_in,
                fade_out=sfx.fade_out,
            )
            for sfx in request.sound_effects
        ]

    if request.duration is not None:
        scene.duration = request.duration
    if request.sync_mode is not None:
        scene.sync_mode = SyncMode(request.sync_mode)
    if request.video_fit_mode is not None:
        scene.video_fit_mode = VideoFitMode(request.video_fit_mode)
    if request.camera_movement is not None:
        scene.fx_beat.camera_movement = CameraMovement(request.camera_movement)
    if request.transition_next is not None:
        scene.fx_beat.transition_next = Transition(request.transition_next)

    _save_to_file()

    return {"status": "updated", "scene_id": scene_id, "dirty": False}


@app.get("/api/asset")
async def serve_asset(path: str):
    file_path = Path(path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Asset not found: {path}")

    media_type = None
    suffix = file_path.suffix.lower()
    if suffix in (".mp4", ".mov"):
        media_type = "video/mp4"
    elif suffix in (".wav", ".mp3"):
        media_type = "audio/wav" if suffix == ".wav" else "audio/mpeg"
    elif suffix in (".png", ".jpg", ".jpeg", ".webp"):
        media_type = f"image/{suffix[1:]}"

    return FileResponse(file_path, media_type=media_type)


@app.post("/api/scan-assets")
async def scan_and_populate_prepared():
    scenario = get_scenario()
    config = get_config()

    audio_dir = config.paths.generated / "audio"
    text_overlay_dir = config.paths.generated / "text_overlays"

    updated_count = 0
    for scene in scenario.scenes:
        if scene.prepared is None:
            scene.prepared = PreparedAssets()

        audio_file = audio_dir / f"{scene.scene_id}_audio_{scene.audio_script.speed:.2f}.wav"
        if audio_file.exists():
            import wave

            with wave.open(str(audio_file), "r") as wf:
                duration = wf.getnframes() / wf.getframerate()
            scene.prepared.audio_path = str(audio_file)
            scene.prepared.audio_duration = duration
            updated_count += 1

        text_overlay_pattern = list(text_overlay_dir.glob(f"*{scene.scene_id}*.mp4"))
        if not text_overlay_pattern:
            text_overlay_pattern = list(text_overlay_dir.glob(f"*{scene.scene_id}*.mov"))
        if text_overlay_pattern:
            scene.prepared.text_overlay_path = str(text_overlay_pattern[0])

    _state["dirty"] = True

    return {"status": "scanned", "updated_scenes": updated_count}


@app.post("/api/regenerate")
async def regenerate_asset(request: RegenerateRequest, background_tasks: BackgroundTasks):
    import uuid

    scenario = get_scenario()
    scene = next((s for s in scenario.scenes if s.scene_id == request.scene_id), None)
    if not scene:
        raise HTTPException(status_code=404, detail=f"Scene not found: {request.scene_id}")

    task_id = str(uuid.uuid4())[:8]
    _state["tasks"][task_id] = {"status": "running", "message": f"Starting {request.asset_type}..."}

    if request.asset_type == "scene":
        background_tasks.add_task(_regenerate_scene, request.scene_id, task_id)
        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Re-rendering scene {request.scene_id}",
        }

    if request.asset_type == "audio":
        background_tasks.add_task(_regenerate_audio, request.scene_id, task_id)
        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Regenerating audio for {request.scene_id}",
        }

    if request.asset_type == "visual":
        background_tasks.add_task(_regenerate_visual, request.scene_id, task_id)
        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Regenerating visual for {request.scene_id}",
        }

    if request.asset_type == "text_overlay":
        background_tasks.add_task(_regenerate_text_overlay, request.scene_id, task_id)
        return {
            "status": "started",
            "task_id": task_id,
            "message": f"Regenerating text overlay for {request.scene_id}",
        }

    return {"status": "error", "message": "Unknown asset type"}


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    task = _state["tasks"].get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, **task}


def _regenerate_audio(scene_id: str, task_id: str):
    from domains.studio.tts_generator import TTSGenerator

    try:
        config = get_config()
        scenario = get_scenario()
        scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
        if not scene:
            _state["tasks"][task_id] = {"status": "failed", "message": "Scene not found"}
            return

        tts = TTSGenerator(output_dir=config.paths.generated / "audio", cache=None)

        audio_asset = tts.generate(
            text=scene.audio_script.text,
            preset_id=scene.audio_script.voice_preset_id,
            speed=scene.audio_script.speed,
            output_filename=f"{scene.scene_id}_audio_{scene.audio_script.speed:.2f}.wav",
        )

        if scene.prepared is None:
            scene.prepared = PreparedAssets()
        scene.prepared.audio_path = str(audio_asset.file_path)
        scene.prepared.audio_duration = audio_asset.duration

        _state["dirty"] = True
        _state["tasks"][task_id] = {
            "status": "completed",
            "message": f"Audio: {audio_asset.file_path}",
        }
        print(f"[Viewer] Audio regenerated: {audio_asset.file_path}")
    except Exception as e:
        _state["tasks"][task_id] = {"status": "failed", "message": str(e)}
        print(f"[Viewer] Audio regeneration failed: {e}")


def _regenerate_visual(scene_id: str, task_id: str):
    from domains.studio.image_generator import ImageGenerator
    from domains.studio.video_generator import VideoGenerator
    from domains.planning.models import VisualType

    try:
        config = get_config()
        scenario = get_scenario()
        scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
        if not scene:
            _state["tasks"][task_id] = {"status": "failed", "message": "Scene not found"}
            return

        width, height = scenario.scenario_meta.resolution

        visual = scene.visual_layer
        prompt = visual.prompt or visual.fallback_gen_prompt or ""

        if visual.type == VisualType.MOTION_GRAPHIC_GEN:
            video_gen = VideoGenerator(
                output_dir=config.paths.generated / "videos",
                project=config.api.google_project_id,
                location="us-central1",
                gcs_bucket=config.api.gcs_bucket,
                cache=None,
            )
            duration = visual.gen_duration or _snap_to_veo_duration(scene.duration or 6)
            asset = video_gen.generate(prompt=prompt, width=width, height=height, duration=duration)
            visual_path = asset.file_path
        else:
            image_gen = ImageGenerator(
                output_dir=config.paths.generated / "images",
                project=config.api.google_project_id,
                location="global",
                cache=None,
                locale=config.generation.locale,
                context=config.generation.context,
            )
            asset = image_gen.generate(prompt=prompt, width=width, height=height)
            visual_path = asset.file_path

        if scene.prepared is None:
            scene.prepared = PreparedAssets()
        scene.prepared.visual_path = str(visual_path)
        scene.prepared.visual_clip_start = None
        scene.prepared.visual_clip_end = None

        _state["dirty"] = True
        _state["tasks"][task_id] = {"status": "completed", "message": f"Visual: {visual_path}"}
        print(f"[Viewer] Visual regenerated: {visual_path}")
    except Exception as e:
        _state["tasks"][task_id] = {"status": "failed", "message": str(e)}
        print(f"[Viewer] Visual regeneration failed: {e}")


def _regenerate_text_overlay(scene_id: str, task_id: str):
    from domains.studio.text_renderer import TextAnimationRenderer

    try:
        config = get_config()
        scenario = get_scenario()
        scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
        if not scene or not scene.text_overlay:
            _state["tasks"][task_id] = {
                "status": "failed",
                "message": "Scene or text overlay not found",
            }
            return

        text_renderer = TextAnimationRenderer(
            output_dir=config.paths.generated / "text_overlays",
            cache=None,
            max_font_size=config.generation.text_overlay.max_font_size,
        )

        width, height = scenario.scenario_meta.resolution
        duration = scene.prepared.audio_duration if scene.prepared else 3.0

        text_asset = text_renderer.render_overlay(
            text=scene.text_overlay.content,
            style_template=scene.text_overlay.style.value,
            animation=scene.text_overlay.animation.value,
            position=scene.text_overlay.position,
            duration=duration or 3.0,
            width=width,
            height=height,
            font_color=scene.text_overlay.font_color,
            background_color=scene.text_overlay.background_color,
        )

        if scene.prepared is None:
            scene.prepared = PreparedAssets()
        scene.prepared.text_overlay_path = str(text_asset.file_path)

        _state["dirty"] = True
        _state["tasks"][task_id] = {
            "status": "completed",
            "message": f"Text overlay: {text_asset.file_path}",
        }
        print(f"[Viewer] Text overlay regenerated: {text_asset.file_path}")
    except Exception as e:
        _state["tasks"][task_id] = {"status": "failed", "message": str(e)}
        print(f"[Viewer] Text overlay regeneration failed: {e}")


def _regenerate_scene(scene_id: str, task_id: str):
    from domains.editing.composer import SequenceComposer
    from domains.editing.renderer import FFmpegRenderer
    from domains.library.analyzer import VideoContentAnalyzer
    from domains.library.repository import AssetRepository
    from domains.library.selector import FootageSelector
    from domains.studio.image_generator import ImageGenerator
    from domains.studio.text_renderer import TextAnimationRenderer
    from domains.studio.tts_generator import TTSGenerator
    from domains.studio.video_generator import VideoGenerator
    from infrastructure.cache import AssetCache

    try:
        config = get_config()
        scenario = get_scenario()

        cache = AssetCache(cache_dir=config.paths.generated / ".cache")

        tts = TTSGenerator(output_dir=config.paths.generated / "audio", cache=cache)
        image_gen = ImageGenerator(
            output_dir=config.paths.generated / "images",
            project=config.api.google_project_id,
            location="global",
            cache=cache,
            locale=config.generation.locale,
            context=config.generation.context,
        )
        video_gen = VideoGenerator(
            output_dir=config.paths.generated / "videos",
            project=config.api.google_project_id,
            location="us-central1",
            gcs_bucket=config.api.gcs_bucket,
            cache=cache,
        )
        text_renderer = TextAnimationRenderer(
            output_dir=config.paths.generated / "text_overlays",
            cache=cache,
            max_font_size=config.generation.text_overlay.max_font_size,
        )

        analyzer = VideoContentAnalyzer(
            project=config.api.google_project_id,
            location=config.api.google_location,
            gcs_bucket=config.api.gcs_bucket,
        )
        asset_repo = AssetRepository(
            raw_footage_dir=config.paths.raw_footage,
            index_dir=config.paths.library_index,
            analyzer=analyzer,
            project=config.api.google_project_id,
        )

        footage_selector = FootageSelector(
            project=config.api.google_project_id,
            location="global",
        )

        renderer = FFmpegRenderer(output_dir=config.paths.review_output)

        composer = SequenceComposer(
            tts_generator=tts,
            image_generator=image_gen,
            video_generator=video_gen,
            text_renderer=text_renderer,
            asset_repository=asset_repo,
            footage_selector=footage_selector,
            renderer=renderer,
            verbose=True,
            max_tts_speed=config.generation.tts.max_speed,
            min_tts_speed=config.generation.tts.min_speed,
        )

        output_path, new_clip_id = composer.recompose_scene(scenario, scene_id)

        _state["dirty"] = True
        _state["tasks"][task_id] = {"status": "completed", "message": f"Scene {scene_id} rendered"}
        print(f"[Viewer] Scene {scene_id} re-rendered: {output_path}")
    except Exception as e:
        _state["tasks"][task_id] = {"status": "failed", "message": str(e)}
        print(f"[Viewer] Scene render failed: {e}")


def _save_to_file():
    if _state["sequence_path"] is None or _state["scenario"] is None:
        return

    scenario = _state["scenario"]
    path = _state["sequence_path"]

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for scene in scenario.scenes:
        for orig_scene in data.get("scenes", []):
            if orig_scene.get("scene_id") == scene.scene_id:
                orig_scene["audio_script"]["text"] = scene.audio_script.text
                orig_scene["audio_script"]["speed"] = scene.audio_script.speed
                orig_scene["audio_script"]["voice_preset_id"] = scene.audio_script.voice_preset_id
                orig_scene["visual_layer"]["type"] = scene.visual_layer.type.value
                orig_scene["visual_layer"]["prompt"] = scene.visual_layer.prompt
                orig_scene["visual_layer"]["fallback_gen_prompt"] = (
                    scene.visual_layer.fallback_gen_prompt
                )
                orig_scene["visual_layer"]["query_tags"] = scene.visual_layer.query_tags
                if scene.visual_layer.gen_duration:
                    orig_scene["visual_layer"]["gen_duration"] = scene.visual_layer.gen_duration
                if scene.text_overlay:
                    if "text_overlay" not in orig_scene:
                        orig_scene["text_overlay"] = {}
                    orig_scene["text_overlay"]["content"] = scene.text_overlay.content
                    orig_scene["text_overlay"]["style"] = scene.text_overlay.style.value
                    orig_scene["text_overlay"]["animation"] = scene.text_overlay.animation.value
                    orig_scene["text_overlay"]["position"] = scene.text_overlay.position
                    orig_scene["text_overlay"]["font_color"] = scene.text_overlay.font_color
                    orig_scene["text_overlay"]["background_color"] = (
                        scene.text_overlay.background_color
                    )
                else:
                    orig_scene.pop("text_overlay", None)

                orig_scene["lottie_overlays"] = [
                    {
                        "lottie_name": lo.lottie_name,
                        "start_time": lo.start_time,
                        "position": lo.position,
                        "scale": lo.scale,
                    }
                    for lo in scene.lottie_overlays
                ]

                orig_scene["sound_effects"] = [
                    {
                        "preset_name": sfx.preset_name,
                        "volume": sfx.volume,
                        "start_time": sfx.start_time,
                        "fade_in": sfx.fade_in,
                        "fade_out": sfx.fade_out,
                    }
                    for sfx in scene.sound_effects
                ]

                orig_scene["duration"] = scene.duration
                orig_scene["sync_mode"] = scene.sync_mode.value
                orig_scene["video_fit_mode"] = scene.video_fit_mode.value
                if "fx_beat" not in orig_scene:
                    orig_scene["fx_beat"] = {}
                orig_scene["fx_beat"]["camera_movement"] = scene.fx_beat.camera_movement.value
                orig_scene["fx_beat"]["transition_next"] = scene.fx_beat.transition_next.value
                if scene.selected_clip_id:
                    orig_scene["selected_clip_id"] = scene.selected_clip_id
                if scene.prepared:
                    orig_scene["prepared"] = scene.prepared.model_dump(exclude_none=True)
                break

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _state["dirty"] = False


def get_viewer_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sequence Viewer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e; color: #eee; height: 100vh; overflow: hidden;
        }
        .container { display: flex; height: 100vh; }

        .panel {
            display: flex; flex-direction: column; overflow: hidden;
            border-right: 1px solid #0f3460;
        }
        .panel:last-child { border-right: none; }
        .panel-header {
            padding: 12px 16px; background: #16213e; border-bottom: 1px solid #0f3460;
            display: flex; align-items: center; gap: 8px; min-height: 52px;
        }
        .panel-header h3 { font-size: 13px; font-weight: 600; color: #e94560; }
        .panel-content { flex: 1; overflow-y: auto; padding: 12px; }

        /* Left Panel - Scene List */
        .panel-left { width: 280px; background: #16213e; }
        .load-row { display: flex; gap: 8px; margin-bottom: 12px; }
        .load-input {
            flex: 1; padding: 8px 10px; border: 1px solid #0f3460; border-radius: 6px;
            background: #1a1a2e; color: #eee; font-size: 11px;
        }
        .load-btn {
            padding: 8px 12px; background: #e94560; border: none; border-radius: 6px;
            color: white; cursor: pointer; font-size: 11px; font-weight: 500;
        }
        .load-btn:hover { background: #ff6b6b; }

        .scene-item {
            padding: 10px; margin-bottom: 6px; background: #1a1a2e; border-radius: 6px;
            cursor: pointer; border: 2px solid transparent; transition: all 0.15s;
        }
        .scene-item:hover { border-color: #0f3460; }
        .scene-item.active { border-color: #e94560; background: #1f2b47; }
        .scene-id { font-weight: 600; color: #e94560; font-size: 12px; }
        .scene-text {
            font-size: 11px; color: #888; margin-top: 4px;
            display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .scene-badges { display: flex; gap: 4px; margin-top: 6px; flex-wrap: wrap; }
        .badge { font-size: 9px; padding: 2px 6px; border-radius: 8px; background: #0f3460; color: #4da8da; }
        .badge.ready { background: #1b4332; color: #52b788; }
        .badge.missing { background: #3d0000; color: #ff6b6b; }

        /* Center Panel - Scene Editor */
        .panel-center { flex: 1; background: #1a1a2e; min-width: 400px; }
        .editor-section { background: #16213e; border-radius: 8px; padding: 14px; margin-bottom: 12px; }
        .editor-section h4 { font-size: 12px; color: #4da8da; margin-bottom: 10px; font-weight: 600; }
        .form-row { margin-bottom: 10px; }
        .form-label { font-size: 11px; color: #888; margin-bottom: 4px; display: block; }
        .form-input, .form-textarea, .form-select {
            width: 100%; padding: 8px 10px; border: 1px solid #0f3460; border-radius: 6px;
            background: #1a1a2e; color: #eee; font-size: 12px;
        }
        .form-textarea { min-height: 60px; resize: vertical; font-family: inherit; }
        .form-row-inline { display: flex; gap: 12px; }
        .form-row-inline .form-row { flex: 1; margin-bottom: 0; }
        .save-btn {
            padding: 10px 24px; background: #4da8da; border: none; border-radius: 6px;
            color: white; cursor: pointer; font-size: 12px; font-weight: 600;
        }
        .save-btn:hover { background: #5bc0eb; }
        .tag { display: inline-block; font-size: 10px; padding: 3px 8px; background: #0f3460;
               color: #4da8da; border-radius: 10px; margin: 2px 4px 2px 0; }
        .meta-info { font-size: 11px; color: #666; }

        /* Toggle Switch */
        .toggle-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
        .toggle-label { font-size: 11px; color: #888; }
        .toggle { position: relative; width: 40px; height: 20px; background: #0f3460; border-radius: 10px; cursor: pointer; }
        .toggle.on { background: #4da8da; }
        .toggle::after { content: ''; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; background: #eee; border-radius: 50%; transition: 0.2s; }
        .toggle.on::after { left: 22px; }

        /* Color Input */
        .color-row { display: flex; align-items: center; gap: 8px; }
        .color-input { width: 36px; height: 28px; border: none; border-radius: 4px; cursor: pointer; background: transparent; padding: 0; }
        .color-text { flex: 1; }

        /* Section Header with Actions */
        .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .section-header h4 { margin-bottom: 0; }
        .section-actions { display: flex; gap: 6px; }
        .btn-small { padding: 4px 8px; font-size: 10px; background: #0f3460; border: none; border-radius: 4px; color: #4da8da; cursor: pointer; }
        .btn-small:hover { background: #1a4a7a; }
        .btn-small.danger { color: #ff6b6b; }
        .btn-small.danger:hover { background: #3d0000; }

        /* Item List */
        .item-list { display: flex; flex-direction: column; gap: 8px; }
        .item-card { background: #1a1a2e; border-radius: 6px; padding: 10px; border: 1px solid #0f3460; }
        .item-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .item-card-title { font-size: 11px; font-weight: 600; color: #e94560; }
        .item-card-remove { background: none; border: none; color: #666; cursor: pointer; font-size: 14px; }
        .item-card-remove:hover { color: #ff6b6b; }
        .item-card-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .item-card-grid .form-row { margin-bottom: 0; }
        .empty-list { text-align: center; color: #444; font-size: 11px; padding: 16px; }

        /* Preview List (Right Panel) */
        .preview-list { display: flex; flex-direction: column; gap: 8px; }
        .preview-item { background: #0d1321; border-radius: 6px; padding: 8px; }
        .preview-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
        .preview-item-name { font-size: 11px; font-weight: 600; color: #4da8da; }
        .preview-item-meta { font-size: 9px; color: #555; }
        .preview-item-content { min-height: 32px; }
        .preview-play-btn { padding: 6px 12px; background: #0f3460; border: none; border-radius: 4px; color: #4da8da; cursor: pointer; font-size: 10px; }
        .preview-play-btn:hover { background: #1a4a7a; }

        /* Right Panel - Asset Preview */
        .panel-right { width: 380px; background: #16213e; }
        .asset-section { background: #1a1a2e; border-radius: 8px; padding: 12px; margin-bottom: 10px; }
        .asset-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .asset-title { font-size: 11px; font-weight: 600; color: #4da8da; }
        .asset-status { font-size: 10px; padding: 2px 8px; border-radius: 8px; }
        .asset-status.ready { background: #1b4332; color: #52b788; }
        .asset-status.missing { background: #3d0000; color: #ff6b6b; }
        .asset-preview { background: #0d1321; border-radius: 6px; padding: 8px; margin-bottom: 8px; overflow: hidden; }
        .asset-preview video, .asset-preview audio, .asset-preview img { max-width: 100%; border-radius: 4px; display: block; }
        .asset-preview audio { width: 100%; }
        .asset-path { font-size: 10px; color: #555; word-break: break-all; }
        .regen-btn {
            padding: 4px 10px; background: #0f3460; border: none; border-radius: 4px;
            color: #4da8da; cursor: pointer; font-size: 10px; margin-left: 6px;
        }
        .regen-btn:hover { background: #1a4a7a; }
        .render-scene-btn {
            width: 100%; padding: 12px; background: #e94560; border: none; border-radius: 6px;
            color: white; cursor: pointer; font-size: 12px; font-weight: 600; margin-top: 8px;
            position: relative; z-index: 10; display: block;
        }
        .render-scene-btn:hover { background: #ff6b6b; }
        .render-scene-btn:disabled { background: #444; cursor: not-allowed; }

        .empty-state {
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; height: 100%; color: #444; text-align: center;
        }
        .empty-state svg { width: 48px; height: 48px; margin-bottom: 12px; opacity: 0.5; }
        .empty-state p { font-size: 12px; }

        .toast {
            position: fixed; bottom: 20px; right: 20px; padding: 12px 24px;
            background: #1b4332; color: #52b788; border-radius: 8px;
            font-size: 12px; opacity: 0; transition: opacity 0.3s; z-index: 1000;
        }
        .toast.show { opacity: 1; }
        .toast.error { background: #3d0000; color: #ff6b6b; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Panel: Scene List -->
        <div class="panel panel-left">
            <div class="panel-header"><h3>Scenes</h3></div>
            <div class="panel-content">
                <div class="load-row">
                    <input type="text" class="load-input" id="sequencePath" placeholder="sequence.json">
                    <button class="load-btn" onclick="loadSequence()">Load</button>
                </div>
                <div class="load-row">
                    <button class="load-btn" style="flex:1;background:#4da8da;" onclick="scanAssets()">Scan Assets</button>
                    <button class="load-btn" style="flex:1;background:#52b788;" onclick="saveToFile()">Save File <span id="dirtyIndicator" style="display:none;color:#ff6b6b;">*</span></button>
                </div>
                <div id="sceneList">
                    <div class="empty-state">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/>
                        </svg>
                        <p>Load a sequence</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Center Panel: Scene Editor -->
        <div class="panel panel-center">
            <div class="panel-header"><h3 id="editorTitle">Scene Editor</h3></div>
            <div class="panel-content" id="editorContent">
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                    </svg>
                    <p>Select a scene to edit</p>
                </div>
            </div>
        </div>

        <!-- Right Panel: Asset Preview -->
        <div class="panel panel-right">
            <div class="panel-header"><h3>Prepared Assets</h3></div>
            <div class="panel-content" id="assetContent">
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                    </svg>
                    <p>Select a scene to preview</p>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        let currentSceneId = null;
        let scenes = [];
        let currentScene = null;
        let isDirty = false;
        let enumOpts = { visual_types: [], camera_movements: [], transitions: [], sync_modes: [], video_fit_modes: [], text_animations: [], text_styles: [], text_positions: [], lottie_presets: [], lottie_positions: [], sfx_presets: [] };

        async function loadSequence() {
            const path = document.getElementById('sequencePath').value.trim();
            if (!path) return;
            try {
                const res = await fetch('/api/load', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                    body: `sequence_path=${encodeURIComponent(path)}`
                });
                if (!res.ok) throw new Error((await res.json()).detail);
                const data = await res.json();
                isDirty = data.dirty || false;
                updateDirtyIndicator();
                await refreshScenes();
                showToast('Sequence loaded');
            } catch (e) { showToast(e.message, true); }
        }

        async function saveToFile() {
            try {
                const res = await fetch('/api/save', { method: 'POST' });
                if (!res.ok) throw new Error((await res.json()).detail);
                const data = await res.json();
                isDirty = false;
                updateDirtyIndicator();
                showToast('Saved to file');
            } catch (e) { showToast(e.message, true); }
        }

        function updateDirtyIndicator() {
            const indicator = document.getElementById('dirtyIndicator');
            if (indicator) {
                indicator.style.display = isDirty ? 'inline' : 'none';
            }
        }

        async function scanAssets() {
            try {
                const res = await fetch('/api/scan-assets', { method: 'POST' });
                if (!res.ok) throw new Error((await res.json()).detail);
                const data = await res.json();
                showToast(`Scanned: ${data.updated_scenes} scenes updated`);
                await refreshScenes();
            } catch (e) { showToast(e.message, true); }
        }

        async function refreshScenes() {
            try {
                const res = await fetch('/api/scenes');
                scenes = await res.json();
                renderSceneList();
                if (currentSceneId) await selectScene(currentSceneId);
            } catch (e) { showToast('Failed to load scenes', true); }
        }

        function renderSceneList() {
            const list = document.getElementById('sceneList');
            if (!scenes.length) {
                list.innerHTML = '<div class="empty-state"><p>No scenes</p></div>';
                return;
            }
            list.innerHTML = scenes.map(s => {
                const hasAudio = s.prepared?.audio_path;
                const hasVisual = s.prepared?.visual_path;
                const hasRendered = s.rendered_scene_path;
                return `
                    <div class="scene-item ${s.scene_id === currentSceneId ? 'active' : ''}"
                         onclick="selectScene('${s.scene_id}')">
                        <div class="scene-id">${s.scene_id}</div>
                        <div class="scene-text">${esc(s.audio_script_text)}</div>
                        <div class="scene-badges">
                            <span class="badge">${s.visual_type}</span>
                            ${hasAudio ? '<span class="badge ready">audio</span>' : ''}
                            ${hasVisual ? '<span class="badge ready">visual</span>' : ''}
                            ${hasRendered ? '<span class="badge ready">rendered</span>' : ''}
                        </div>
                    </div>`;
            }).join('');
        }

        async function selectScene(sceneId) {
            currentSceneId = sceneId;
            currentScene = scenes.find(s => s.scene_id === sceneId);
            renderSceneList();
            if (!currentScene) return;
            document.getElementById('editorTitle').textContent = `Scene: ${sceneId}`;
            renderEditor(currentScene);
            renderAssets(currentScene);
        }

        function renderEditor(s) {
            const c = document.getElementById('editorContent');
            const hasTextOverlay = s.text_overlay_content !== null;
            c.innerHTML = `
                <div class="editor-section">
                    <h4>Audio Script</h4>
                    <div class="form-row">
                        <label class="form-label">Narration Text</label>
                        <textarea class="form-textarea" id="editAudioText">${esc(s.audio_script_text)}</textarea>
                    </div>
                    <div class="form-row-inline">
                        <div class="form-row">
                            <label class="form-label">Speed</label>
                            <input type="number" class="form-input" id="editAudioSpeed" value="${s.audio_script_speed}" step="0.1" min="0.5" max="2.0">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Voice Preset</label>
                            <input type="text" class="form-input" id="editVoicePreset" value="${esc(s.voice_preset_id)}" readonly>
                        </div>
                    </div>
                </div>

                <div class="editor-section">
                    <h4>Visual Layer</h4>
                    <div class="form-row">
                        <label class="form-label">Type</label>
                        <select class="form-select" id="editVisualType">
                            ${enumOpts.visual_types.map(v => `<option value="${v}" ${v === s.visual_type ? 'selected' : ''}>${v}</option>`).join('')}
                        </select>
                    </div>
                    <div class="form-row">
                        <label class="form-label">Prompt</label>
                        <textarea class="form-textarea" id="editVisualPrompt">${esc(s.visual_prompt || '')}</textarea>
                    </div>
                    <div class="form-row">
                        <label class="form-label">Fallback Prompt</label>
                        <textarea class="form-textarea" id="editFallbackPrompt">${esc(s.visual_fallback_prompt || '')}</textarea>
                    </div>
                    <div class="form-row-inline">
                        <div class="form-row">
                            <label class="form-label">Query Tags</label>
                            <div>${s.visual_query_tags.map(t => `<span class="tag">${esc(t)}</span>`).join('') || '<span class="meta-info">No tags</span>'}</div>
                        </div>
                        <div class="form-row">
                            <label class="form-label">Gen Duration (4/6/8s)</label>
                            <select class="form-select" id="editGenDuration">
                                <option value="" ${!s.visual_gen_duration ? 'selected' : ''}>Auto</option>
                                <option value="4" ${s.visual_gen_duration === 4 ? 'selected' : ''}>4s</option>
                                <option value="6" ${s.visual_gen_duration === 6 ? 'selected' : ''}>6s</option>
                                <option value="8" ${s.visual_gen_duration === 8 ? 'selected' : ''}>8s</option>
                            </select>
                        </div>
                    </div>
                </div>

                <div class="editor-section">
                    <div class="section-header">
                        <h4>Text Overlay</h4>
                        <div class="toggle-row">
                            <span class="toggle-label">Enabled</span>
                            <div class="toggle ${hasTextOverlay ? 'on' : ''}" id="textOverlayToggle" onclick="toggleTextOverlay()"></div>
                        </div>
                    </div>
                    <div id="textOverlayFields" style="${hasTextOverlay ? '' : 'display:none;'}">
                        <div class="form-row">
                            <label class="form-label">Content</label>
                            <input type="text" class="form-input" id="editTextOverlay" value="${esc(s.text_overlay_content || '')}">
                        </div>
                        <div class="form-row-inline">
                            <div class="form-row">
                                <label class="form-label">Style</label>
                                <select class="form-select" id="editTextStyle">
                                    ${enumOpts.text_styles.map(v => `<option value="${v}" ${v === s.text_overlay_style ? 'selected' : ''}>${v}</option>`).join('')}
                                </select>
                            </div>
                            <div class="form-row">
                                <label class="form-label">Animation</label>
                                <select class="form-select" id="editTextAnimation">
                                    ${enumOpts.text_animations.map(v => `<option value="${v}" ${v === s.text_overlay_animation ? 'selected' : ''}>${v}</option>`).join('')}
                                </select>
                            </div>
                        </div>
                        <div class="form-row-inline">
                            <div class="form-row">
                                <label class="form-label">Position</label>
                                <select class="form-select" id="editTextPosition">
                                    ${enumOpts.text_positions.map(v => `<option value="${v}" ${v === s.text_overlay_position ? 'selected' : ''}>${v}</option>`).join('')}
                                </select>
                            </div>
                        </div>
                        <div class="form-row-inline">
                            <div class="form-row">
                                <label class="form-label">Font Color</label>
                                <div class="color-row">
                                    <input type="color" class="color-input" id="editFontColor" value="${s.text_overlay_font_color || '#ffffff'}">
                                    <input type="text" class="form-input color-text" id="editFontColorText" value="${s.text_overlay_font_color || ''}" placeholder="Default">
                                </div>
                            </div>
                            <div class="form-row">
                                <label class="form-label">Background Color</label>
                                <div class="color-row">
                                    <input type="color" class="color-input" id="editBgColor" value="${s.text_overlay_background_color || '#000000'}">
                                    <input type="text" class="form-input color-text" id="editBgColorText" value="${s.text_overlay_background_color || ''}" placeholder="Default">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="editor-section">
                    <div class="section-header">
                        <h4>Lottie Overlays</h4>
                        <button class="btn-small" onclick="addLottie()">+ Add</button>
                    </div>
                    <div class="item-list" id="lottieList">
                        ${s.lottie_overlays.length ? s.lottie_overlays.map((lo, i) => renderLottieItem(lo, i)).join('') : '<div class="empty-list">No Lottie overlays</div>'}
                    </div>
                </div>

                <div class="editor-section">
                    <div class="section-header">
                        <h4>Sound Effects</h4>
                        <button class="btn-small" onclick="addSfx()">+ Add</button>
                    </div>
                    <div class="item-list" id="sfxList">
                        ${s.sound_effects.length ? s.sound_effects.map((sfx, i) => renderSfxItem(sfx, i)).join('') : '<div class="empty-list">No sound effects</div>'}
                    </div>
                </div>

                <div class="editor-section">
                    <h4>Timing & Effects</h4>
                    <div class="form-row-inline">
                        <div class="form-row">
                            <label class="form-label">Duration (sec)</label>
                            <input type="number" class="form-input" id="editDuration" value="${s.duration || ''}" step="0.1" placeholder="Auto">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Sync Mode</label>
                            <select class="form-select" id="editSyncMode">
                                ${enumOpts.sync_modes.map(v => `<option value="${v}" ${v === s.sync_mode ? 'selected' : ''}>${v}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="form-row-inline">
                        <div class="form-row">
                            <label class="form-label">Video Fit Mode</label>
                            <select class="form-select" id="editVideoFitMode">
                                ${enumOpts.video_fit_modes.map(v => `<option value="${v}" ${v === s.video_fit_mode ? 'selected' : ''}>${v}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                    <div class="form-row-inline">
                        <div class="form-row">
                            <label class="form-label">Camera Movement</label>
                            <select class="form-select" id="editCamera">
                                ${enumOpts.camera_movements.map(v => `<option value="${v}" ${v === s.camera_movement ? 'selected' : ''}>${v}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-row">
                            <label class="form-label">Transition</label>
                            <select class="form-select" id="editTransition">
                                ${enumOpts.transitions.map(v => `<option value="${v}" ${v === s.transition_next ? 'selected' : ''}>${v}</option>`).join('')}
                            </select>
                        </div>
                    </div>
                </div>

                <button class="save-btn" onclick="saveScene()">Save Changes</button>
            `;
            setupColorSync();
        }

        function renderLottieItem(lo, index) {
            return `
                <div class="item-card" data-lottie-index="${index}">
                    <div class="item-card-header">
                        <span class="item-card-title">${lo.lottie_name}</span>
                        <button class="item-card-remove" onclick="removeLottie(${index})">x</button>
                    </div>
                    <div class="item-card-grid">
                        <div class="form-row">
                            <label class="form-label">Preset</label>
                            <select class="form-select lottie-field" data-index="${index}" data-field="lottie_name">
                                ${enumOpts.lottie_presets.map(p => `<option value="${p}" ${p === lo.lottie_name ? 'selected' : ''}>${p}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-row">
                            <label class="form-label">Position</label>
                            <select class="form-select lottie-field" data-index="${index}" data-field="position">
                                ${enumOpts.lottie_positions.map(p => `<option value="${p}" ${p === lo.position ? 'selected' : ''}>${p}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-row">
                            <label class="form-label">Start Time</label>
                            <input type="number" class="form-input lottie-field" data-index="${index}" data-field="start_time" value="${lo.start_time}" step="0.1" min="0">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Scale</label>
                            <input type="number" class="form-input lottie-field" data-index="${index}" data-field="scale" value="${lo.scale}" step="0.1" min="0.1" max="1">
                        </div>
                    </div>
                </div>`;
        }

        function renderSfxItem(sfx, index) {
            return `
                <div class="item-card" data-sfx-index="${index}">
                    <div class="item-card-header">
                        <span class="item-card-title">${sfx.preset_name}</span>
                        <button class="item-card-remove" onclick="removeSfx(${index})">x</button>
                    </div>
                    <div class="item-card-grid">
                        <div class="form-row">
                            <label class="form-label">Preset</label>
                            <select class="form-select sfx-field" data-index="${index}" data-field="preset_name">
                                ${enumOpts.sfx_presets.map(p => `<option value="${p}" ${p === sfx.preset_name ? 'selected' : ''}>${p}</option>`).join('')}
                            </select>
                        </div>
                        <div class="form-row">
                            <label class="form-label">Volume</label>
                            <input type="number" class="form-input sfx-field" data-index="${index}" data-field="volume" value="${sfx.volume}" step="0.1" min="0" max="1">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Start Time</label>
                            <input type="number" class="form-input sfx-field" data-index="${index}" data-field="start_time" value="${sfx.start_time}" step="0.1" min="0">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Fade In</label>
                            <input type="number" class="form-input sfx-field" data-index="${index}" data-field="fade_in" value="${sfx.fade_in}" step="0.1" min="0">
                        </div>
                        <div class="form-row">
                            <label class="form-label">Fade Out</label>
                            <input type="number" class="form-input sfx-field" data-index="${index}" data-field="fade_out" value="${sfx.fade_out}" step="0.1" min="0">
                        </div>
                    </div>
                </div>`;
        }

        function setupColorSync() {
            const fontColor = document.getElementById('editFontColor');
            const fontColorText = document.getElementById('editFontColorText');
            const bgColor = document.getElementById('editBgColor');
            const bgColorText = document.getElementById('editBgColorText');
            if (fontColor && fontColorText) {
                fontColor.addEventListener('input', () => { fontColorText.value = fontColor.value; });
                fontColorText.addEventListener('input', () => { if (fontColorText.value) fontColor.value = fontColorText.value; });
            }
            if (bgColor && bgColorText) {
                bgColor.addEventListener('input', () => { bgColorText.value = bgColor.value; });
                bgColorText.addEventListener('input', () => { if (bgColorText.value) bgColor.value = bgColorText.value; });
            }
        }

        let textOverlayEnabled = null;
        function toggleTextOverlay() {
            const toggle = document.getElementById('textOverlayToggle');
            const fields = document.getElementById('textOverlayFields');
            const isOn = toggle.classList.contains('on');
            if (isOn) {
                toggle.classList.remove('on');
                fields.style.display = 'none';
                textOverlayEnabled = false;
            } else {
                toggle.classList.add('on');
                fields.style.display = '';
                textOverlayEnabled = true;
            }
        }

        function getLottieData() {
            const items = document.querySelectorAll('[data-lottie-index]');
            const data = [];
            items.forEach(item => {
                const index = parseInt(item.dataset.lottieIndex);
                const fields = item.querySelectorAll('.lottie-field');
                const lo = {};
                fields.forEach(f => {
                    const val = f.type === 'number' ? parseFloat(f.value) : f.value;
                    lo[f.dataset.field] = val;
                });
                data[index] = lo;
            });
            return data.filter(Boolean);
        }

        function getSfxData() {
            const items = document.querySelectorAll('[data-sfx-index]');
            const data = [];
            items.forEach(item => {
                const index = parseInt(item.dataset.sfxIndex);
                const fields = item.querySelectorAll('.sfx-field');
                const sfx = {};
                fields.forEach(f => {
                    const val = f.type === 'number' ? parseFloat(f.value) : f.value;
                    sfx[f.dataset.field] = val;
                });
                data[index] = sfx;
            });
            return data.filter(Boolean);
        }

        function addLottie() {
            if (!currentScene) return;
            currentScene.lottie_overlays.push({ lottie_name: enumOpts.lottie_presets[0] || 'success', start_time: 0, position: 'center', scale: 0.5 });
            renderEditor(currentScene);
        }

        function removeLottie(index) {
            if (!currentScene) return;
            currentScene.lottie_overlays.splice(index, 1);
            renderEditor(currentScene);
        }

        function addSfx() {
            if (!currentScene) return;
            currentScene.sound_effects.push({ preset_name: enumOpts.sfx_presets[0] || 'success', volume: 0.5, start_time: 0, fade_in: 0, fade_out: 0 });
            renderEditor(currentScene);
        }

        function removeSfx(index) {
            if (!currentScene) return;
            currentScene.sound_effects.splice(index, 1);
            renderEditor(currentScene);
        }

        function renderAssets(s) {
            const c = document.getElementById('assetContent');
            const lottieOverlays = s.lottie_overlays || [];
            const soundEffects = s.sound_effects || [];
            c.innerHTML = `
                ${renderAssetSection('Rendered Scene', s.rendered_scene_path, 'video', null)}
                ${renderAssetSection('Audio (TTS)', s.prepared?.audio_path, 'audio', 'audio', s.prepared?.audio_duration ? `Duration: ${s.prepared.audio_duration.toFixed(2)}s` : null)}
                ${renderAssetSection('Visual Layer (' + s.visual_type + ')', s.prepared?.visual_path, detectMediaType(s.prepared?.visual_path), 'visual')}
                ${s.text_overlay_content !== null ? renderAssetSection('Text Overlay', s.prepared?.text_overlay_path, 'video', 'text_overlay') : ''}
                ${lottieOverlays.length > 0 ? renderLottiePreviewSection(lottieOverlays) : ''}
                ${soundEffects.length > 0 ? renderSfxPreviewSection(soundEffects) : ''}
                <button class="render-scene-btn" onclick="regenerate(currentSceneId, 'scene')">Re-render Scene</button>
            `;
        }

        function renderLottiePreviewSection(lottieOverlays) {
            const items = lottieOverlays.map((lo, i) => `
                <div class="preview-item">
                    <div class="preview-item-header">
                        <span class="preview-item-name">${lo.lottie_name}</span>
                        <span class="preview-item-meta">pos: ${lo.position}, scale: ${lo.scale}</span>
                    </div>
                    <div class="preview-item-content" id="lottiePreview_${i}">
                        <button class="preview-play-btn" onclick="playLottie('${lo.lottie_name}', ${i})">Play</button>
                    </div>
                </div>
            `).join('');
            return `
                <div class="asset-section">
                    <div class="asset-header">
                        <span class="asset-title">Lottie Overlays</span>
                        <span class="asset-status ready">${lottieOverlays.length}</span>
                    </div>
                    <div class="preview-list">${items}</div>
                </div>`;
        }

        function renderSfxPreviewSection(soundEffects) {
            const items = soundEffects.map((sfx, i) => `
                <div class="preview-item">
                    <div class="preview-item-header">
                        <span class="preview-item-name">${sfx.preset_name}</span>
                        <span class="preview-item-meta">vol: ${sfx.volume}, start: ${sfx.start_time}s</span>
                    </div>
                    <div class="preview-item-content" id="sfxPreview_${i}">
                        <button class="preview-play-btn" onclick="playSfx('${sfx.preset_name}', ${i})">Play</button>
                    </div>
                </div>
            `).join('');
            return `
                <div class="asset-section">
                    <div class="asset-header">
                        <span class="asset-title">Sound Effects</span>
                        <span class="asset-status ready">${soundEffects.length}</span>
                    </div>
                    <div class="preview-list">${items}</div>
                </div>`;
        }

        async function playLottie(presetName, index) {
            const container = document.getElementById(`lottiePreview_${index}`);
            if (!container) return;
            try {
                const res = await fetch(`/api/lottie/${encodeURIComponent(presetName)}`);
                if (!res.ok) throw new Error('Failed to load lottie');
                const data = await res.json();
                const cacheBust = `&_t=${Date.now()}`;
                container.innerHTML = `<video controls autoplay src="/api/asset?path=${encodeURIComponent(data.path)}${cacheBust}" style="max-width:100%;max-height:120px;border-radius:4px;"></video>`;
            } catch (e) {
                container.innerHTML = `<p style="color:#ff6b6b;font-size:10px;">Failed to load</p>`;
            }
        }

        async function playSfx(presetName, index) {
            const container = document.getElementById(`sfxPreview_${index}`);
            if (!container) return;
            try {
                const res = await fetch(`/api/sfx/${encodeURIComponent(presetName)}`);
                if (!res.ok) throw new Error('Failed to load sfx');
                const data = await res.json();
                const cacheBust = `&_t=${Date.now()}`;
                container.innerHTML = `<audio controls autoplay src="/api/asset?path=${encodeURIComponent(data.path)}${cacheBust}" style="width:100%;height:32px;"></audio>`;
            } catch (e) {
                container.innerHTML = `<p style="color:#ff6b6b;font-size:10px;">Failed to load</p>`;
            }
        }

        function renderAssetSection(title, path, mediaType, regenType, extra) {
            const hasPath = !!path;
            const cacheBust = `&_t=${Date.now()}`;
            return `
                <div class="asset-section">
                    <div class="asset-header">
                        <span class="asset-title">${title}</span>
                        <div>
                            <span class="asset-status ${hasPath ? 'ready' : 'missing'}">${hasPath ? 'Ready' : 'Missing'}</span>
                            ${regenType ? `<button class="regen-btn" onclick="regenerate(currentSceneId, '${regenType}')">Regen</button>` : ''}
                        </div>
                    </div>
                    <div class="asset-preview">
                        ${hasPath && mediaType === 'video' ? `<video controls src="/api/asset?path=${encodeURIComponent(path)}${cacheBust}"></video>` : ''}
                        ${hasPath && mediaType === 'audio' ? `<audio controls src="/api/asset?path=${encodeURIComponent(path)}${cacheBust}"></audio>` : ''}
                        ${hasPath && mediaType === 'image' ? `<img src="/api/asset?path=${encodeURIComponent(path)}${cacheBust}">` : ''}
                        ${!hasPath ? '<p style="color:#444;font-size:11px;">Not generated</p>' : ''}
                    </div>
                    ${extra ? `<div class="asset-path">${extra}</div>` : ''}
                    ${hasPath ? `<div class="asset-path">${path}</div>` : ''}
                </div>`;
        }

        function detectMediaType(path) {
            if (!path) return null;
            if (path.match(/\\.(mp4|mov)$/i)) return 'video';
            if (path.match(/\\.(png|jpg|jpeg|webp)$/i)) return 'image';
            return 'video';
        }

        async function saveScene() {
            if (!currentSceneId) return;
            const genDurVal = document.getElementById('editGenDuration')?.value;
            const data = {
                audio_script_text: document.getElementById('editAudioText')?.value,
                audio_script_speed: parseFloat(document.getElementById('editAudioSpeed')?.value) || null,
                visual_type: document.getElementById('editVisualType')?.value || null,
                visual_prompt: document.getElementById('editVisualPrompt')?.value || null,
                visual_fallback_prompt: document.getElementById('editFallbackPrompt')?.value || null,
                visual_gen_duration: genDurVal ? parseInt(genDurVal) : null,
                duration: parseFloat(document.getElementById('editDuration')?.value) || null,
                sync_mode: document.getElementById('editSyncMode')?.value || null,
                video_fit_mode: document.getElementById('editVideoFitMode')?.value || null,
                camera_movement: document.getElementById('editCamera')?.value || null,
                transition_next: document.getElementById('editTransition')?.value || null,
                lottie_overlays: getLottieData(),
                sound_effects: getSfxData(),
            };
            if (textOverlayEnabled !== null) {
                data.text_overlay_enabled = textOverlayEnabled;
            }
            const toggle = document.getElementById('textOverlayToggle');
            if (toggle && toggle.classList.contains('on')) {
                data.text_overlay_content = document.getElementById('editTextOverlay')?.value || '';
                data.text_overlay_style = document.getElementById('editTextStyle')?.value || null;
                data.text_overlay_animation = document.getElementById('editTextAnimation')?.value || null;
                data.text_overlay_position = document.getElementById('editTextPosition')?.value || null;
                data.text_overlay_font_color = document.getElementById('editFontColorText')?.value || null;
                data.text_overlay_background_color = document.getElementById('editBgColorText')?.value || null;
            }
            try {
                const res = await fetch(`/api/scenes/${currentSceneId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!res.ok) throw new Error((await res.json()).detail);
                const result = await res.json();
                isDirty = result.dirty || false;
                updateDirtyIndicator();
                textOverlayEnabled = null;
                showToast('Scene saved');
                await refreshScenes();
            } catch (e) { showToast(e.message, true); }
        }

        async function regenerate(sceneId, assetType) {
            try {
                await saveScene();
                const res = await fetch('/api/regenerate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ scene_id: sceneId, asset_type: assetType })
                });
                const data = await res.json();
                showToast(data.message + ' (processing...)');
                if (data.task_id) {
                    pollTaskStatus(data.task_id);
                }
            } catch (e) { showToast('Regeneration failed', true); }
        }

        async function pollTaskStatus(taskId) {
            const poll = async () => {
                try {
                    const res = await fetch(`/api/tasks/${taskId}`);
                    if (!res.ok) return;
                    const task = await res.json();
                    if (task.status === 'completed') {
                        isDirty = true;
                        updateDirtyIndicator();
                        showToast('Completed: ' + task.message);
                        await refreshScenes();
                    } else if (task.status === 'failed') {
                        showToast('Failed: ' + task.message, true);
                    } else {
                        setTimeout(poll, 1000);
                    }
                } catch (e) {
                    setTimeout(poll, 1000);
                }
            };
            poll();
        }

        function esc(text) {
            const d = document.createElement('div');
            d.textContent = text || '';
            return d.innerHTML;
        }

        function showToast(msg, isError = false) {
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.className = 'toast show' + (isError ? ' error' : '');
            setTimeout(() => t.className = 'toast', 3000);
        }

        document.getElementById('sequencePath').addEventListener('keypress', e => {
            if (e.key === 'Enter') loadSequence();
        });

        (async function init() {
            try {
                const enumRes = await fetch('/api/enums');
                if (enumRes.ok) enumOpts = await enumRes.json();

                const res = await fetch('/api/scenario');
                if (res.ok) {
                    const data = await res.json();
                    isDirty = data.dirty || false;
                    updateDirtyIndicator();
                    await refreshScenes();
                }
            } catch (e) {}
        })();
    </script>
</body>
</html>"""


def run_viewer(sequence_path: str | None = None, host: str = "127.0.0.1", port: int = 8765):
    import uvicorn

    if sequence_path:
        path = Path(sequence_path)
        if path.exists():
            parser = ScenarioParser()
            _state["sequence_path"] = path
            _state["scenario"] = parser.parse_file(path)
            print(f"Loaded sequence: {sequence_path}")

    print(f"Starting viewer at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
