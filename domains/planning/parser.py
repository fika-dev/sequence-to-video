import json
from pathlib import Path

from domains.planning.models import (
    AudioScript,
    FxBeat,
    Scene,
    Scenario,
    ScenarioMeta,
    SyncMode,
    TextOverlay,
    VideoType,
    VisualLayer,
    VisualType,
)


class ScenarioParser:
    def parse_file(self, file_path: str | Path) -> Scenario:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        return self.parse_dict(data)

    def parse_json(self, json_str: str) -> Scenario:
        data = json.loads(json_str)
        return self.parse_dict(data)

    def parse_dict(self, data: dict) -> Scenario:
        project_id = data.get("project_id", "unnamed_project")
        scenario_meta = self._parse_meta(data.get("scenario_meta", {}), data)
        scenes = [self._parse_scene(s, i) for i, s in enumerate(data.get("scenes", []), 1)]

        return Scenario(
            project_id=project_id,
            scenario_meta=scenario_meta,
            scenes=scenes,
        )

    def _parse_meta(self, meta_data: dict, root_data: dict) -> ScenarioMeta:
        title = meta_data.get("title") or root_data.get("scenario_title", "Untitled")
        tone_voice = meta_data.get("tone_voice") or root_data.get("matched_tone", "")
        video_type = self._parse_video_type(meta_data.get("video_type"))

        return ScenarioMeta(
            title=title,
            tone_voice=tone_voice,
            aspect_ratio=meta_data.get("aspect_ratio", "9:16"),
            video_type=video_type,
        )

    def _parse_video_type(self, video_type_str: str | None) -> VideoType:
        if not video_type_str:
            return VideoType.MIXED
        try:
            return VideoType(video_type_str)
        except ValueError:
            return VideoType.MIXED

    def _parse_scene(self, scene_data: dict, default_order: int) -> Scene:
        scene_id = scene_data.get("scene_id", f"s{default_order:02d}")
        sequence_order = scene_data.get("sequence_order") or scene_data.get(
            "scene_number", default_order
        )

        audio_script = self._parse_audio(scene_data)
        visual_layer = self._parse_visual(scene_data)
        text_overlay = self._parse_text_overlay(scene_data)
        fx_beat = self._parse_fx_beat(scene_data)
        sync_mode = self._parse_sync_mode(scene_data)
        duration = scene_data.get("duration")

        return Scene(
            scene_id=scene_id,
            sequence_order=sequence_order,
            audio_script=audio_script,
            visual_layer=visual_layer,
            text_overlay=text_overlay,
            fx_beat=fx_beat,
            sync_mode=sync_mode,
            duration=duration,
        )

    def _parse_sync_mode(self, scene_data: dict) -> SyncMode:
        sync_mode_str = scene_data.get("sync_mode", "audio")
        try:
            return SyncMode(sync_mode_str)
        except ValueError:
            return SyncMode.AUDIO

    def _parse_audio(self, scene_data: dict) -> AudioScript:
        if "audio_script" in scene_data:
            audio_data = scene_data["audio_script"]
            return AudioScript(
                text=audio_data.get("text", ""),
                voice_preset_id=audio_data.get(
                    "voice_preset_id", "chirp_v3_korean_female_confident"
                ),
                speed=audio_data.get("speed", 1.0),
            )

        return AudioScript(
            text=scene_data.get("script_kr", ""),
            voice_preset_id=self._infer_voice_preset(scene_data.get("audio_note", "")),
        )

    def _parse_visual(self, scene_data: dict) -> VisualLayer:
        if "visual_layer" in scene_data:
            vl = scene_data["visual_layer"]
            return VisualLayer(
                type=VisualType(vl.get("type", "existing_footage")),
                query_tags=vl.get("query_tags", []),
                prompt=vl.get("prompt"),
                fallback_gen_prompt=vl.get("fallback_gen_prompt"),
                model=vl.get("model", "google_imagen_3"),
            )

        visual_note = scene_data.get("scene_visual_note", "")
        visual_type, tags = self._infer_visual_type(visual_note)

        return VisualLayer(
            type=visual_type,
            query_tags=tags,
            fallback_gen_prompt=visual_note,
        )

    def _parse_text_overlay(self, scene_data: dict) -> TextOverlay | None:
        if "text_overlay" in scene_data:
            to = scene_data["text_overlay"]
            return TextOverlay(
                content=to.get("content", ""),
                style_template=to.get("style_template", "bold_impact_white"),
            )

        visual_note = scene_data.get("scene_visual_note", "")
        text_content = self._extract_text_from_visual_note(visual_note)
        if text_content:
            return TextOverlay(content=text_content)

        return None

    def _parse_fx_beat(self, scene_data: dict) -> FxBeat:
        if "fx_beat" in scene_data:
            fb = scene_data["fx_beat"]
            return FxBeat(
                camera_movement=fb.get("camera_movement", "none"),
                transition_next=fb.get("transition_next", "cut"),
                effect=fb.get("effect"),
                beat_timing=fb.get("beat_timing", []),
            )
        return FxBeat()

    def _infer_voice_preset(self, audio_note: str) -> str:
        note_lower = audio_note.lower()
        if "냉소" in audio_note or "cynical" in note_lower:
            return "chirp_v3_korean_female_cynical"
        if "강조" in audio_note or "emphasis" in note_lower:
            return "chirp_v3_korean_female_emphasis"
        if "은밀" in audio_note or "whisper" in note_lower:
            return "chirp_v3_korean_female_whisper"
        return "chirp_v3_korean_female_confident"

    def _infer_visual_type(self, visual_note: str) -> tuple[VisualType, list[str]]:
        note_lower = visual_note.lower()

        if "[모션그래픽]" in visual_note or "[3d 그래픽]" in visual_note.lower():
            return VisualType.MOTION_GRAPHIC_GEN, []
        if "[자료화면]" in visual_note or "[자료]" in visual_note:
            return VisualType.EXISTING_FOOTAGE, self._extract_tags(visual_note)
        if "[인물]" in visual_note or "[상황]" in visual_note:
            return VisualType.EXISTING_FOOTAGE, self._extract_tags(visual_note)
        if "[제품]" in visual_note:
            return VisualType.EXISTING_FOOTAGE, ["product", "closeup"]
        if "animation" in note_lower or "graphic" in note_lower:
            return VisualType.MOTION_GRAPHIC_GEN, []

        return VisualType.EXISTING_FOOTAGE, self._extract_tags(visual_note)

    def _extract_tags(self, visual_note: str) -> list[str]:
        tags = []
        keywords = [
            "여성",
            "남성",
            "뒷모습",
            "정면",
            "클로즈업",
            "줌인",
            "줌아웃",
            "사무실",
            "화장실",
            "야식",
            "배",
            "얼굴",
            "손",
            "제품",
        ]
        for kw in keywords:
            if kw in visual_note:
                tags.append(kw)
        return tags

    def _extract_text_from_visual_note(self, visual_note: str) -> str | None:
        import re

        patterns = [r"자막:\s*['\"]?([^'\"]+)['\"]?", r"'([^']+)'\s*자막", r"텍스트[:\s]+([^\s]+)"]
        for pattern in patterns:
            match = re.search(pattern, visual_note)
            if match:
                return match.group(1).strip()
        return None
