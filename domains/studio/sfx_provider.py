import subprocess
from pathlib import Path

from domains.studio.models import AudioAsset


SFX_PRESETS = {
    "success": "assets/stock/sfx/success_ding.mp3",
    "error": "assets/stock/sfx/error_beep.mp3",
    "warning": "assets/stock/sfx/warning_alert.mp3",
    "loading": "assets/stock/sfx/loading_tick.mp3",
    "whoosh": "assets/stock/sfx/sfx_391449.mp3",
    "click": "assets/stock/sfx/sfx_687105.mp3",
}

DEFAULT_SFX_DIR = Path("assets/stock/sfx")


class SFXProvider:
    def __init__(self, sfx_dir: Path | None = None):
        self.sfx_dir = Path(sfx_dir) if sfx_dir else DEFAULT_SFX_DIR

    def get_sfx_path(self, sfx_name: str) -> Path:
        if sfx_name in SFX_PRESETS:
            path = Path(SFX_PRESETS[sfx_name])
            if path.exists():
                return path

        for ext in [".mp3", ".wav", ".ogg"]:
            sfx_path = self.sfx_dir / f"{sfx_name}{ext}"
            if sfx_path.exists():
                return sfx_path

        direct_path = Path(sfx_name)
        if direct_path.exists() and direct_path.suffix in {".mp3", ".wav", ".ogg"}:
            return direct_path

        raise FileNotFoundError(
            f"SFX not found: {sfx_name}. Available presets: {', '.join(SFX_PRESETS.keys())}"
        )

    def get_sfx(self, sfx_name: str) -> AudioAsset:
        sfx_path = self.get_sfx_path(sfx_name)
        duration = self._get_audio_duration(sfx_path)

        return AudioAsset(
            file_path=sfx_path,
            duration=duration,
            sample_rate=44100,
            text=sfx_name,
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
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    @staticmethod
    def list_presets() -> list[str]:
        return list(SFX_PRESETS.keys())

    @staticmethod
    def list_available() -> dict[str, dict]:
        available = {}
        for name, path in SFX_PRESETS.items():
            path_obj = Path(path)
            available[name] = {
                "path": path,
                "exists": path_obj.exists(),
            }
        return available
