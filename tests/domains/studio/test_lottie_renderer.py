import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.studio.lottie_renderer import (
    LottieRenderer,
    LOTTIE_PRESETS,
    DEFAULT_LOTTIE_MOV_DIR,
)
from domains.studio.models import VideoAsset


class TestLottiePresetsConstant:
    def test_success_preset_exists(self):
        assert "success" in LOTTIE_PRESETS

    def test_error_preset_exists(self):
        assert "error" in LOTTIE_PRESETS

    def test_warning_preset_exists(self):
        assert "warning" in LOTTIE_PRESETS

    def test_loading_preset_exists(self):
        assert "loading" in LOTTIE_PRESETS

    def test_presets_point_to_mov_files(self):
        for name, path in LOTTIE_PRESETS.items():
            assert path.endswith(".mov"), f"{name} should point to .mov file"


class TestLottieRendererInit:
    def test_uses_default_directory(self):
        renderer = LottieRenderer()
        assert renderer.lottie_mov_dir == DEFAULT_LOTTIE_MOV_DIR

    def test_uses_custom_directory(self, tmp_path):
        custom_dir = tmp_path / "custom_lottie"
        custom_dir.mkdir()
        renderer = LottieRenderer(lottie_mov_dir=custom_dir)
        assert renderer.lottie_mov_dir == custom_dir


class TestLottieRendererGetOverlayPath:
    @pytest.fixture
    def renderer(self, tmp_path):
        return LottieRenderer(lottie_mov_dir=tmp_path)

    def test_returns_preset_path_when_exists(self, tmp_path):
        preset_path = Path(LOTTIE_PRESETS["success"])
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.touch()

        renderer = LottieRenderer()
        result = renderer.get_overlay_path("success")
        assert result == preset_path

        preset_path.unlink()

    def test_returns_custom_mov_when_exists(self, renderer, tmp_path):
        custom_mov = tmp_path / "custom_anim.mov"
        custom_mov.touch()

        result = renderer.get_overlay_path("custom_anim")
        assert result == custom_mov

    def test_returns_direct_path_when_exists(self, renderer, tmp_path):
        direct_mov = tmp_path / "direct.mov"
        direct_mov.touch()

        result = renderer.get_overlay_path(str(direct_mov))
        assert result == direct_mov

    def test_raises_when_not_found(self, renderer):
        with pytest.raises(FileNotFoundError, match="Lottie MOV not found"):
            renderer.get_overlay_path("nonexistent_animation")


class TestLottieRendererGetOverlay:
    def test_returns_video_asset_with_correct_properties(self, tmp_path):
        test_mov = tmp_path / "test.mov"
        test_mov.touch()

        renderer = LottieRenderer(lottie_mov_dir=tmp_path)

        with patch.object(renderer, "_get_video_duration") as mock_duration:
            with patch.object(renderer, "_get_video_dimensions") as mock_dimensions:
                mock_duration.return_value = 2.5
                mock_dimensions.return_value = (1080, 1080)

                result = renderer.get_overlay("test")

                assert isinstance(result, VideoAsset)
                assert result.file_path == test_mov
                assert result.duration == 2.5
                assert result.width == 1080
                assert result.height == 1080
                assert result.fps == 30.0


class TestLottieRendererListPresets:
    def test_returns_list_of_preset_names(self):
        result = LottieRenderer.list_presets()
        assert isinstance(result, list)
        assert "success" in result
        assert "error" in result


class TestLottieRendererListAvailable:
    def test_returns_dict_with_exists_status(self):
        result = LottieRenderer.list_available()
        assert isinstance(result, dict)
        for name, info in result.items():
            assert "path" in info
            assert "exists" in info
            assert isinstance(info["exists"], bool)
