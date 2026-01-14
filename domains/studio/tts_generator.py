import subprocess
from pathlib import Path

from google.cloud import texttospeech

from domains.studio.models import AudioAsset
from infrastructure.cache import AssetCache
from infrastructure.metadata import MetadataManager


VOICE_PRESETS = {
    "chirp_v3_korean_female_confident": {
        "language_code": "ko-KR",
        "name": "ko-KR-Chirp3-HD-Leda",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE,
    },
    "chirp_v3_korean_female_cynical": {
        "language_code": "ko-KR",
        "name": "ko-KR-Chirp3-HD-Leda",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE,
    },
    "chirp_v3_korean_female_emphasis": {
        "language_code": "ko-KR",
        "name": "ko-KR-Chirp3-HD-Leda",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE,
    },
    "chirp_v3_korean_female_whisper": {
        "language_code": "ko-KR",
        "name": "ko-KR-Chirp3-HD-Leda",
        "ssml_gender": texttospeech.SsmlVoiceGender.FEMALE,
    },
    "chirp_v3_korean_male_confident": {
        "language_code": "ko-KR",
        "name": "ko-KR-Chirp3-HD-Kore",
        "ssml_gender": texttospeech.SsmlVoiceGender.MALE,
    },
}


class TTSGenerator:
    def __init__(
        self,
        output_dir: Path | None = None,
        cache: AssetCache | None = None,
        metadata_manager: MetadataManager | None = None,
    ):
        self.client = texttospeech.TextToSpeechClient()
        self.output_dir = Path(output_dir) if output_dir else Path("assets/generated/audio")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        self.metadata = metadata_manager or MetadataManager()

    def generate(
        self,
        text: str,
        preset_id: str = "chirp_v3_korean_female_confident",
        speed: float = 1.0,
        output_filename: str | None = None,
    ) -> AudioAsset:
        cache_params = {"text": text, "preset_id": preset_id, "speed": speed}

        if self.cache:
            cached_path = self.cache.get("tts", cache_params)
            if cached_path:
                metadata = self.cache.get_metadata("tts", cache_params)
                return AudioAsset(
                    file_path=cached_path,
                    duration=metadata.get("duration", 0.0) if metadata else 0.0,
                    sample_rate=24000,
                    text=text,
                )

        preset = VOICE_PRESETS.get(preset_id, VOICE_PRESETS["chirp_v3_korean_female_confident"])

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code=preset["language_code"],
            name=preset["name"],
            ssml_gender=preset["ssml_gender"],
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=speed,
            sample_rate_hertz=24000,
        )

        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"tts_{hash(text) & 0xFFFFFFFF:08x}.wav"

        with open(output_path, "wb") as f:
            f.write(response.audio_content)

        duration = self._get_audio_duration(output_path)

        if self.cache:
            self.cache.put("tts", cache_params, output_path, metadata={"duration": duration})

        self.metadata.save(
            asset_type="audio",
            asset_path=output_path,
            prompt=text,
            params={
                "preset_id": preset_id,
                "speed": speed,
                "duration": duration,
            },
        )

        return AudioAsset(
            file_path=output_path,
            duration=duration,
            sample_rate=24000,
            text=text,
        )

    def _get_audio_duration(self, audio_path: Path) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())
