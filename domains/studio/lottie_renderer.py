import subprocess
from pathlib import Path

from domains.studio.models import VideoAsset


LOTTIE_PRESETS = {
    "success": "assets/stock/lottie_mov/success.mov",
    "error": "assets/stock/lottie_mov/error.mov",
    "warning": "assets/stock/lottie_mov/warning.mov",
    "loading": "assets/stock/lottie_mov/loading.mov",
}

DEFAULT_LOTTIE_MOV_DIR = Path("assets/stock/lottie_mov")


class LottieRenderer:
    def __init__(
        self,
        lottie_mov_dir: Path | None = None,
    ):
        self.lottie_mov_dir = Path(lottie_mov_dir) if lottie_mov_dir else DEFAULT_LOTTIE_MOV_DIR

    def get_overlay_path(self, lottie_name: str) -> Path:
        if lottie_name in LOTTIE_PRESETS:
            path = Path(LOTTIE_PRESETS[lottie_name])
            if path.exists():
                return path

        mov_path = self.lottie_mov_dir / f"{lottie_name}.mov"
        if mov_path.exists():
            return mov_path

        direct_path = Path(lottie_name)
        if direct_path.exists() and direct_path.suffix == ".mov":
            return direct_path

        raise FileNotFoundError(
            f"Lottie MOV not found: {lottie_name}. "
            f"Run 'uv run python scripts/convert_lottie_to_mov.py' to generate MOV files."
        )

    def get_overlay(self, lottie_name: str) -> VideoAsset:
        mov_path = self.get_overlay_path(lottie_name)
        duration = self._get_video_duration(mov_path)
        width, height = self._get_video_dimensions(mov_path)

        return VideoAsset(
            file_path=mov_path,
            duration=duration,
            width=width,
            height=height,
            fps=30.0,
        )

    def _get_video_duration(self, video_path: Path) -> float:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )
        return float(result.stdout.strip())

    def _get_video_dimensions(self, video_path: Path) -> tuple[int, int]:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=width,height",
                "-of",
                "csv=s=x:p=0",
                str(video_path),
            ],
            capture_output=True,
            text=True,
        )
        width, height = result.stdout.strip().split("x")
        return int(width), int(height)

    @staticmethod
    def list_presets() -> list[str]:
        return list(LOTTIE_PRESETS.keys())

    @staticmethod
    def list_available() -> dict[str, dict]:
        available = {}
        for name, path in LOTTIE_PRESETS.items():
            path_obj = Path(path)
            available[name] = {
                "path": path,
                "exists": path_obj.exists(),
            }
        return available
