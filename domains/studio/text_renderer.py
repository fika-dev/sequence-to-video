import asyncio
import subprocess
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright

from domains.studio.models import VideoAsset
from infrastructure.cache import AssetCache


TEXT_STYLES = {
    "bold_impact_white": {
        "font_family": "Arial Black, sans-serif",
        "font_size": "144px",
        "font_weight": "900",
        "color": "#FFFFFF",
        "-webkit-text-stroke": "3px #000000",
        "paint-order": "stroke fill",
        "text_align": "center",
        "line_height": "1.2",
        "word_break": "keep-all",
    },
    "bold_impact_red": {
        "font_family": "Arial Black, sans-serif",
        "font_size": "144px",
        "font_weight": "900",
        "color": "#FF3333",
        "-webkit-text-stroke": "3px #000000",
        "paint-order": "stroke fill",
        "text_align": "center",
        "line_height": "1.2",
        "word_break": "keep-all",
    },
    "subtitle_clean": {
        "font_family": "Noto Sans KR, sans-serif",
        "font_size": "96px",
        "font_weight": "500",
        "color": "#FFFFFF",
        "background": "#000000",
        "padding": "16px 32px",
        "border_radius": "8px",
        "line_height": "1.3",
        "word_break": "keep-all",
    },
}

ANIMATION_CSS = {
    "none": "",
    "fade_in": """
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .text-overlay { animation: fadeIn 0.5s ease-out forwards; }
    """,
    "fade_in_up": """
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .text-overlay { animation: fadeInUp 0.5s ease-out forwards; }
    """,
    "slide_in_left": """
        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-100px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .text-overlay { animation: slideInLeft 0.4s ease-out forwards; }
    """,
    "slide_in_right": """
        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(100px); }
            to { opacity: 1; transform: translateX(0); }
        }
        .text-overlay { animation: slideInRight 0.4s ease-out forwards; }
    """,
    "bounce": """
        @keyframes bounce {
            0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(-20px); }
            60% { transform: translateY(-10px); }
        }
        .text-overlay { animation: bounce 1s ease-out; }
    """,
    "typewriter": """
        @keyframes typewriter {
            from { width: 0; }
            to { width: 100%; }
        }
        .text-overlay {
            overflow: hidden;
            white-space: nowrap;
            animation: typewriter 2s steps(40) forwards;
        }
    """,
}


def _smart_line_break(text: str, max_chars_per_line: int = 8) -> str:
    if len(text) <= max_chars_per_line:
        return text

    lines = []
    current_line = ""

    for char in text:
        current_line += char
        if len(current_line) >= max_chars_per_line and char in " ,，.。!！?？、":
            lines.append(current_line.strip())
            current_line = ""

    if current_line.strip():
        if lines and len(current_line) <= max_chars_per_line // 2:
            lines[-1] += current_line.strip()
        else:
            lines.append(current_line.strip())

    if len(lines) == 1:
        mid = len(text) // 2
        break_pos = mid
        for i in range(mid - 3, mid + 4):
            if 0 <= i < len(text) and text[i] in " ,，.。!！?？、":
                break_pos = i + 1
                break
        lines = [text[:break_pos].strip(), text[break_pos:].strip()]
        lines = [l for l in lines if l]

    return "<br>".join(lines)


class TextAnimationRenderer:
    def __init__(
        self,
        output_dir: Path | None = None,
        cache: AssetCache | None = None,
        max_font_size: int = 144,
    ):
        self.output_dir = Path(output_dir) if output_dir else Path("assets/generated/text_overlays")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        self.max_font_size = max_font_size

    async def render_overlay_async(
        self,
        text: str,
        style_template: str = "bold_impact_white",
        animation: str = "fade_in",
        position: str = "bottom",
        duration: float = 3.0,
        width: int = 720,
        height: int = 1280,
        fps: int = 30,
        output_filename: str | None = None,
    ) -> VideoAsset:
        style = TEXT_STYLES.get(style_template, TEXT_STYLES["bold_impact_white"]).copy()
        animation_css = ANIMATION_CSS.get(animation, "")

        style = self._apply_max_font_size(style)

        position_css = self._get_position_css(position)
        style_css = self._build_style_css(style)

        display_text = _smart_line_break(text)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                    width: {width}px;
                    height: {height}px;
                    background-color: transparent;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .text-overlay {{
                    {style_css}
                    padding: 32px;
                    max-width: 90%;
                    text-align: center;
                }}
                {animation_css}
            </style>
        </head>
        <body>
            <div class="text-overlay">{display_text}</div>
        </body>
        </html>
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
            f.write(html_content)
            html_path = f.name

        frames_dir = tempfile.mkdtemp()
        total_frames = int(duration * fps)

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.goto(f"file://{html_path}")

            for frame_num in range(total_frames):
                frame_path = Path(frames_dir) / f"frame_{frame_num:05d}.png"
                await page.screenshot(path=str(frame_path), omit_background=True)
                await asyncio.sleep(1 / fps / 10)

            await browser.close()

        if output_filename:
            base_name = (
                output_filename.rsplit(".", 1)[0] if "." in output_filename else output_filename
            )
            output_path = self.output_dir / f"{base_name}.mov"
        else:
            output_path = self.output_dir / f"text_{hash(text) & 0xFFFFFFFF:08x}.mov"

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                f"{frames_dir}/frame_%05d.png",
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4444",
                "-pix_fmt",
                "yuva444p10le",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

        Path(html_path).unlink()
        for frame_file in Path(frames_dir).glob("*.png"):
            frame_file.unlink()
        Path(frames_dir).rmdir()

        return VideoAsset(
            file_path=output_path,
            duration=duration,
            width=width,
            height=height,
            fps=float(fps),
        )

    def render_overlay(
        self,
        text: str,
        style_template: str = "bold_impact_white",
        animation: str = "fade_in",
        position: str = "bottom",
        duration: float = 3.0,
        width: int = 720,
        height: int = 1280,
        fps: int = 30,
        output_filename: str | None = None,
    ) -> VideoAsset:
        cache_params = {
            "text": text,
            "style_template": style_template,
            "animation": animation,
            "position": position,
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
        }

        if self.cache:
            cached_path = self.cache.get("text_overlay", cache_params)
            if cached_path:
                return VideoAsset(
                    file_path=cached_path,
                    duration=duration,
                    width=width,
                    height=height,
                    fps=float(fps),
                )

        result = asyncio.run(
            self.render_overlay_async(
                text=text,
                style_template=style_template,
                animation=animation,
                position=position,
                duration=duration,
                width=width,
                height=height,
                fps=fps,
                output_filename=output_filename,
            )
        )

        if self.cache:
            self.cache.put("text_overlay", cache_params, result.file_path)

        return result

    def _get_position_css(self, position: str) -> str:
        positions = {
            "top": "align-items: flex-start; justify-content: center; padding-top: 60px;",
            "center": "align-items: center; justify-content: center;",
            "bottom": "align-items: flex-end; justify-content: center; padding-bottom: 120px;",
        }
        return positions.get(position, positions["bottom"])

    def _build_style_css(self, style: dict) -> str:
        css_props = []
        for key, value in style.items():
            css_key = key.replace("_", "-")
            css_props.append(f"{css_key}: {value};")
        return " ".join(css_props)

    def _apply_max_font_size(self, style: dict) -> dict:
        if "font_size" in style:
            current_size = int(style["font_size"].replace("px", ""))
            if current_size > self.max_font_size:
                style["font_size"] = f"{self.max_font_size}px"
        return style
