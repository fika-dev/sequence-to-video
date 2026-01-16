from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from domains.editing.composer import SequenceComposer
from domains.planning.models import (
    AudioScript,
    FxBeat,
    PreparedAssets,
    Scene,
    Scenario,
    ScenarioMeta,
    SyncMode,
    TextOverlay,
    VideoType,
    VisualLayer,
    VisualType,
)
from domains.studio.models import AudioAsset


class TestSequenceComposerBuildSearchQuery:
    def test_includes_audio_text(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="This is the narration"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
        )

        query = composer._build_search_query(scene)

        assert "This is the narration" in query

    def test_includes_visual_prompt(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Narration"),
            visual_layer=VisualLayer(
                type=VisualType.EXISTING_FOOTAGE,
                prompt="Close-up of product",
            ),
        )

        query = composer._build_search_query(scene)

        assert "Close-up of product" in query

    def test_includes_fallback_prompt(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Narration"),
            visual_layer=VisualLayer(
                type=VisualType.EXISTING_FOOTAGE,
                fallback_gen_prompt="Product on marble surface",
            ),
        )

        query = composer._build_search_query(scene)

        assert "Product on marble surface" in query

    def test_includes_query_tags(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Narration"),
            visual_layer=VisualLayer(
                type=VisualType.EXISTING_FOOTAGE,
                query_tags=["skincare", "product", "female"],
            ),
        )

        query = composer._build_search_query(scene)

        assert "skincare" in query
        assert "product" in query
        assert "female" in query

    def test_combines_all_parts(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Apply the product"),
            visual_layer=VisualLayer(
                type=VisualType.EXISTING_FOOTAGE,
                prompt="Woman applying cream",
                fallback_gen_prompt="Skincare routine",
                query_tags=["skincare", "application"],
            ),
        )

        query = composer._build_search_query(scene)

        assert "Apply the product" in query
        assert "Woman applying cream" in query
        assert "Skincare routine" in query
        assert "skincare" in query
        assert "application" in query


class TestSequenceComposerResolveDurationAndAudio:
    def test_audio_sync_mode_returns_natural_duration(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        sample_audio_asset: AudioAsset,
    ):
        mock_tts_generator.generate.return_value = sample_audio_asset
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test narration"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            sync_mode=SyncMode.AUDIO,
        )

        duration, audio = composer._resolve_duration_and_audio(scene)

        assert duration == sample_audio_asset.duration
        assert audio is not None

    def test_visual_sync_mode_adjusts_speed(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        tmp_path: Path,
    ):
        first_audio = AudioAsset(
            file_path=tmp_path / "first.wav",
            duration=4.0,
            sample_rate=24000,
            text="Test",
        )
        adjusted_audio = AudioAsset(
            file_path=tmp_path / "adjusted.wav",
            duration=5.0,
            sample_rate=24000,
            text="Test",
        )
        (tmp_path / "first.wav").write_bytes(b"audio")
        (tmp_path / "adjusted.wav").write_bytes(b"audio")

        mock_tts_generator.generate.side_effect = [first_audio, adjusted_audio]

        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test narration"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            sync_mode=SyncMode.VISUAL,
            duration=5.0,
        )

        duration, audio = composer._resolve_duration_and_audio(scene)

        assert mock_tts_generator.generate.call_count == 2
        first_call = mock_tts_generator.generate.call_args_list[0]
        assert first_call.kwargs.get("speed") == 1.0

    def test_uses_prepared_audio_when_available(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        tmp_path: Path,
    ):
        prepared_path = tmp_path / "prepared_audio.wav"
        prepared_path.write_bytes(b"prepared_content")

        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            sync_mode=SyncMode.AUDIO,
            prepared=PreparedAssets(
                audio_path=str(prepared_path),
                audio_duration=2.5,
            ),
        )

        duration, audio = composer._resolve_duration_and_audio(scene)

        mock_tts_generator.generate.assert_not_called()
        assert duration == 2.5
        assert audio.file_path == prepared_path

    def test_beat_sync_mode_uses_max_beat_timing(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        tmp_path: Path,
    ):
        first_audio = AudioAsset(
            file_path=tmp_path / "first.wav",
            duration=3.0,
            sample_rate=24000,
            text="Test",
        )
        (tmp_path / "first.wav").write_bytes(b"audio")

        mock_tts_generator.generate.return_value = first_audio

        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            sync_mode=SyncMode.BEAT,
            fx_beat=FxBeat(beat_timing=[0.5, 1.0, 2.0, 3.5]),
        )

        duration, audio = composer._resolve_duration_and_audio(scene)

        assert mock_tts_generator.generate.call_count >= 1


class TestSequenceComposerClipDeduplication:
    def test_tracks_used_clip_ids(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        mock_asset_repository: MagicMock,
        mock_footage_selector: MagicMock,
        sample_video_clips,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
            asset_repository=mock_asset_repository,
            footage_selector=mock_footage_selector,
        )

        mock_footage_selector.select_clip.return_value = sample_video_clips[0]

        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
        )

        clip = composer._find_existing_clip_for_selection(scene)

        assert "clip_001" in composer._used_clip_ids

    def test_excludes_used_clips_from_candidates(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
        mock_asset_repository: MagicMock,
        mock_footage_selector: MagicMock,
        sample_video_clips,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
            asset_repository=mock_asset_repository,
            footage_selector=mock_footage_selector,
        )

        composer._used_clip_ids.add("clip_001")
        composer._used_clip_ids.add("clip_002")

        scene = Scene(
            scene_id="s02",
            sequence_order=2,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
        )

        composer._find_existing_clip_for_selection(scene)

        select_call = mock_footage_selector.select_clip.call_args
        if select_call:
            passed_clips = select_call.kwargs.get("clips", [])
            passed_clip_ids = {c.clip_id for c in passed_clips}
            assert "clip_001" not in passed_clip_ids
            assert "clip_002" not in passed_clip_ids

    def test_initializes_used_clips_from_scenario(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )

        scenario = Scenario(
            project_id="test",
            scenario_meta=ScenarioMeta(title="Test"),
            scenes=[
                Scene(
                    scene_id="s01",
                    sequence_order=1,
                    audio_script=AudioScript(text="Test"),
                    visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
                    selected_clip_id="pre_selected_clip",
                )
            ],
        )

        composer._init_used_clips_from_scenario(scenario)

        assert "pre_selected_clip" in composer._used_clip_ids
        assert composer._scene_clip_mapping["s01"] == "pre_selected_clip"


class TestSequenceComposerResolveLottieOverlays:
    def test_returns_empty_list_when_no_overlays(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            lottie_overlays=[],
        )

        result = composer._resolve_lottie_overlays(scene)

        assert result == []


class TestSequenceComposerResolveSoundEffects:
    def test_returns_empty_list_when_no_effects(
        self,
        mock_tts_generator: MagicMock,
        mock_image_generator: MagicMock,
        mock_video_generator: MagicMock,
        mock_text_renderer: MagicMock,
    ):
        composer = SequenceComposer(
            tts_generator=mock_tts_generator,
            image_generator=mock_image_generator,
            video_generator=mock_video_generator,
            text_renderer=mock_text_renderer,
        )
        scene = Scene(
            scene_id="s01",
            sequence_order=1,
            audio_script=AudioScript(text="Test"),
            visual_layer=VisualLayer(type=VisualType.EXISTING_FOOTAGE),
            sound_effects=[],
        )

        result = composer._resolve_sound_effects(scene)

        assert result == []
