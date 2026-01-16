import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest

from domains.library.models import VideoClip, VideoIndex
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
from domains.studio.models import AudioAsset


@pytest.fixture
def sample_sequence_dict() -> dict[str, Any]:
    return {
        "project_id": "test_project",
        "metadata": {
            "locale": "ko-KR",
            "context": "skincare advertisement",
            "title": "Test Video",
        },
        "scenario_meta": {
            "title": "Test Video",
            "tone_voice": "energetic",
            "aspect_ratio": "9:16",
            "resolution": [720, 1280],
            "video_type": "mixed",
        },
        "scenes": [
            {
                "scene_id": "s01",
                "sequence_order": 1,
                "audio_script": {
                    "text": "Hello world",
                    "voice_preset_id": "chirp_v3_korean_female_confident",
                    "speed": 1.0,
                },
                "visual_layer": {
                    "type": "existing_footage",
                    "query_tags": ["product", "closeup"],
                    "prompt": "Product shot on white background",
                },
                "sync_mode": "audio",
            },
        ],
    }


@pytest.fixture
def sample_scene() -> Scene:
    return Scene(
        scene_id="s01",
        sequence_order=1,
        audio_script=AudioScript(
            text="Test narration text",
            voice_preset_id="chirp_v3_korean_female_confident",
            speed=1.0,
        ),
        visual_layer=VisualLayer(
            type=VisualType.EXISTING_FOOTAGE,
            query_tags=["skincare", "product"],
            prompt="Product closeup shot",
            fallback_gen_prompt="Skincare product on marble surface",
        ),
        text_overlay=TextOverlay(content="Amazing Product!"),
        fx_beat=FxBeat(),
        sync_mode=SyncMode.AUDIO,
    )


@pytest.fixture
def sample_scenario(sample_scene: Scene) -> Scenario:
    return Scenario(
        project_id="test_project",
        scenario_meta=ScenarioMeta(
            title="Test Video",
            tone_voice="energetic",
            video_type=VideoType.MIXED,
        ),
        scenes=[sample_scene],
    )


@pytest.fixture
def sample_video_clip() -> VideoClip:
    return VideoClip(
        clip_id="clip_001",
        source_file=Path("/fake/video.mp4"),
        start_time=0.0,
        end_time=5.0,
        description="Woman applying skincare product",
        tags=["skincare", "application", "female"],
        appeal_point="Shows product texture and application",
        content_type="product_demo",
        usage_context="Product demonstration scene",
        embedding=[0.1] * 768,
    )


@pytest.fixture
def sample_video_clips() -> list[VideoClip]:
    return [
        VideoClip(
            clip_id="clip_001",
            source_file=Path("/fake/video1.mp4"),
            start_time=0.0,
            end_time=5.0,
            description="Woman applying skincare product to face",
            tags=["skincare", "application", "face"],
            appeal_point="Shows smooth application",
            embedding=[0.9, 0.1, 0.0] + [0.0] * 765,
        ),
        VideoClip(
            clip_id="clip_002",
            source_file=Path("/fake/video2.mp4"),
            start_time=0.0,
            end_time=8.0,
            description="Product closeup on white background",
            tags=["product", "closeup", "studio"],
            appeal_point="Clean product shot",
            embedding=[0.1, 0.9, 0.0] + [0.0] * 765,
        ),
        VideoClip(
            clip_id="clip_003",
            source_file=Path("/fake/video3.mp4"),
            start_time=0.0,
            end_time=3.0,
            description="Hands holding product bottle",
            tags=["hands", "product", "holding"],
            appeal_point="Human touch element",
            embedding=[0.0, 0.1, 0.9] + [0.0] * 765,
        ),
    ]


@pytest.fixture
def sample_video_index(sample_video_clip: VideoClip) -> VideoIndex:
    return VideoIndex(
        source_file=Path("/fake/video.mp4"),
        total_duration=30.0,
        analyzed_at="2025-01-01T00:00:00",
        clips=[sample_video_clip],
    )


