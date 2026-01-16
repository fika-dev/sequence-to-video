import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from domains.library.models import VideoClip
from domains.library.selector import FootageSelector


class TestFootageSelectorBuildClipsSummary:
    def test_includes_clip_id(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips[:1])

        assert "[clip_001]" in summary

    def test_includes_duration(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips[:1])

        assert "Duration: 5.0s" in summary

    def test_includes_description(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips[:1])

        assert "Woman applying skincare product to face" in summary

    def test_includes_appeal_point_when_present(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips[:1])

        assert "Appeal: Shows smooth application" in summary

    def test_includes_tags_when_present(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips[:1])

        assert "Tags: skincare, application, face" in summary

    def test_separates_multiple_clips(self, sample_video_clips: list[VideoClip]):
        selector = FootageSelector.__new__(FootageSelector)

        summary = selector._build_clips_summary(sample_video_clips)

        assert "[clip_001]" in summary
        assert "[clip_002]" in summary
        assert "[clip_003]" in summary


class TestFootageSelectorParseResponse:
    def test_parses_valid_json(self):
        selector = FootageSelector.__new__(FootageSelector)
        response = '{"selected_clip_id": "clip_001", "reason": "Best match"}'

        result = selector._parse_response(response)

        assert result["selected_clip_id"] == "clip_001"
        assert result["reason"] == "Best match"

    def test_strips_markdown_json_block(self):
        selector = FootageSelector.__new__(FootageSelector)
        response = '```json\n{"selected_clip_id": "clip_002"}\n```'

        result = selector._parse_response(response)

        assert result["selected_clip_id"] == "clip_002"

    def test_returns_none_on_invalid_json(self):
        selector = FootageSelector.__new__(FootageSelector)
        response = "invalid json {"

        result = selector._parse_response(response)

        assert result["selected_clip_id"] == "NONE"


class TestFootageSelectorSelectClip:
    def test_returns_none_for_empty_clips(self):
        selector = FootageSelector.__new__(FootageSelector)

        result = selector.select_clip(
            clips=[],
            audio_text="test",
            visual_prompt="test",
            query_tags=[],
            min_duration=0,
        )

        assert result is None

    def test_calls_llm_with_scene_requirements(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "clip_001",
            "reason": "Best fit for skincare application scene",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            result = selector.select_clip(
                clips=sample_video_clips,
                audio_text="Apply the product gently",
                visual_prompt="Close-up of skincare application",
                query_tags=["skincare", "application"],
                min_duration=3.0,
            )

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs["contents"][0]
        assert "Apply the product gently" in prompt
        assert "Close-up of skincare application" in prompt
        assert "skincare, application" in prompt

    def test_returns_selected_clip(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "clip_002",
            "reason": "Product closeup matches requirement",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            result = selector.select_clip(
                clips=sample_video_clips,
                audio_text="Here is the product",
                visual_prompt="Product shot",
                query_tags=["product"],
                min_duration=3.0,
            )

        assert result is not None
        assert result.clip_id == "clip_002"

    def test_returns_none_when_llm_selects_none(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "NONE",
            "reason": "No suitable clip found",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            result = selector.select_clip(
                clips=sample_video_clips,
                audio_text="Underwater scene",
                visual_prompt="Fish swimming",
                query_tags=["underwater"],
                min_duration=3.0,
            )

        assert result is None

    def test_filters_clips_by_min_duration(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "clip_002",
            "reason": "Only clip meeting duration",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            selector.select_clip(
                clips=sample_video_clips,
                audio_text="Long scene",
                visual_prompt="Extended shot",
                query_tags=[],
                min_duration=6.0,
            )

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs["contents"][0]
        assert "[clip_002]" in prompt
        assert "[clip_003]" not in prompt

    def test_uses_all_clips_if_none_meet_duration(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "clip_001",
            "reason": "Best available",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            selector.select_clip(
                clips=sample_video_clips,
                audio_text="Very long scene",
                visual_prompt="Extended shot",
                query_tags=[],
                min_duration=100.0,
            )

        call_args = mock_client.models.generate_content.call_args
        prompt = call_args.kwargs["contents"][0]
        assert "[clip_001]" in prompt
        assert "[clip_002]" in prompt
        assert "[clip_003]" in prompt

    def test_handles_bracketed_clip_id_in_response(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "[clip_001]",
            "reason": "Selected",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            result = selector.select_clip(
                clips=sample_video_clips,
                audio_text="Test",
                visual_prompt="Test",
                query_tags=[],
                min_duration=0,
            )

        assert result is not None
        assert result.clip_id == "clip_001"

    def test_returns_none_when_clip_not_found_in_list(self, sample_video_clips: list[VideoClip]):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "selected_clip_id": "nonexistent_clip",
            "reason": "LLM hallucinated",
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.library.selector.genai.Client", return_value=mock_client):
            selector = FootageSelector(project="test-project")
            result = selector.select_clip(
                clips=sample_video_clips,
                audio_text="Test",
                visual_prompt="Test",
                query_tags=[],
                min_duration=0,
            )

        assert result is None
