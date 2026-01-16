from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from domains.studio.tts_generator import TTSGenerator, VOICE_PRESETS


class TestTTSGeneratorVoicePresets:
    def test_korean_female_confident_preset_exists(self):
        assert "chirp_v3_korean_female_confident" in VOICE_PRESETS

    def test_korean_male_confident_preset_exists(self):
        assert "chirp_v3_korean_male_confident" in VOICE_PRESETS

    def test_presets_have_required_fields(self):
        for preset_id, preset in VOICE_PRESETS.items():
            assert "language_code" in preset
            assert "name" in preset
            assert "ssml_gender" in preset


class TestTTSGeneratorGenerate:
    def test_creates_output_directory(self, tmp_path: Path, mock_tts_client: MagicMock):
        output_dir = tmp_path / "audio_output"

        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.5):
                generator = TTSGenerator(output_dir=output_dir)

        assert output_dir.exists()

    def test_calls_synthesize_speech_with_correct_params(
        self, tmp_path: Path, mock_tts_client: MagicMock
    ):
        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.5):
                generator = TTSGenerator(output_dir=tmp_path)
                generator.generate(
                    text="Hello world",
                    preset_id="chirp_v3_korean_female_confident",
                    speed=1.2,
                )

        mock_tts_client.synthesize_speech.assert_called_once()
        call_kwargs = mock_tts_client.synthesize_speech.call_args.kwargs
        assert call_kwargs["input"].text == "Hello world"
        assert call_kwargs["voice"].language_code == "ko-KR"
        assert call_kwargs["audio_config"].speaking_rate == 1.2

    def test_writes_audio_file(self, tmp_path: Path, mock_tts_client: MagicMock):
        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.5):
                generator = TTSGenerator(output_dir=tmp_path)
                result = generator.generate(text="Test", output_filename="test_output.wav")

        assert result.file_path.exists()
        assert result.file_path.name == "test_output.wav"
        assert result.file_path.read_bytes() == b"fake_audio_content"

    def test_returns_audio_asset_with_correct_metadata(
        self, tmp_path: Path, mock_tts_client: MagicMock
    ):
        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=3.7):
                generator = TTSGenerator(output_dir=tmp_path)
                result = generator.generate(text="Test narration")

        assert result.duration == 3.7
        assert result.sample_rate == 24000
        assert result.text == "Test narration"

    def test_uses_cache_when_available(self, tmp_path: Path, mock_tts_client: MagicMock):
        cached_path = tmp_path / "cached_audio.wav"
        cached_path.write_bytes(b"cached_content")

        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_path
        mock_cache.get_metadata.return_value = {"duration": 5.0}

        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            generator = TTSGenerator(output_dir=tmp_path, cache=mock_cache)
            result = generator.generate(text="Cached text")

        mock_tts_client.synthesize_speech.assert_not_called()
        assert result.file_path == cached_path
        assert result.duration == 5.0

    def test_stores_in_cache_after_generation(self, tmp_path: Path, mock_tts_client: MagicMock):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.5):
                generator = TTSGenerator(output_dir=tmp_path, cache=mock_cache)
                generator.generate(text="New text", speed=1.0)

        mock_cache.put.assert_called_once()
        put_call = mock_cache.put.call_args
        assert put_call.args[0] == "tts"
        assert put_call.args[1]["text"] == "New text"
        assert put_call.args[1]["speed"] == 1.0

    def test_falls_back_to_default_preset(self, tmp_path: Path, mock_tts_client: MagicMock):
        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.0):
                generator = TTSGenerator(output_dir=tmp_path)
                generator.generate(text="Test", preset_id="nonexistent_preset")

        call_kwargs = mock_tts_client.synthesize_speech.call_args.kwargs
        assert call_kwargs["voice"].language_code == "ko-KR"
        assert call_kwargs["voice"].name == "ko-KR-Chirp3-HD-Leda"

    def test_generates_filename_from_text_hash(self, tmp_path: Path, mock_tts_client: MagicMock):
        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.0):
                generator = TTSGenerator(output_dir=tmp_path)
                result = generator.generate(text="Some unique text")

        assert result.file_path.name.startswith("tts_")
        assert result.file_path.suffix == ".wav"

    def test_saves_metadata(self, tmp_path: Path, mock_tts_client: MagicMock):
        mock_metadata_manager = MagicMock()

        with patch("domains.studio.tts_generator.texttospeech.TextToSpeechClient") as mock_cls:
            mock_cls.return_value = mock_tts_client
            with patch.object(TTSGenerator, "_get_audio_duration", return_value=2.5):
                generator = TTSGenerator(
                    output_dir=tmp_path, metadata_manager=mock_metadata_manager
                )
                generator.generate(
                    text="Metadata test",
                    preset_id="chirp_v3_korean_female_confident",
                    speed=1.1,
                )

        mock_metadata_manager.save.assert_called_once()
        save_call = mock_metadata_manager.save.call_args.kwargs
        assert save_call["asset_type"] == "audio"
        assert save_call["prompt"] == "Metadata test"
        assert save_call["params"]["preset_id"] == "chirp_v3_korean_female_confident"
        assert save_call["params"]["speed"] == 1.1
        assert save_call["params"]["duration"] == 2.5