@pytest.fixture
def mock_tts_client() -> MagicMock:
    client = MagicMock()
    response = MagicMock()
    response.audio_content = b"fake_audio_content"
    client.synthesize_speech.return_value = response
    return client


@pytest.fixture
def sample_audio_asset(tmp_path: Path) -> AudioAsset:
    audio_path = tmp_path / "test_audio.wav"
    audio_path.write_bytes(b"fake_wav_content")
    return AudioAsset(
        file_path=audio_path,
        duration=3.5,
        sample_rate=24000,
        text="Test narration",
    )


@pytest.fixture
def mock_genai_client() -> MagicMock:
    client = MagicMock()
    return client


@pytest.fixture
def sample_gemini_response() -> str:
    return json.dumps(
        {
            "project_id": "generated_project",
            "metadata": {
                "locale": "ko-KR",
                "context": "skincare ad",
                "title": "New Product Launch",
            },
            "scenario_meta": {
                "title": "New Product Launch",
                "tone_voice": "energetic",
                "aspect_ratio": "9:16",
                "resolution": [720, 1280],
                "video_type": "mixed",
            },
            "scenes": [
                {
                    "scene_id": "s01",
                    "sequence_order": 1,
                    "audio_script": {"text": "Intro text", "speed": 1.0},
                    "visual_layer": {"type": "existing_footage", "query_tags": ["intro"]},
                    "sync_mode": "audio",
                }
            ],
        }
    )


@pytest.fixture
def mock_tts_generator(sample_audio_asset: AudioAsset) -> MagicMock:
    generator = MagicMock()
    generator.generate.return_value = sample_audio_asset
    return generator


@pytest.fixture
def mock_image_generator(tmp_path: Path) -> MagicMock:
    from domains.studio.models import ImageAsset

    generator = MagicMock()
    img_path = tmp_path / "generated_image.png"
    img_path.write_bytes(b"fake_png_content")
    generator.generate.return_value = ImageAsset(
        file_path=img_path,
        width=720,
        height=1280,
        prompt="test prompt",
    )
    return generator


@pytest.fixture
def mock_video_generator(tmp_path: Path) -> MagicMock:
    from domains.studio.models import VideoAsset

    generator = MagicMock()
    vid_path = tmp_path / "generated_video.mp4"
    vid_path.write_bytes(b"fake_mp4_content")
    generator.generate.return_value = VideoAsset(
        file_path=vid_path,
        width=720,
        height=1280,
        duration=5.0,
        prompt="test prompt",
    )
    return generator


@pytest.fixture
def mock_text_renderer(tmp_path: Path) -> MagicMock:
    from domains.studio.models import VideoAsset

    renderer = MagicMock()
    overlay_path = tmp_path / "text_overlay.mov"
    overlay_path.write_bytes(b"fake_mov_content")
    renderer.render_overlay.return_value = VideoAsset(
        file_path=overlay_path,
        width=720,
        height=1280,
        duration=3.0,
        prompt="overlay text",
    )
    return renderer


@pytest.fixture
def mock_asset_repository(sample_video_clips: list[VideoClip]) -> MagicMock:
    repo = MagicMock()
    repo.find_by_embedding.return_value = sample_video_clips
    repo.get_all_clips.return_value = sample_video_clips
    repo.get_clip_by_id.side_effect = lambda cid: next(
        (c for c in sample_video_clips if c.clip_id == cid), None
    )
    return repo


@pytest.fixture
def mock_footage_selector(sample_video_clips: list[VideoClip]) -> MagicMock:
    selector = MagicMock()
    selector.select_clip.return_value = sample_video_clips[0]
    return selector


@pytest.fixture
def temp_index_dir(tmp_path: Path) -> Path:
    index_dir = tmp_path / "library_index"
    index_dir.mkdir()
    return index_dir


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir
