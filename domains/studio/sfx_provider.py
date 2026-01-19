import json
import subprocess
from pathlib import Path

from domains.studio.models import AudioAsset

DEFAULT_SFX_DIR = Path("assets/stock/sfx")
SFX_PRESETS_FILE = Path("assets/presets/sfx_presets.json")


def _load_sfx_presets() -> dict[str, dict]:
    if not SFX_PRESETS_FILE.exists():
        return {}
    with open(SFX_PRESETS_FILE, encoding="utf-8") as f:
        return json.load(f)


class SFXProvider:
    def __init__(self, sfx_dir: Path | None = None):
        self.sfx_dir = Path(sfx_dir) if sfx_dir else DEFAULT_SFX_DIR
        self._presets = _load_sfx_presets()

    def get_sfx_path(self, sfx_name: str) -> Path:
        if sfx_name in self._presets:
            preset = self._presets[sfx_name]
            file_path = preset.get("file_path")
            if file_path:
                path = Path(file_path)
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
            f"SFX not found: {sfx_name}. Available presets: {', '.join(self._presets.keys())}"
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
        presets = _load_sfx_presets()
        return list(presets.keys())

    @staticmethod
    def list_available() -> dict[str, dict]:
        presets = _load_sfx_presets()
        available = {}
        for name, data in presets.items():
            file_path = data.get("file_path", "")
            path_obj = Path(file_path) if file_path else None
            available[name] = {
                "file_path": file_path,
                "description": data.get("description", ""),
                "use_case": data.get("use_case", ""),
                "exists": path_obj.exists() if path_obj else False,
            }
        return available
