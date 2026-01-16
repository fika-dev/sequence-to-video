from typing import Any

import pytest

from domains.planning.models import (
    SyncMode,
    TextStyle,
    VideoType,
    VisualType,
)
from domains.planning.parser import ScenarioParser


class TestScenarioParserParseDict:
    def test_parses_minimal_sequence(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)

        assert scenario.project_id == "test_project"
        assert len(scenario.scenes) == 1

    def test_extracts_scenario_meta(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)

        assert scenario.scenario_meta.title == "Test Video"
        assert scenario.scenario_meta.tone_voice == "energetic"
        assert scenario.scenario_meta.aspect_ratio == "9:16"

    def test_defaults_project_id_if_missing(self):
        parser = ScenarioParser()
        data = {"scenes": []}

        scenario = parser.parse_dict(data)

        assert scenario.project_id == "unnamed_project"

    def test_defaults_video_type_to_mixed(self):
        parser = ScenarioParser()
        data = {
            "project_id": "test",
            "scenario_meta": {"title": "Test"},
            "scenes": [],
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenario_meta.video_type == VideoType.MIXED

    def test_parses_ugc_centered_video_type(self):
        parser = ScenarioParser()
        data = {
            "project_id": "test",
            "scenario_meta": {"title": "Test", "video_type": "ugc_centered"},
            "scenes": [],
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenario_meta.video_type == VideoType.UGC_CENTERED

    def test_parses_ai_generated_video_type(self):
        parser = ScenarioParser()
        data = {
            "project_id": "test",
            "scenario_meta": {"title": "Test", "video_type": "ai_generated"},
            "scenes": [],
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenario_meta.video_type == VideoType.AI_GENERATED


class TestScenarioParserParseScene:
    def test_parses_scene_id_and_order(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)
        scene = scenario.scenes[0]

        assert scene.scene_id == "s01"
        assert scene.sequence_order == 1

    def test_generates_scene_id_if_missing(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "sequence_order": 3,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].scene_id == "s01"

    def test_parses_audio_script(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)
        audio = scenario.scenes[0].audio_script

        assert audio.text == "Hello world"
        assert audio.voice_preset_id == "chirp_v3_korean_female_confident"
        assert audio.speed == 1.0

    def test_parses_visual_layer(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)
        visual = scenario.scenes[0].visual_layer

        assert visual.type == VisualType.EXISTING_FOOTAGE
        assert visual.query_tags == ["product", "closeup"]
        assert visual.prompt == "Product shot on white background"

    def test_parses_image_gen_visual_type(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "image_gen", "prompt": "Beautiful sunset"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].visual_layer.type == VisualType.IMAGE_GEN

    def test_parses_motion_graphic_visual_type(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "motion_graphic_gen"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].visual_layer.type == VisualType.MOTION_GRAPHIC_GEN

    def test_parses_sync_mode_audio(self, sample_sequence_dict: dict[str, Any]):
        parser = ScenarioParser()

        scenario = parser.parse_dict(sample_sequence_dict)

        assert scenario.scenes[0].sync_mode == SyncMode.AUDIO

    def test_parses_sync_mode_visual(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "sync_mode": "visual",
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].sync_mode == SyncMode.VISUAL

    def test_parses_sync_mode_beat(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "sync_mode": "beat",
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].sync_mode == SyncMode.BEAT

    def test_defaults_sync_mode_to_audio(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].sync_mode == SyncMode.AUDIO


class TestScenarioParserParseTextOverlay:
    def test_parses_text_overlay(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "text_overlay": {
                        "content": "Amazing!",
                        "style": "bold_impact_white",
                    },
                }
            ]
        }

        scenario = parser.parse_dict(data)
        overlay = scenario.scenes[0].text_overlay

        assert overlay is not None
        assert overlay.content == "Amazing!"
        assert overlay.style == TextStyle.BOLD_IMPACT_WHITE

    def test_parses_bold_impact_red_style(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "text_overlay": {
                        "content": "Warning!",
                        "style": "bold_impact_red",
                    },
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].text_overlay.style == TextStyle.BOLD_IMPACT_RED

    def test_defaults_style_on_invalid_value(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "text_overlay": {
                        "content": "Text",
                        "style": "invalid_style",
                    },
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].text_overlay.style == TextStyle.BOLD_IMPACT_WHITE

    def test_returns_none_when_no_overlay(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].text_overlay is None


class TestScenarioParserParseSoundEffects:
    def test_parses_sound_effects(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "sound_effects": [
                        {"preset_name": "success", "volume": 0.7, "start_time": 0.5}
                    ],
                }
            ]
        }

        scenario = parser.parse_dict(data)
        sfx = scenario.scenes[0].sound_effects

        assert len(sfx) == 1
        assert sfx[0].preset_name == "success"
        assert sfx[0].volume == 0.7
        assert sfx[0].start_time == 0.5

    def test_parses_multiple_sound_effects(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "sound_effects": [
                        {"preset_name": "whoosh", "volume": 0.5},
                        {"preset_name": "click", "volume": 0.3, "start_time": 1.0},
                    ],
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert len(scenario.scenes[0].sound_effects) == 2

    def test_filters_out_effects_without_preset_name(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "sound_effects": [
                        {"preset_name": "success"},
                        {"volume": 0.5},
                        {"preset_name": "", "volume": 0.5},
                    ],
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert len(scenario.scenes[0].sound_effects) == 1

    def test_returns_empty_list_when_no_effects(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].sound_effects == []


class TestScenarioParserParseFxBeat:
    def test_parses_camera_movement(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "fx_beat": {"camera_movement": "zoom_in_slow"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].fx_beat.camera_movement == "zoom_in_slow"

    def test_parses_transition(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                    "fx_beat": {"transition_next": "fade"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].fx_beat.transition_next == "fade"

    def test_defaults_to_none_and_cut(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Test"},
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)
        fx = scenario.scenes[0].fx_beat

        assert fx.camera_movement.value == "none"
        assert fx.transition_next.value == "cut"


class TestScenarioParserInferVoicePreset:
    def test_infers_cynical_from_korean_keyword(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "script_kr": "Test text",
                    "audio_note": "냉소적인 톤으로",
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].audio_script.voice_preset_id == "chirp_v3_korean_female_cynical"

    def test_infers_whisper_from_korean_keyword(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "script_kr": "Secret message",
                    "audio_note": "은밀하게 속삭이듯",
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert scenario.scenes[0].audio_script.voice_preset_id == "chirp_v3_korean_female_whisper"

    def test_defaults_to_confident(self):
        parser = ScenarioParser()
        data = {
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "script_kr": "Normal text",
                    "audio_note": "일반적인 톤",
                    "visual_layer": {"type": "existing_footage"},
                }
            ]
        }

        scenario = parser.parse_dict(data)

        assert (
            scenario.scenes[0].audio_script.voice_preset_id == "chirp_v3_korean_female_confident"
        )
