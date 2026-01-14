import subprocess
from pathlib import Path


class FallbackGenerator:
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path("assets/generated/fallback")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_black_screen_image(
        self,
        width: int,
        height: int,
        error_message: str,
        output_filename: str | None = None,
    ) -> Path:
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"fallback_{hash(error_message) & 0xFFFFFFFF:08x}.png"

        font_size = min(width, height) // 20
        wrapped_message = self._wrap_text(error_message, max_chars=30)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={width}x{height}:d=1",
                "-vf",
                f"drawtext=text='{wrapped_message}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2",
                "-frames:v",
                "1",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        return output_path

    def generate_black_screen_video(
        self,
        width: int,
        height: int,
        duration: float,
        error_message: str,
        output_filename: str | None = None,
    ) -> Path:
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"fallback_{hash(error_message) & 0xFFFFFFFF:08x}.mp4"

        font_size = min(width, height) // 20
        wrapped_message = self._wrap_text(error_message, max_chars=30)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=c=black:s={width}x{height}:d={duration}",
                "-vf",
                f"drawtext=text='{wrapped_message}':fontcolor=white:fontsize={font_size}:x=(w-text_w)/2:y=(h-text_h)/2",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(output_path),
            ],
            capture_output=True,
            check=True,
        )

        return output_path

    def _wrap_text(self, text: str, max_chars: int = 30) -> str:
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 > max_chars and current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1

        if current_line:
            lines.append(" ".join(current_line))

        return "\\n".join(lines)
