import json
from unittest.mock import MagicMock, patch

import pytest

from domains.sequencing.generator import SequenceGenerator


class TestSequenceGeneratorParseResponse:
    def test_parses_clean_json(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        raw_json = '{"project_id": "test", "scenes": []}'

        result = generator._parse_response(raw_json)

        assert result == {"project_id": "test", "scenes": []}

    def test_strips_markdown_json_block(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        raw_json = '```json\n{"project_id": "test"}\n```'

        result = generator._parse_response(raw_json)

        assert result == {"project_id": "test"}

    def test_strips_plain_markdown_block(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        raw_json = '```\n{"key": "value"}\n```'

        result = generator._parse_response(raw_json)

        assert result == {"key": "value"}

    def test_handles_whitespace_around_json(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        raw_json = '   \n{"data": 123}\n   '

        result = generator._parse_response(raw_json)

        assert result == {"data": 123}

    def test_raises_on_invalid_json(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        invalid_json = '{"unclosed": '

        with pytest.raises(ValueError, match="Failed to parse sequence JSON"):
            generator._parse_response(invalid_json)

    def test_complex_nested_structure(self):
        generator = SequenceGenerator.__new__(SequenceGenerator)
        complex_json = json.dumps({
            "project_id": "complex_project",
            "metadata": {"locale": "ko-KR"},
            "scenes": [
                {
                    "scene_id": "s01",
                    "audio_script": {"text": "Hello", "speed": 1.0},
                    "visual_layer": {"type": "existing_footage"},
                }
            ],
        })

        result = generator._parse_response(complex_json)

        assert result["project_id"] == "complex_project"
        assert len(result["scenes"]) == 1
        assert result["scenes"][0]["audio_script"]["text"] == "Hello"


class TestSequenceGeneratorBuildPrompt:
    @patch("domains.sequencing.generator._load_presets")
    def test_includes_script_in_prompt(self, mock_load_presets):
        mock_load_presets.return_value = {}
        generator = SequenceGenerator.__new__(SequenceGenerator)

        prompt = generator._build_prompt("This is my test script")

        assert "This is my test script" in prompt

    @patch("domains.sequencing.generator._load_presets")
    def test_includes_voice_presets(self, mock_load_presets):
        mock_load_presets.return_value = {}
        generator = SequenceGenerator.__new__(SequenceGenerator)

        prompt = generator._build_prompt("test")

        assert "chirp_v3_korean_female_confident" in prompt
        assert "chirp_v3_korean_male_confident" in prompt

    @patch("domains.sequencing.generator._load_presets")
    def test_includes_visual_layer_types(self, mock_load_presets):
        mock_load_presets.return_value = {}
        generator = SequenceGenerator.__new__(SequenceGenerator)

        prompt = generator._build_prompt("test")

        assert "image_gen" in prompt
        assert "motion_graphic_gen" in prompt
        assert "existing_footage" in prompt

    @patch("domains.sequencing.generator._load_presets")
    def test_includes_video_types(self, mock_load_presets):
        mock_load_presets.return_value = {}
        generator = SequenceGenerator.__new__(SequenceGenerator)

        prompt = generator._build_prompt("test")

        assert "ugc_centered" in prompt
        assert "ai_generated" in prompt
        assert "mixed" in prompt


class TestSequenceGeneratorGenerateFromScript:
    @patch("domains.sequencing.generator._load_presets")
    def test_calls_genai_client_with_prompt(self, mock_load_presets):
        mock_load_presets.return_value = {}

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "project_id": "test",
            "metadata": {"locale": "ko-KR", "context": "test", "title": "Test"},
            "scenes": [],
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.sequencing.generator.genai.Client", return_value=mock_client):
            generator = SequenceGenerator(project="test-project")
            result, metadata = generator.generate_from_script("My script content")

        mock_client.models.generate_content.assert_called_once()
        call_kwargs = mock_client.models.generate_content.call_args
        assert "My script content" in call_kwargs.kwargs["contents"][0]

    @patch("domains.sequencing.generator._load_presets")
    def test_extracts_metadata_from_response(self, mock_load_presets):
        mock_load_presets.return_value = {}

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "project_id": "test",
            "metadata": {
                "locale": "en-US",
                "context": "product review",
                "title": "Review Video",
            },
            "scenes": [],
        })
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.sequencing.generator.genai.Client", return_value=mock_client):
            generator = SequenceGenerator(project="test-project")
            result, metadata = generator.generate_from_script("Script")

        assert metadata.locale == "en-US"
        assert metadata.context == "product review"
        assert metadata.title == "Review Video"

    @patch("domains.sequencing.generator._load_presets")
    def test_raises_on_empty_response(self, mock_load_presets):
        mock_load_presets.return_value = {}

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = None
        mock_client.models.generate_content.return_value = mock_response

        with patch("domains.sequencing.generator.genai.Client", return_value=mock_client):
            generator = SequenceGenerator(project="test-project")

            with pytest.raises(ValueError, match="Empty response"):
                generator.generate_from_script("Script")
