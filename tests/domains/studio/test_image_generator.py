import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from domains.studio.image_generator import ImageGenerator
from domains.studio.models import ImageAsset


class TestImageGeneratorGetAspectRatio:
    @pytest.fixture
    def generator(self, tmp_path):
        with patch("domains.studio.image_generator.genai.Client"):
            return ImageGenerator(output_dir=tmp_path, project="test-project")

    def test_portrait_returns_9_16(self, generator):
        result = generator._get_aspect_ratio(720, 1280)
        assert result == "9:16"

    def test_landscape_returns_16_9(self, generator):
        result = generator._get_aspect_ratio(1920, 1080)
        assert result == "16:9"

    def test_square_returns_1_1(self, generator):
        result = generator._get_aspect_ratio(1080, 1080)
        assert result == "1:1"

    def test_near_square_returns_1_1(self, generator):
        result = generator._get_aspect_ratio(1000, 1050)
        assert result == "1:1"

    def test_3_4_portrait_returns_3_4(self, generator):
        result = generator._get_aspect_ratio(900, 1200)
        assert result == "3:4"

    def test_4_3_landscape_returns_4_3(self, generator):
        result = generator._get_aspect_ratio(1200, 900)
        assert result == "4:3"


class TestImageGeneratorGetLocaleInstruction:
    @pytest.fixture
    def generator_kr(self, tmp_path):
        with patch("domains.studio.image_generator.genai.Client"):
            return ImageGenerator(output_dir=tmp_path, project="test-project", locale="ko-KR")

    @pytest.fixture
    def generator_en(self, tmp_path):
        with patch("domains.studio.image_generator.genai.Client"):
            return ImageGenerator(output_dir=tmp_path, project="test-project", locale="en-US")

    @pytest.fixture
    def generator_unknown(self, tmp_path):
        with patch("domains.studio.image_generator.genai.Client"):
            return ImageGenerator(output_dir=tmp_path, project="test-project", locale="xx-XX")

    def test_korean_locale_includes_korean_instruction(self, generator_kr):
        result = generator_kr._get_locale_instruction()
        assert "Korean" in result
        assert "IMPORTANT" in result

    def test_english_locale_includes_english_instruction(self, generator_en):
        result = generator_en._get_locale_instruction()
        assert "English" in result

    def test_unknown_locale_returns_empty(self, generator_unknown):
        result = generator_unknown._get_locale_instruction()
        assert result == ""


class TestImageGeneratorGenerate:
    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.get.return_value = None
        return cache

    @pytest.fixture
    def mock_pil_image(self):
        img = MagicMock()
        img.width = 720
        img.height = 1280
        return img

    def test_returns_cached_result_when_available(self, tmp_path, mock_cache):
        cached_path = tmp_path / "cached.png"
        cached_path.touch()
        mock_cache.get.return_value = cached_path
        mock_cache.get_metadata.return_value = {"width": 720, "height": 1280}

        with patch("domains.studio.image_generator.genai.Client"):
            generator = ImageGenerator(
                output_dir=tmp_path, project="test-project", cache=mock_cache
            )

        result = generator.generate("test prompt")

        assert result.file_path == cached_path
        assert result.width == 720
        assert result.height == 1280
        assert result.prompt == "test prompt"

    def test_calls_genai_when_not_cached(self, tmp_path, mock_cache, mock_pil_image):
        mock_cache.get.return_value = None

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = mock_pil_image

                generator = ImageGenerator(
                    output_dir=tmp_path, project="test-project", cache=mock_cache
                )
                generator.generate("test prompt")

                mock_run.assert_called_once()

    def test_raises_on_no_image_generated(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = None

                generator = ImageGenerator(
                    output_dir=tmp_path, project="test-project", cache=mock_cache
                )

                with pytest.raises(RuntimeError, match="No image generated"):
                    generator.generate("test prompt")

    def test_stores_in_cache_after_generation(self, tmp_path, mock_cache, mock_pil_image):
        mock_cache.get.return_value = None

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = mock_pil_image

                generator = ImageGenerator(
                    output_dir=tmp_path, project="test-project", cache=mock_cache
                )
                generator.generate("test prompt")

                mock_cache.put.assert_called_once()

    def test_saves_metadata_after_generation(self, tmp_path, mock_cache, mock_pil_image):
        mock_cache.get.return_value = None
        mock_metadata = MagicMock()

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = mock_pil_image

                generator = ImageGenerator(
                    output_dir=tmp_path,
                    project="test-project",
                    cache=mock_cache,
                    metadata_manager=mock_metadata,
                )
                generator.generate("test prompt")

                mock_metadata.save.assert_called_once()
                call_kwargs = mock_metadata.save.call_args.kwargs
                assert call_kwargs["asset_type"] == "image"
                assert call_kwargs["prompt"] == "test prompt"

    def test_custom_output_filename_used(self, tmp_path, mock_cache, mock_pil_image):
        mock_cache.get.return_value = None

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = mock_pil_image

                generator = ImageGenerator(
                    output_dir=tmp_path, project="test-project", cache=mock_cache
                )
                result = generator.generate("test prompt", output_filename="custom.png")

                assert result.file_path.name == "custom.png"

    def test_returns_image_asset_with_correct_metadata(self, tmp_path, mock_cache, mock_pil_image):
        mock_cache.get.return_value = None
        mock_pil_image.width = 720
        mock_pil_image.height = 1280

        with patch("domains.studio.image_generator.genai.Client"):
            with patch("domains.studio.image_generator.asyncio.run") as mock_run:
                mock_run.return_value = mock_pil_image

                generator = ImageGenerator(
                    output_dir=tmp_path, project="test-project", cache=mock_cache
                )
                result = generator.generate("test prompt")

                assert isinstance(result, ImageAsset)
                assert result.width == 720
                assert result.height == 1280
                assert result.prompt == "test prompt"
