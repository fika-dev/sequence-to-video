import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from domains.studio.sfx_provider import (
    SFXProvider,
    SFX_PRESETS,
    DEFAULT_SFX_DIR,
)
from domains.studio.models import AudioAsset


class TestSfxPresetsConstant:
    def test_success_preset_exists(self):
        assert "success" in SFX_PRESETS

    def test_error_preset_exists(self):
        assert "error" in SFX_PRESETS

    def test_warning_preset_exists(self):
        assert "warning" in SFX_PRESETS

    def test_whoosh_preset_exists(self):
        assert "whoosh" in SFX_PRESETS

    def test_click_preset_exists(self):
        assert "click" in SFX_PRESETS

    def test_presets_point_to_audio_files(self):
        for name, path in SFX_PRESETS.items():
            assert path.endswith(".mp3"), f"{name} should point to .mp3 file"


class TestSfxProviderInit:
    def test_uses_default_directory(self):
        provider = SFXProvider()
        assert provider.sfx_dir == DEFAULT_SFX_DIR

    def test_uses_custom_directory(self, tmp_path):
        custom_dir = tmp_path / "custom_sfx"
        custom_dir.mkdir()
        provider = SFXProvider(sfx_dir=custom_dir)
        assert provider.sfx_dir == custom_dir


class TestSfxProviderGetSfxPath:
    @pytest.fixture
    def provider(self, tmp_path):
        return SFXProvider(sfx_dir=tmp_path)

    def test_returns_preset_path_when_exists(self, tmp_path):
        preset_path = Path(SFX_PRESETS["success"])
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.touch()

        provider = SFXProvider()
        result = provider.get_sfx_path("success")
        assert result == preset_path

        preset_path.unlink()

    def test_returns_mp3_when_exists(self, provider, tmp_path):
        mp3_file = tmp_path / "custom.mp3"
        mp3_file.touch()

        result = provider.get_sfx_path("custom")
        assert result == mp3_file

    def test_returns_wav_when_exists(self, provider, tmp_path):
        wav_file = tmp_path / "custom.wav"
        wav_file.touch()

        result = provider.get_sfx_path("custom")
        assert result == wav_file

    def test_returns_ogg_when_exists(self, provider, tmp_path):
        ogg_file = tmp_path / "custom.ogg"
        ogg_file.touch()

        result = provider.get_sfx_path("custom")
        assert result == ogg_file

    def test_prefers_mp3_over_wav(self, provider, tmp_path):
        mp3_file = tmp_path / "custom.mp3"
        wav_file = tmp_path / "custom.wav"
        mp3_file.touch()
        wav_file.touch()

        result = provider.get_sfx_path("custom")
        assert result == mp3_file

    def test_returns_direct_path_when_exists(self, provider, tmp_path):
        direct_mp3 = tmp_path / "direct.mp3"
        direct_mp3.touch()

        result = provider.get_sfx_path(str(direct_mp3))
        assert result == direct_mp3

    def test_raises_when_not_found(self, provider):
        with pytest.raises(FileNotFoundError, match="SFX not found"):
            provider.get_sfx_path("nonexistent_sound")


class TestSfxProviderGetSfx:
    def test_returns_audio_asset_with_correct_properties(self, tmp_path):
        test_mp3 = tmp_path / "test.mp3"
        test_mp3.touch()

        provider = SFXProvider(sfx_dir=tmp_path)

        with patch.object(provider, "_get_audio_duration") as mock_duration:
            mock_duration.return_value = 1.5

            result = provider.get_sfx("test")

            assert isinstance(result, AudioAsset)
            assert result.file_path == test_mp3
            assert result.duration == 1.5
            assert result.sample_rate == 44100
            assert result.text == "test"


class TestSfxProviderGetAudioDuration:
    def test_returns_zero_on_invalid_output(self, tmp_path):
        provider = SFXProvider(sfx_dir=tmp_path)

        with patch("domains.studio.sfx_provider.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "invalid"
            mock_run.return_value = mock_result

            result = provider._get_audio_duration(tmp_path / "test.mp3")
            assert result == 0.0


class TestSfxProviderListPresets:
    def test_returns_list_of_preset_names(self):
        result = SFXProvider.list_presets()
        assert isinstance(result, list)
        assert "success" in result
        assert "whoosh" in result


class TestSfxProviderListAvailable:
    def test_returns_dict_with_exists_status(self):
        result = SFXProvider.list_available()
        assert isinstance(result, dict)
        for name, info in result.items():
            assert "path" in info
            assert "exists" in info
            assert isinstance(info["exists"], bool)
