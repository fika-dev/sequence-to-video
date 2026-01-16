import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.studio.fallback_generator import FallbackGenerator


class TestFallbackGeneratorInit:
    def test_creates_output_directory(self, tmp_path):
        output_dir = tmp_path / "fallback"
        generator = FallbackGenerator(output_dir=output_dir)
        assert output_dir.exists()

    def test_uses_default_output_directory(self):
        generator = FallbackGenerator()
        assert generator.output_dir == Path("assets/generated/fallback")


class TestFallbackGeneratorWrapText:
    @pytest.fixture
    def generator(self, tmp_path):
        return FallbackGenerator(output_dir=tmp_path)

    def test_wraps_text_at_max_chars(self, generator):
        text = "This is a very long error message that should be wrapped"
        result = generator._wrap_text(text, max_chars=20)
        assert "\\n" in result

    def test_preserves_short_text(self, generator):
        text = "Short"
        result = generator._wrap_text(text, max_chars=30)
        assert result == "Short"

    def test_respects_word_boundaries(self, generator):
        text = "Hello World Test"
        result = generator._wrap_text(text, max_chars=12)
        lines = result.split("\\n")
        for line in lines:
            assert len(line) <= 13


class TestFallbackGeneratorGenerateBlackScreenImage:
    @pytest.fixture
    def generator(self, tmp_path):
        return FallbackGenerator(output_dir=tmp_path)

    def test_calls_ffmpeg_with_correct_dimensions(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            generator.generate_black_screen_image(
                width=720, height=1280, error_message="Test error"
            )

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "720x1280" in " ".join(call_args)

    def test_uses_custom_output_filename(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = generator.generate_black_screen_image(
                width=720,
                height=1280,
                error_message="Test",
                output_filename="custom.png",
            )

            assert result.name == "custom.png"

    def test_returns_path_in_output_dir(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = generator.generate_black_screen_image(
                width=720, height=1280, error_message="Test"
            )

            assert result.parent == tmp_path


class TestFallbackGeneratorGenerateBlackScreenVideo:
    @pytest.fixture
    def generator(self, tmp_path):
        return FallbackGenerator(output_dir=tmp_path)

    def test_calls_ffmpeg_with_correct_duration(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            generator.generate_black_screen_video(
                width=720, height=1280, duration=5.0, error_message="Test error"
            )

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "d=5.0" in " ".join(call_args)

    def test_uses_custom_output_filename(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = generator.generate_black_screen_video(
                width=720,
                height=1280,
                duration=3.0,
                error_message="Test",
                output_filename="custom.mp4",
            )

            assert result.name == "custom.mp4"

    def test_returns_path_in_output_dir(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            result = generator.generate_black_screen_video(
                width=720, height=1280, duration=3.0, error_message="Test"
            )

            assert result.parent == tmp_path

    def test_uses_libx264_codec(self, generator, tmp_path):
        with patch("domains.studio.fallback_generator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            generator.generate_black_screen_video(
                width=720, height=1280, duration=3.0, error_message="Test"
            )

            call_args = mock_run.call_args[0][0]
            assert "libx264" in call_args
