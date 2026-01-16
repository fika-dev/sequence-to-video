import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.library.analyzer import (
    VideoContentAnalyzer,
    ANALYSIS_PROMPTS,
    CONTEXT_FILE_NAMES,
    MIME_TYPES,
)
from domains.library.models import VideoClip, VideoIndex


class TestAnalysisPromptsConstant:
    def test_generic_prompt_exists(self):
        assert "generic" in ANALYSIS_PROMPTS

    def test_product_ugc_prompt_exists(self):
        assert "product_ugc" in ANALYSIS_PROMPTS

    def test_product_ugc_contains_placeholder(self):
        assert "{product_context}" in ANALYSIS_PROMPTS["product_ugc"]


class TestContextFileNamesConstant:
    def test_contains_context_txt(self):
        assert "context.txt" in CONTEXT_FILE_NAMES

    def test_contains_product_txt(self):
        assert "product.txt" in CONTEXT_FILE_NAMES

    def test_contains_info_txt(self):
        assert "info.txt" in CONTEXT_FILE_NAMES


class TestMimeTypesConstant:
    def test_mp4_mime_type(self):
        assert MIME_TYPES[".mp4"] == "video/mp4"

    def test_mov_mime_type(self):
        assert MIME_TYPES[".mov"] == "video/quicktime"


class TestVideoContentAnalyzerParseDuration:
    @pytest.fixture
    def analyzer(self):
        with patch("domains.library.analyzer.genai.Client"):
            with patch("domains.library.analyzer.storage.Client") as mock_storage:
                mock_storage.return_value.get_bucket.return_value = MagicMock()
                return VideoContentAnalyzer(project="test-project")

    def test_parses_minutes_seconds(self, analyzer):
        result = analyzer._parse_duration("1:30")
        assert result == 90.0

    def test_parses_minutes_seconds_milliseconds(self, analyzer):
        result = analyzer._parse_duration("1:30:500")
        assert result == 90.5

    def test_parses_with_dot_separator(self, analyzer):
        result = analyzer._parse_duration("0:05.500")
        assert result == 5.5

    def test_returns_zero_for_invalid(self, analyzer):
        result = analyzer._parse_duration("invalid")
        assert result == 0.0


class TestVideoContentAnalyzerParseResponse:
    @pytest.fixture
    def analyzer(self):
        with patch("domains.library.analyzer.genai.Client"):
            with patch("domains.library.analyzer.storage.Client") as mock_storage:
                mock_storage.return_value.get_bucket.return_value = MagicMock()
                return VideoContentAnalyzer(project="test-project")

    def test_parses_clean_json(self, analyzer):
        response = '{"clips": [], "total_duration": "1:00"}'
        result = analyzer._parse_response(response)
        assert result == {"clips": [], "total_duration": "1:00"}

    def test_strips_markdown_json_block(self, analyzer):
        response = '```json\n{"clips": []}\n```'
        result = analyzer._parse_response(response)
        assert result == {"clips": []}

    def test_strips_plain_markdown_block(self, analyzer):
        response = '```\n{"clips": []}\n```'
        result = analyzer._parse_response(response)
        assert result == {"clips": []}

    def test_returns_empty_on_invalid_json(self, analyzer):
        response = "not valid json"
        result = analyzer._parse_response(response)
        assert result == {"clips": [], "total_duration": "0:00"}


class TestVideoContentAnalyzerBuildPrompt:
    @pytest.fixture
    def analyzer(self):
        with patch("domains.library.analyzer.genai.Client"):
            with patch("domains.library.analyzer.storage.Client") as mock_storage:
                mock_storage.return_value.get_bucket.return_value = MagicMock()
                return VideoContentAnalyzer(project="test-project")

    def test_generic_type_uses_generic_prompt(self, analyzer):
        result = analyzer._build_prompt("generic", None)
        assert "Analyze this video" in result

    def test_product_ugc_includes_context(self, analyzer):
        result = analyzer._build_prompt("product_ugc", "Vitamin C Serum")
        assert "Vitamin C Serum" in result
        assert "PRODUCT CONTEXT" in result

    def test_product_ugc_without_context_adds_placeholder(self, analyzer):
        result = analyzer._build_prompt("product_ugc", None)
        assert "No specific product context provided" in result

    def test_unknown_type_falls_back_to_generic(self, analyzer):
        result = analyzer._build_prompt("unknown_type", None)
        assert "Analyze this video" in result


class TestVideoContentAnalyzerLoadContextFile:
    @pytest.fixture
    def analyzer(self):
        with patch("domains.library.analyzer.genai.Client"):
            with patch("domains.library.analyzer.storage.Client") as mock_storage:
                mock_storage.return_value.get_bucket.return_value = MagicMock()
                return VideoContentAnalyzer(project="test-project")

    def test_loads_context_txt(self, analyzer, tmp_path):
        context_file = tmp_path / "context.txt"
        context_file.write_text("Product context here")

        result = analyzer._load_context_file(tmp_path)
        assert result == "Product context here"

    def test_loads_product_txt(self, analyzer, tmp_path):
        product_file = tmp_path / "product.txt"
        product_file.write_text("Product info")

        result = analyzer._load_context_file(tmp_path)
        assert result == "Product info"

    def test_prefers_context_over_product(self, analyzer, tmp_path):
        context_file = tmp_path / "context.txt"
        context_file.write_text("Context content")
        product_file = tmp_path / "product.txt"
        product_file.write_text("Product content")

        result = analyzer._load_context_file(tmp_path)
        assert result == "Context content"

    def test_returns_none_when_no_file(self, analyzer, tmp_path):
        result = analyzer._load_context_file(tmp_path)
        assert result is None


class TestVideoContentAnalyzerClipToText:
    @pytest.fixture
    def analyzer(self):
        with patch("domains.library.analyzer.genai.Client"):
            with patch("domains.library.analyzer.storage.Client") as mock_storage:
                mock_storage.return_value.get_bucket.return_value = MagicMock()
                return VideoContentAnalyzer(project="test-project")

    def test_combines_description_and_tags(self, analyzer):
        clip = VideoClip(
            clip_id="test_001",
            source_file=Path("test.mp4"),
            start_time=0.0,
            end_time=5.0,
            description="Person applying serum",
            tags=["skincare", "beauty"],
        )
        result = analyzer._clip_to_text(clip)
        assert "Person applying serum" in result
        assert "skincare" in result
        assert "beauty" in result

    def test_includes_appeal_point(self, analyzer):
        clip = VideoClip(
            clip_id="test_001",
            source_file=Path("test.mp4"),
            start_time=0.0,
            end_time=5.0,
            description="Description",
            appeal_point="Shows product efficacy",
        )
        result = analyzer._clip_to_text(clip)
        assert "Shows product efficacy" in result
