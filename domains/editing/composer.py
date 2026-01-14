import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from domains.editing.models import ComposedScene, Timeline


@dataclass
class VisualResult:
    path: Path | None
    clip_start: float | None = None
    clip_end: float | None = None


from domains.editing.renderer import FFmpegRenderer
from domains.library.models import VideoClip
from domains.library.repository import AssetRepository
from domains.library.selector import FootageSelector
from domains.planning.models import Scene, Scenario, SyncMode, VideoType, VisualType
from domains.studio.fallback_generator import FallbackGenerator
from domains.studio.image_generator import ImageGenerator
from domains.studio.models import AudioAsset, ImageAsset, VideoAsset
from domains.studio.text_renderer import TextAnimationRenderer
from domains.studio.tts_generator import TTSGenerator
from domains.studio.video_generator import VideoGenerator

logger = logging.getLogger(__name__)


class SequenceComposer:
    def __init__(
        self,
        tts_generator: TTSGenerator,
        image_generator: ImageGenerator,
        video_generator: VideoGenerator,
        text_renderer: TextAnimationRenderer,
        asset_repository: AssetRepository | None = None,
        footage_selector: FootageSelector | None = None,
        renderer: FFmpegRenderer | None = None,
        fallback_generator: FallbackGenerator | None = None,
        verbose: bool = False,
        max_tts_speed: float = 1.2,
        min_tts_speed: float = 0.5,
    ):
        self.tts = tts_generator
        self.image_gen = image_generator
        self.video_gen = video_generator
        self.text_renderer = text_renderer
        self.asset_repo = asset_repository
        self.footage_selector = footage_selector
        self.renderer = renderer or FFmpegRenderer()
        self.fallback_gen = fallback_generator or FallbackGenerator()
        self.verbose = verbose
        self.max_tts_speed = max_tts_speed
        self.min_tts_speed = min_tts_speed
        self.max_workers = 4
        self._used_clip_ids: set[str] = set()
        self._scene_clip_mapping: dict[str, str] = {}

    def _log(self, message: str) -> None:
        if self.verbose:
            print(message)

    def _init_used_clips_from_scenario(self, scenario: Scenario) -> None:
        for scene in scenario.scenes:
            if scene.selected_clip_id:
                self._used_clip_ids.add(scene.selected_clip_id)
                self._scene_clip_mapping[scene.scene_id] = scene.selected_clip_id

    def _compose_scenes_parallel(
        self,
        scenes: list[Scene],
        width: int,
        height: int,
        video_type: VideoType,
    ) -> list[ComposedScene]:
        if len(scenes) <= 1:
            return [self._compose_scene(s, width, height, video_type) for s in scenes]

        self._log(f"\n[PARALLEL] Composing {len(scenes)} scenes with {self.max_workers} workers...")

        def compose_with_index(args: tuple[int, Scene]) -> tuple[int, ComposedScene]:
            idx, scene = args
            self._log(f"\n[Scene {idx + 1}/{len(scenes)}] {scene.scene_id}")
            composed = self._compose_scene(scene, width, height, video_type)
            return idx, composed

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(compose_with_index, enumerate(scenes)))

        results.sort(key=lambda x: x[0])
        return [composed for _, composed in results]

    def compose(
        self, scenario: Scenario, output_filename: str | None = None
    ) -> tuple[Path, Timeline]:
        self._log(f"\n=== Composing: {scenario.project_id} ===")
        self._log(f"Scenes: {len(scenario.scenes)}")
        self._log(
            f"Resolution: {scenario.scenario_meta.resolution[0]}x{scenario.scenario_meta.resolution[1]}"
        )

        self._used_clip_ids.clear()
        self._scene_clip_mapping.clear()

        self._init_used_clips_from_scenario(scenario)

        timeline = Timeline(
            project_id=scenario.project_id,
            width=scenario.scenario_meta.resolution[0],
            height=scenario.scenario_meta.resolution[1],
        )

        video_type = scenario.scenario_meta.video_type
        self._log(f"Video type: {video_type.value}")

        composed_scenes = self._compose_scenes_parallel(
            scenario.scenes, timeline.width, timeline.height, video_type
        )
        for composed in composed_scenes:
            timeline.add_scene(composed)

        self._update_scenario_with_selected_clips(scenario)

        self._log(f"\n=== Rendering final video ===")
        return self.renderer.render_timeline(timeline, output_filename), timeline

    def _update_scenario_with_selected_clips(self, scenario: Scenario) -> None:
        for scene in scenario.scenes:
            if scene.scene_id in self._scene_clip_mapping:
                scene.selected_clip_id = self._scene_clip_mapping[scene.scene_id]

    def recompose_scene(
        self,
        scenario: Scenario,
        scene_id: str,
        output_filename: str | None = None,
    ) -> tuple[Path, str | None]:
        scene = next((s for s in scenario.scenes if s.scene_id == scene_id), None)
        if not scene:
            raise ValueError(f"Scene not found: {scene_id}")

        self._log(f"\n=== Recomposing scene: {scene_id} ===")

        self._used_clip_ids.clear()
        self._scene_clip_mapping.clear()

        for s in scenario.scenes:
            if s.scene_id != scene_id and s.selected_clip_id:
                self._used_clip_ids.add(s.selected_clip_id)

        scene.selected_clip_id = None

        timeline = Timeline(
            project_id=scenario.project_id,
            width=scenario.scenario_meta.resolution[0],
            height=scenario.scenario_meta.resolution[1],
        )

        video_type = scenario.scenario_meta.video_type
        composed = self._compose_scene(scene, timeline.width, timeline.height, video_type)

        new_clip_id = self._scene_clip_mapping.get(scene_id)
        if new_clip_id:
            scene.selected_clip_id = new_clip_id

        return self.renderer.render_single_scene(composed, timeline), new_clip_id

    def reassemble(
        self,
        scenario: Scenario,
        output_filename: str | None = None,
    ) -> Path:
        self._log(f"\n=== Reassembling from existing scenes: {scenario.project_id} ===")

        scene_ids = [scene.scene_id for scene in scenario.scenes]

        return self.renderer.reassemble_from_scene_ids(
            project_id=scenario.project_id,
            scene_ids=scene_ids,
            output_filename=output_filename,
        )

    def _compose_scene(
        self, scene: Scene, width: int, height: int, video_type: VideoType = VideoType.MIXED
    ) -> ComposedScene:
        self._log(f"  Sync mode: {scene.sync_mode.value}")

        self._log(f"  Generating audio...")
        duration, audio_asset = self._resolve_duration_and_audio(scene)
        self._log(f"  Audio duration: {duration:.2f}s")

        visual_result, text_overlay_path = self._acquire_visual_and_text_parallel(
            scene, duration, width, height, video_type
        )

        effects = {
            "camera_movement": scene.fx_beat.camera_movement.value,
            "transition_next": scene.fx_beat.transition_next.value,
            "beat_effect": scene.fx_beat.effect,
            "beat_timing": scene.fx_beat.beat_timing,
        }

        return ComposedScene(
            scene_id=scene.scene_id,
            video_path=visual_result.path,
            audio_path=audio_asset.file_path if audio_asset else None,
            text_overlay_path=text_overlay_path,
            duration=duration,
            effects=effects,
            clip_start_time=visual_result.clip_start,
            clip_end_time=visual_result.clip_end,
        )

    def _acquire_visual_and_text_parallel(
        self,
        scene: Scene,
        duration: float,
        width: int,
        height: int,
        video_type: VideoType,
    ) -> tuple[VisualResult, Path | None]:
        has_text_overlay = scene.text_overlay is not None

        if not has_text_overlay:
            self._log(f"  Acquiring visual ({scene.visual_layer.type.value})...")
            visual_result = self._acquire_visual(scene, duration, width, height, video_type)
            self._log(f"  Visual: {visual_result.path}")
            return visual_result, None

        self._log(f"  [PARALLEL] Acquiring visual + text overlay...")

        def acquire_visual() -> VisualResult:
            return self._acquire_visual(scene, duration, width, height, video_type)

        def render_text() -> Path | None:
            if not scene.text_overlay:
                return None
            text_asset = self.text_renderer.render_overlay(
                text=scene.text_overlay.content,
                style_template=scene.text_overlay.style_template,
                animation=scene.text_overlay.animation.value,
                position=scene.text_overlay.position,
                duration=duration,
                width=width,
                height=height,
            )
            return text_asset.file_path

        with ThreadPoolExecutor(max_workers=2) as executor:
            visual_future = executor.submit(acquire_visual)
            text_future = executor.submit(render_text)

            visual_result = visual_future.result()
            text_overlay_path = text_future.result()

        self._log(f"  Visual: {visual_result.path}")
        if text_overlay_path:
            self._log(f"  Text overlay: {text_overlay_path}")

        return visual_result, text_overlay_path

    def _resolve_duration_and_audio(self, scene: Scene) -> tuple[float, AudioAsset | None]:
        sync_mode = scene.sync_mode

        if sync_mode == SyncMode.AUDIO:
            audio_asset = self._generate_audio(scene)
            return audio_asset.duration, audio_asset

        if sync_mode == SyncMode.VISUAL:
            target_duration = scene.duration or 3.0
            return self._generate_audio_fitted_to_duration(scene, target_duration)

        if sync_mode == SyncMode.BEAT:
            beat_timing = scene.fx_beat.beat_timing
            if beat_timing:
                target_duration = max(beat_timing) + 0.5
            else:
                target_duration = scene.duration or 3.0
            return self._generate_audio_fitted_to_duration(scene, target_duration)

        audio_asset = self._generate_audio(scene)
        return audio_asset.duration, audio_asset

    def _generate_audio_fitted_to_duration(
        self, scene: Scene, target_duration: float
    ) -> tuple[float, AudioAsset]:
        test_audio = self._generate_audio(scene, speed_override=1.0)
        natural_duration = test_audio.duration

        required_speed = natural_duration / target_duration
        clamped_speed = max(self.min_tts_speed, min(self.max_tts_speed, required_speed))

        if abs(required_speed - 1.0) < 0.05:
            return target_duration, test_audio

        audio_asset = self._generate_audio(scene, speed_override=clamped_speed)
        return audio_asset.duration, audio_asset

    def _generate_audio(self, scene: Scene, speed_override: float | None = None) -> AudioAsset:
        speed = speed_override if speed_override is not None else scene.audio_script.speed
        return self.tts.generate(
            text=scene.audio_script.text,
            preset_id=scene.audio_script.voice_preset_id,
            speed=speed,
            output_filename=f"{scene.scene_id}_audio_{speed:.2f}.wav",
        )

    def _acquire_visual(
        self,
        scene: Scene,
        duration: float,
        width: int,
        height: int,
        video_type: VideoType = VideoType.MIXED,
    ) -> VisualResult:
        if video_type == VideoType.UGC_CENTERED:
            return self._acquire_visual_ugc_centered(scene, duration, width, height)

        if video_type == VideoType.AI_GENERATED:
            return self._acquire_visual_ai_generated(scene, duration, width, height)

        return self._acquire_visual_mixed(scene, duration, width, height)

    def _acquire_visual_ugc_centered(
        self,
        scene: Scene,
        duration: float,
        width: int,
        height: int,
    ) -> VisualResult:
        visual = scene.visual_layer

        clip = self._find_existing_clip(scene, duration)
        if clip:
            return VisualResult(
                path=clip.source_file, clip_start=clip.start_time, clip_end=clip.end_time
            )

        prompt = visual.prompt or visual.fallback_gen_prompt
        if prompt:
            self._log(f"    No existing footage found, falling back to AI generation")
            return VisualResult(path=self._generate_image(prompt, width, height))

        return VisualResult(path=None)

    def _acquire_visual_ai_generated(
        self,
        scene: Scene,
        duration: float,
        width: int,
        height: int,
    ) -> VisualResult:
        visual = scene.visual_layer
        prompt = visual.prompt or visual.fallback_gen_prompt or ""

        if visual.type == VisualType.MOTION_GRAPHIC_GEN:
            return VisualResult(path=self._generate_video(prompt, duration, width, height))

        return VisualResult(path=self._generate_image(prompt, width, height))

    def _acquire_visual_mixed(
        self,
        scene: Scene,
        duration: float,
        width: int,
        height: int,
    ) -> VisualResult:
        visual = scene.visual_layer

        if visual.type == VisualType.EXISTING_FOOTAGE:
            clip = self._find_existing_clip(scene, duration)
            if clip:
                return VisualResult(
                    path=clip.source_file, clip_start=clip.start_time, clip_end=clip.end_time
                )

            if visual.fallback_gen_prompt:
                return VisualResult(
                    path=self._generate_image(visual.fallback_gen_prompt, width, height)
                )
            return VisualResult(path=None)

        if visual.type == VisualType.IMAGE_GEN:
            prompt = visual.prompt or visual.fallback_gen_prompt or ""
            return VisualResult(path=self._generate_image(prompt, width, height))

        if visual.type == VisualType.MOTION_GRAPHIC_GEN:
            prompt = visual.prompt or visual.fallback_gen_prompt or ""
            return VisualResult(path=self._generate_video(prompt, duration, width, height))

        return VisualResult(path=None)

    def _find_existing_clip(
        self,
        scene: Scene,
        min_duration: float,
    ) -> VideoClip | None:
        if not self.asset_repo:
            return None

        if scene.selected_clip_id:
            clip = self.asset_repo.get_clip_by_id(scene.selected_clip_id)
            if clip:
                self._log(f"    Using pre-selected clip: {scene.selected_clip_id}")
                return clip

        visual = scene.visual_layer
        query_tags = visual.query_tags

        search_query = self._build_search_query(scene)
        candidates = self.asset_repo.find_by_embedding(
            query=search_query,
            max_results=20,
            min_duration=0,
        )

        if not candidates:
            candidates = self.asset_repo.get_all_clips()

        if not candidates:
            return None

        candidates = [c for c in candidates if c.clip_id not in self._used_clip_ids]

        if not candidates:
            self._log(f"    All candidates already used in this sequence")
            return None

        self._log(f"    Found {len(candidates)} candidates via embedding search")

        selected: VideoClip | None = None
        if self.footage_selector:
            selected = self.footage_selector.select_clip(
                clips=candidates,
                audio_text=scene.audio_script.text,
                visual_prompt=visual.prompt or visual.fallback_gen_prompt or "",
                query_tags=query_tags,
                min_duration=min_duration,
                verbose=self.verbose,
            )
        else:
            eligible = [c for c in candidates if c.duration >= min_duration]
            selected = eligible[0] if eligible else (candidates[0] if candidates else None)

        if selected:
            self._used_clip_ids.add(selected.clip_id)
            self._scene_clip_mapping[scene.scene_id] = selected.clip_id

        return selected

    def _build_search_query(self, scene: Scene) -> str:
        parts = []
        if scene.audio_script.text:
            parts.append(scene.audio_script.text)
        visual = scene.visual_layer
        if visual.prompt:
            parts.append(visual.prompt)
        if visual.fallback_gen_prompt:
            parts.append(visual.fallback_gen_prompt)
        if visual.query_tags:
            parts.append(" ".join(visual.query_tags))
        return " ".join(parts)

    def _generate_image(self, prompt: str, width: int, height: int) -> Path:
        try:
            asset = self.image_gen.generate(prompt=prompt, width=width, height=height)
            return asset.file_path
        except Exception as e:
            logger.warning(f"Image generation failed: {e}")
            return self.fallback_gen.generate_black_screen_image(
                width=width,
                height=height,
                error_message=f"[Image Generation Failed]\n{prompt[:50]}",
            )

    def _generate_video(
        self,
        prompt: str,
        duration: float,
        width: int,
        height: int,
    ) -> Path:
        try:
            dur_seconds = min(int(duration), 8)
            asset = self.video_gen.generate(
                prompt=prompt,
                width=width,
                height=height,
                duration=dur_seconds,
            )
            return asset.file_path
        except Exception as e:
            logger.warning(f"Video generation failed: {e}")
            return self.fallback_gen.generate_black_screen_video(
                width=width,
                height=height,
                duration=duration,
                error_message=f"[Video Generation Failed]\n{prompt[:50]}",
            )
