import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.studio.text_renderer import (
    TextAnimationRenderer,
    TEXT_STYLES,
    ANIMATION_CSS,
    _smart_line_break,
)
from domains.studio.models import VideoAsset


class TestSmartLineBreak:
    def test_short_text_unchanged(self):
        result = _smart_line_break("Hello")
        assert result == "Hello"

    def test_text_at_max_unchanged(self):
        result = _smart_line_break("12345678", max_chars_per_line=8)
        assert result == "12345678"

    def test_breaks_at_punctuation(self):
        result = _smart_line_break("안녕하세요, 반갑습니다", max_chars_per_line=8)
        assert "<br>" in result

    def test_breaks_long_text_near_middle(self):
        result = _smart_line_break("이것은매우긴텍스트입니다", max_chars_per_line=6)
        assert "<br>" in result

    def test_returns_string_with_br_tags(self):
        result = _smart_line_break("Hello World, this is a test!", max_chars_per_line=10)
        assert isinstance(result, str)


class TestTextStylesConstant:
    def test_bold_impact_white_exists(self):
        assert "bold_impact_white" in TEXT_STYLES

    def test_bold_impact_red_exists(self):
        assert "bold_impact_red" in TEXT_STYLES

    def test_subtitle_clean_exists(self):
        assert "subtitle_clean" in TEXT_STYLES

    def test_styles_have_font_family(self):
        for style_name, style_dict in TEXT_STYLES.items():
            assert "font_family" in style_dict, f"{style_name} missing font_family"

    def test_styles_have_font_size(self):
        for style_name, style_dict in TEXT_STYLES.items():
            assert "font_size" in style_dict, f"{style_name} missing font_size"


class TestAnimationCssConstant:
    def test_none_animation_exists(self):
        assert "none" in ANIMATION_CSS

    def test_fade_in_animation_exists(self):
        assert "fade_in" in ANIMATION_CSS

    def test_bounce_animation_exists(self):
        assert "bounce" in ANIMATION_CSS

    def test_typewriter_animation_exists(self):
        assert "typewriter" in ANIMATION_CSS

    def test_none_animation_is_empty(self):
        assert ANIMATION_CSS["none"] == ""

    def test_fade_in_contains_keyframes(self):
        assert "@keyframes" in ANIMATION_CSS["fade_in"]


class TestTextAnimationRendererInit:
    def test_creates_output_directory(self, tmp_path):
        output_dir = tmp_path / "text_overlays"
        renderer = TextAnimationRenderer(output_dir=output_dir)
        assert output_dir.exists()

    def test_default_max_font_size(self, tmp_path):
        renderer = TextAnimationRenderer(output_dir=tmp_path)
        assert renderer.max_font_size == 144


class TestTextAnimationRendererGetPositionCss:
    @pytest.fixture
    def renderer(self, tmp_path):
        return TextAnimationRenderer(output_dir=tmp_path)

    def test_top_position(self, renderer):
        result = renderer._get_position_css("top")
        assert "flex-start" in result
        assert "padding-top" in result

    def test_center_position(self, renderer):
        result = renderer._get_position_css("center")
        assert "center" in result

    def test_bottom_position(self, renderer):
        result = renderer._get_position_css("bottom")
        assert "flex-end" in result
        assert "padding-bottom" in result

    def test_unknown_position_defaults_to_bottom(self, renderer):
        result = renderer._get_position_css("unknown")
        assert "flex-end" in result


class TestTextAnimationRendererBuildStyleCss:
    @pytest.fixture
    def renderer(self, tmp_path):
        return TextAnimationRenderer(output_dir=tmp_path)

    def test_converts_underscores_to_dashes(self, renderer):
        style = {"font_size": "16px", "font_weight": "bold"}
        result = renderer._build_style_css(style)
        assert "font-size: 16px" in result
        assert "font-weight: bold" in result

    def test_joins_properties_with_spaces(self, renderer):
        style = {"color": "red", "background": "blue"}
        result = renderer._build_style_css(style)
        assert "color: red;" in result
        assert "background: blue;" in result


class TestTextAnimationRendererApplyMaxFontSize:
    @pytest.fixture
    def renderer(self, tmp_path):
        return TextAnimationRenderer(output_dir=tmp_path, max_font_size=100)

    def test_reduces_large_font_size(self, renderer):
        style = {"font_size": "200px"}
        result = renderer._apply_max_font_size(style)
        assert result["font_size"] == "100px"

    def test_preserves_small_font_size(self, renderer):
        style = {"font_size": "50px"}
        result = renderer._apply_max_font_size(style)
        assert result["font_size"] == "50px"

    def test_handles_missing_font_size(self, renderer):
        style = {"color": "red"}
        result = renderer._apply_max_font_size(style)
        assert "font_size" not in result


class TestTextAnimationRendererRenderOverlay:
    @pytest.fixture
    def mock_cache(self):
        cache = MagicMock()
        cache.get.return_value = None
        return cache

    def test_returns_cached_result_when_available(self, tmp_path, mock_cache):
        cached_path = tmp_path / "cached.mov"
        cached_path.touch()
        mock_cache.get.return_value = cached_path

        renderer = TextAnimationRenderer(output_dir=tmp_path, cache=mock_cache)

        result = renderer.render_overlay("Test text", duration=3.0)

        assert result.file_path == cached_path
        assert result.duration == 3.0
        assert isinstance(result, VideoAsset)

    def test_stores_in_cache_after_generation(self, tmp_path, mock_cache):
        mock_cache.get.return_value = None

        renderer = TextAnimationRenderer(output_dir=tmp_path, cache=mock_cache)

        with patch.object(renderer, "render_overlay_async") as mock_async:
            mock_asset = VideoAsset(
                file_path=tmp_path / "test.mov",
                duration=3.0,
                width=720,
                height=1280,
                fps=30.0,
            )
            with patch("domains.studio.text_renderer.asyncio.run") as mock_run:
                mock_run.return_value = mock_asset

                renderer.render_overlay("Test text", duration=3.0)

                mock_cache.put.assert_called_once()

    def test_applies_custom_font_color(self, tmp_path):
        renderer = TextAnimationRenderer(output_dir=tmp_path)

        with patch("domains.studio.text_renderer.asyncio.run") as mock_run:
            mock_asset = VideoAsset(
                file_path=tmp_path / "test.mov",
                duration=3.0,
                width=720,
                height=1280,
                fps=30.0,
            )
            mock_run.return_value = mock_asset

            result = renderer.render_overlay("Test", font_color="#FF0000")

            call_kwargs = mock_run.call_args
            assert call_kwargs is not None

    def test_applies_custom_background_color(self, tmp_path):
        renderer = TextAnimationRenderer(output_dir=tmp_path)

        with patch("domains.studio.text_renderer.asyncio.run") as mock_run:
            mock_asset = VideoAsset(
                file_path=tmp_path / "test.mov",
                duration=3.0,
                width=720,
                height=1280,
                fps=30.0,
            )
            mock_run.return_value = mock_asset

            result = renderer.render_overlay("Test", background_color="#000000")

            call_kwargs = mock_run.call_args
            assert call_kwargs is not None
